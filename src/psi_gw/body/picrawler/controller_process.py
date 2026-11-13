"""Local JSONL process boundary; never a hardware/network transport choice.

The parent owns simulation time and emits stop on timeout/EOF/protocol failure.
Nonblocking pipes bound both writes and reads. Wall-clock deadlines are I/O
mechanisms only; the child policy receives logical observations and actions.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import os
import selectors
import subprocess
import sys
import time
from typing import Any, Sequence

from psi_gw.body import Action, Observation

from .robot_controllers import ControllerConfig, ReferenceController, sensor_view
from .validation_io import _unique, canonical

MAX_BYTES = 2_000_000


def parse_line(line: bytes) -> dict[str, Any]:
    if len(line) > MAX_BYTES:
        raise ValueError("JSONL record exceeds bound")
    def invalid(token):
        raise ValueError("nonfinite JSON token")
    value = json.loads(line.decode("utf-8"), object_pairs_hook=_unique, parse_constant=invalid)
    canonical(value)
    if not isinstance(value, dict):
        raise ValueError("JSONL record must be an object")
    return value


def fields(value: Any, expected: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("unexpected protocol fields")


def validated_action(payload: Any) -> Action:
    fields(payload, {"name", "params"})
    name, params = payload["name"], payload["params"]
    if name not in ("drive", "stop", "stand") or not isinstance(params, dict):
        raise ValueError("invalid reference-controller action")
    if (name != "drive" and params) or set(params) - {"forward_mps", "lateral_mps", "yaw_rps"}:
        raise ValueError("invalid action parameters")
    try:
        valid = all(type(v) in (int, float) and math.isfinite(v) for v in params.values())
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("action values must be finite numbers")
    if math.hypot(params.get("forward_mps", 0), params.get("lateral_mps", 0)) > .03 + 1e-12 or abs(params.get("yaw_rps", 0)) > .3:
        raise ValueError("action exceeds the body envelope")
    return Action(name, params.copy())


def worker() -> int:
    controller, session, last_sequence = None, None, -1
    previous_wire, previous_reply = None, None
    for line in iter(lambda: sys.stdin.buffer.readline(MAX_BYTES + 1), b""):
        request = None
        try:
            request = parse_line(line)
            fields(request, {"version", "session", "sequence", "operation", "payload"})
            if type(request["version"]) is not int or request["version"] != 1:
                raise ValueError("unsupported protocol version")
            if type(request["sequence"]) is not int or request["sequence"] < 0 or not isinstance(request["session"], str):
                raise ValueError("invalid session/sequence")
            if request["sequence"] == last_sequence and canonical(request) == previous_wire:
                sys.stdout.buffer.write(previous_reply)
                sys.stdout.buffer.flush()
                continue
            if controller is None:
                if request["operation"] != "init" or request["sequence"] != 0 or not request["session"]:
                    raise ValueError("first message must initialize a session")
                data = request["payload"]
                fields(data, {"policy", "seed", "config", "state"})
                controller = ReferenceController(data["policy"], data["seed"], ControllerConfig(**data["config"]))
                if data["state"] is not None:
                    restored = ReferenceController.restore(data["state"])
                    if (restored.policy, restored.seed, restored.config) != (controller.policy, controller.seed, controller.config):
                        raise ValueError("checkpoint and initialization disagree")
                    controller = restored
                session = request["session"]
                payload = {"state": controller.snapshot()}
            else:
                if request["session"] != session or request["sequence"] != last_sequence + 1 or request["operation"] != "choose":
                    raise ValueError("wrong session, sequence or operation")
                data = request["payload"]
                fields(data, {"observation", "previous_action"})
                fields(data["observation"], {"tick", "sensors", "internal"})
                if not isinstance(data["observation"]["sensors"], dict) or not isinstance(data["observation"]["internal"], dict):
                    raise ValueError("observation channels must be objects")
                observation = Observation(**data["observation"])
                previous = validated_action(data["previous_action"])
                action = controller.choose(observation, previous)
                payload = {"action": asdict(action), "state": controller.snapshot(), "decision": controller.last_decision}
            reply = {"version": 1, "session": session, "sequence": request["sequence"], "ok": True, "payload": payload}
            previous_reply = (canonical(reply) + "\n").encode()
            if len(previous_reply) > MAX_BYTES:
                raise ValueError("response exceeds bound")
            sys.stdout.buffer.write(previous_reply)
            sys.stdout.buffer.flush()
            last_sequence, previous_wire = request["sequence"], canonical(request)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
            reply = {"version": 1, "session": session,
                     "sequence": request.get("sequence") if isinstance(request, dict) else None,
                     "ok": False, "payload": {"error": str(error)}}
            sys.stdout.buffer.write((canonical(reply) + "\n").encode())
            sys.stdout.buffer.flush()
            return 2
    return 0


class ProcessController:
    """A failed child is fenced until explicit restart; no command is retained."""

    def __init__(self, policy: str, seed: int = 0, config: ControllerConfig = ControllerConfig(), *,
                 timeout_s: float = .5, startup_timeout_s: float = 5.0,
                 worker_command: Sequence[str] | None = None, state: dict[str, Any] | None = None) -> None:
        if any(type(v) not in (float, int) or not math.isfinite(v) or v <= 0 for v in (timeout_s, startup_timeout_s)):
            raise ValueError("timeouts must be finite and positive")
        self.policy, self.seed, self.config = policy, seed, config
        self.timeout_s, self.startup_timeout_s = timeout_s, startup_timeout_s
        if isinstance(worker_command, (str, bytes)):
            raise ValueError("worker command must be an argument list, not shell text")
        self.command = list(worker_command) if worker_command is not None else [sys.executable, "-m", __name__, "--worker"]
        if not self.command or not all(isinstance(s, str) and s for s in self.command):
            raise ValueError("worker command must be an explicit nonempty argument list")
        self.last_state = ReferenceController(policy, seed, config).snapshot()
        self.last_decision: dict[str, Any] = {}
        self.process: subprocess.Popen | None = None
        self.failed, self.failure_reason = False, None
        self.generation, self.sequence = 0, 0
        self.buffer = b""
        self.restart(state=state)

    def _exchange(self, operation: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        if self.process is None:
            raise RuntimeError("controller process is not running")
        request = {"version": 1, "session": self.session, "sequence": self.sequence,
                   "operation": operation, "payload": payload}
        wire = (canonical(request) + "\n").encode()
        if len(wire) > MAX_BYTES:
            raise ValueError("request exceeds bound")
        pending = memoryview(wire)
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            selector.register(self.process.stdin, selectors.EVENT_WRITE)
            while True:
                if not pending and b"\n" in self.buffer:
                    line, self.buffer = self.buffer.split(b"\n", 1)
                    reply = parse_line(line)
                    fields(reply, {"version", "session", "sequence", "ok", "payload"})
                    if type(reply["version"]) is not int or reply["version"] != 1 or type(reply["sequence"]) is not int or reply["sequence"] != self.sequence or reply["session"] != self.session:
                        raise ValueError("response does not match this session/request")
                    if reply["ok"] is not True:
                        raise ValueError("worker rejected request: " + str(reply["payload"]))
                    return reply["payload"]
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("controller I/O deadline exceeded")
                for key, _ in selector.select(remaining):
                    if key.fileobj is self.process.stdin:
                        try:
                            pending = pending[os.write(key.fd, pending):]
                            if not pending:
                                selector.unregister(self.process.stdin)
                        except BlockingIOError:
                            pass
                    else:
                        try:
                            chunk = os.read(key.fd, 65_536)
                        except BlockingIOError:
                            continue
                        if not chunk:
                            raise EOFError("controller process closed its output")
                        self.buffer += chunk
                        if len(self.buffer) > MAX_BYTES:
                            raise ValueError("response exceeds bound")

    def _terminate(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=2)
        for pipe in (self.process.stdin, self.process.stdout):
            if pipe is not None:
                pipe.close()

    def _fence(self, error: Exception) -> None:
        self.failed = True
        self.failure_reason = f"{type(error).__name__}: {error}"
        self.last_decision = {"mode": "process_failure", "error": self.failure_reason,
                              "features": {"range_source": "unknown", "tracks": []}}
        self._terminate()

    def restart(self, *, state: dict[str, Any] | None = None) -> bool:
        self._terminate()
        self.generation += 1
        self.session, self.sequence = f"local:{self.generation}", 0
        self.buffer, self.failed, self.failure_reason = b"", False, None
        try:
            self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, bufsize=0, close_fds=True)
            os.set_blocking(self.process.stdin.fileno(), False)
            os.set_blocking(self.process.stdout.fileno(), False)
            reply = self._exchange("init", {"policy": self.policy, "seed": self.seed,
                "config": asdict(self.config), "state": state}, self.startup_timeout_s)
            fields(reply, {"state"})
            obj = ReferenceController.restore(reply["state"])
            if (obj.policy, obj.seed, obj.config) != (self.policy, self.seed, self.config):
                raise ValueError("worker initialized the wrong controller")
            self.last_state, self.last_decision = reply["state"], obj.last_decision
            return True
        except (OSError, ValueError, TypeError, KeyError, RuntimeError, EOFError, TimeoutError) as error:
            self._fence(error)
            return False

    def choose(self, observation: Observation, previous_action: Action = Action("stop")) -> Action:
        if self.failed:
            return Action("stop")
        try:
            self.sequence += 1
            clean = sensor_view(observation)
            reply = self._exchange("choose", {"observation": asdict(clean), "previous_action": asdict(previous_action)}, self.timeout_s)
            fields(reply, {"action", "state", "decision"})
            action = validated_action(reply["action"])
            state = ReferenceController.restore(reply["state"])
            if (state.policy, state.seed, state.config) != (self.policy, self.seed, self.config) or type(state.last_tick) is not int or state.last_tick != clean.tick or state.last_action != action or state.last_decision != reply["decision"]:
                raise ValueError("worker action and checkpoint disagree")
            self.last_state, self.last_decision = reply["state"], reply["decision"]
            return action
        except (OSError, ValueError, TypeError, KeyError, RuntimeError, EOFError, TimeoutError) as error:
            self._fence(error)
            return Action("stop")

    def snapshot(self) -> dict[str, Any]:
        # JSON round-trip detaches the cached logical state from the caller.
        return json.loads(canonical(self.last_state))

    def close(self) -> None:
        self._terminate()
        self.failed = True
        self.failure_reason = "closed"

    def __enter__(self) -> ProcessController:
        return self

    def __exit__(self, *args) -> None:
        self.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", required=True)
    parser.parse_args(argv)
    return worker()


if __name__ == "__main__":
    raise SystemExit(main())
