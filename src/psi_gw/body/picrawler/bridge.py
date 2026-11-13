"""Versioned, transport-independent messages and a deterministic simulated bridge.

This is a protocol testbed, not a hardware service. There are no sockets,
threads or wall-clock timers. Requests are fenced by a connection session and
monotone sequence; retries use the *same* serialized request. The endpoint
advances its body exactly once per step, applying stop when no command runs.
"""

from __future__ import annotations

import copy
import heapq
import json
import math
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Protocol

from psi_gw.body import Action, Observation

VERSION = 1
MAX_INTEGER = 2**53 - 1  # Exact in common JSON/JavaScript transports.
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_STATUSES = {"completed", "expired", "rejected"}
_REASONS = {"deadline", "stale", "wrong_session", "sequence_conflict", "sequence_gap",
            "replay_too_old", "future_tick", "queue_full", "invalid_action"}


class ProtocolError(ValueError):
    """A message is not a valid version-1 protocol value."""


class StaleObservation(ProtocolError):
    """A reply contains an observation too old for the caller's use."""


class QueueFull(RuntimeError):
    """The bounded simulated request transport has no free slot."""


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= MAX_INTEGER:
        raise ProtocolError(f"{name} must be an integer in [{minimum}, {MAX_INTEGER}]")
    return value


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ProtocolError(f"invalid {name}")
    return value


def _number(value: Any, name: str) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ProtocolError(f"{name} must be finite numeric data")
    return float(value)


def _fields(value: Any, required: set[str], optional: set[str] | None = None) -> dict:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - (optional or set()):
        raise ProtocolError(f"expected fields {sorted(required)}")
    return value


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ProtocolError(f"nonfinite JSON number {value}")


def _load(payload: str, maximum_bytes: int) -> dict:
    try:
        valid = isinstance(payload, str) and len(payload.encode("utf-8")) <= maximum_bytes
    except UnicodeError:
        valid = False
    if not valid:
        raise ProtocolError("message must be bounded UTF-8 JSON text")
    try:
        value = json.loads(payload, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (ValueError, RecursionError) as exc:
        raise ProtocolError("invalid JSON message") from exc
    if not isinstance(value, dict):
        raise ProtocolError("message must be a JSON object")
    return value


def _dump(value: dict, maximum_bytes: int) -> str:
    try:
        payload = json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError, RecursionError) as exc:
        raise ProtocolError("message contains non-JSON data") from exc
    if len(payload.encode("utf-8")) > maximum_bytes:
        raise ProtocolError("message exceeds the protocol size limit")
    return payload


def _action(value: Any) -> Action:
    data = _fields(value, {"name", "params"})
    if data["name"] not in ("drive", "stop", "stand", "tone", "sound", "speak", "stop_audio", "led") or not isinstance(data["params"], dict):
        raise ProtocolError("invalid action")
    name, params = data["name"], data["params"]
    if name in ("tone", "sound", "speak", "stop_audio", "led"):
        # Use the same strict parameter validator as the simulated hardware.
        from .peripherals import PeripheralSim
        probe = PeripheralSim()
        try:
            probe.command(name, **params)
        except (TypeError, ValueError) as error:
            raise ProtocolError("invalid peripheral action") from error
        return Action(name, copy.deepcopy(params))
    names = {"forward_mps", "lateral_mps", "yaw_rps"} if name == "drive" else set()
    if params.keys() - names:
        raise ProtocolError("unknown action parameter")
    return Action(name, {field: _number(v, field) for field, v in params.items()})


def _telemetry(value: Any) -> None:
    """Validate the explicitly simulated energy extension, without losing provenance."""
    numeric = {"open_circuit_voltage_v", "battery_voltage_v", "supply_voltage_v", "current_a",
               "power_w", "requested_power_w", "cpu_power_w", "servo_power_w", "state_of_charge",
               "cpu_temperature_c", "charge_used_ah", "energy_consumed_j", "battery_loss_j",
               "ambient_temperature_c", "cpu_load"}
    flags = {"undervoltage", "thermal_throttled", "power_limited", "powered", "battery_depleted"}
    data = _fields(value, numeric | flags | {"core_voltage_v", "shutdown_reason", "history", "source"})
    if data["source"] != "simulated":
        raise ProtocolError("this telemetry extension must identify simulated values")
    for name in numeric:
        number = _number(data[name], name)
        if name not in {"cpu_temperature_c", "ambient_temperature_c"} and number < 0:
            raise ProtocolError("negative electrical/energy quantity")
        if name in {"state_of_charge", "cpu_load"} and number > 1:
            raise ProtocolError("normalized telemetry exceeds one")
    if data["core_voltage_v"] is not None:
        raise ProtocolError("the simulator has no core-voltage measurement")
    if any(type(data[name]) is not bool for name in flags):
        raise ProtocolError("telemetry flags must be boolean")
    if data["shutdown_reason"] not in (None, "battery_empty", "power_limit", "battery_cutoff"):
        raise ProtocolError("invalid shutdown reason")
    history = _fields(data["history"], {"undervoltage", "thermal_throttled"})
    if any(type(flag) is not bool for flag in history.values()):
        raise ProtocolError("historical telemetry flags must be boolean")


def _observation(value: Any) -> Observation:
    data = _fields(value, {"tick", "sensors", "internal"})
    tick = _integer(data["tick"], "observation tick")
    sensors = _fields(data["sensors"], {"ultrasonic"}, {"camera", "telemetry", "peripherals"})
    ultrasonic = _fields(sensors["ultrasonic"], {"distance_m", "status"})
    status = ultrasonic["status"]
    if status not in ("ok", "too_close", "out_of_range", "dropout"):
        raise ProtocolError("invalid range status")
    if status == "ok":
        if _number(ultrasonic["distance_m"], "range") < 0:
            raise ProtocolError("range must be nonnegative")
    elif ultrasonic["distance_m"] is not None:
        raise ProtocolError("invalid range readings must have a null distance")
    if "camera" in sensors:
        camera = _fields(sensors["camera"], {"encoding", "width", "height", "rgb"})
        width, height = _integer(camera["width"], "width", 1), _integer(camera["height"], "height", 1)
        if camera["encoding"] != "rgb8" or width > 320 or height > 240:
            raise ProtocolError("invalid camera encoding or dimensions")
        rgb = camera["rgb"]
        if not isinstance(rgb, list) or len(rgb) != height:
            raise ProtocolError("invalid camera rows")
        for row in rgb:
            if not isinstance(row, list) or len(row) != width:
                raise ProtocolError("invalid camera row width")
            for pixel in row:
                if not isinstance(pixel, list) or len(pixel) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in pixel):
                    raise ProtocolError("invalid RGB8 pixel")
    if "telemetry" in sensors:
        _telemetry(sensors["telemetry"])
    if "peripherals" in sensors:
        peripheral = _fields(sensors["peripherals"], {"tick", "source", "speaker", "user_led",
            "user_button_down", "reset_button_down", "battery_indicator_leds",
            "microphone", "extra_connected_sensors"})
        if peripheral["source"] != "simulated" or peripheral["tick"] != tick:
            raise ProtocolError("invalid peripheral provenance or tick")
        if any(type(peripheral[k]) is not bool for k in ("user_led", "user_button_down", "reset_button_down")):
            raise ProtocolError("invalid peripheral boolean readings")
        if peripheral["battery_indicator_leds"] not in (None, 0, 1, 2) or type(peripheral["battery_indicator_leds"]) is bool:
            raise ProtocolError("invalid battery indicator")
        if peripheral["microphone"] is not None or peripheral["extra_connected_sensors"] is not None:
            raise ProtocolError("unconfirmed accessory sensor data")
        speaker = _fields(peripheral["speaker"], {"playing", "event"})
        if type(speaker["playing"]) is not bool or (speaker["playing"] != (speaker["event"] is not None)):
            raise ProtocolError("invalid speaker status")
        if speaker["event"] is not None:
            event = _fields(speaker["event"], {"mode", "payload", "start_tick", "end_tick"})
            if event["mode"] not in ("tone", "sound", "speak"):
                raise ProtocolError("invalid speaker mode")
            _integer(event["start_tick"], "audio start")
            _integer(event["end_tick"], "audio end")
            if not event["start_tick"] <= tick < event["end_tick"]:
                raise ProtocolError("invalid active audio interval")
            _action({"name": event["mode"], "params": event["payload"]})
    internal = data["internal"]
    if not isinstance(internal, dict):
        raise ProtocolError("internal readings must be an object")
    for name, value in internal.items():
        _identifier(name, "internal reading name")
        if value is not None:  # Unknown need inputs must not become a fabricated zero.
            _number(value, name)
    return Observation(tick, copy.deepcopy(sensors), copy.deepcopy(internal))


def _observation_dict(observation: Observation) -> dict:
    if not isinstance(observation, Observation):
        raise ProtocolError("expected an Observation")
    value = {"tick": observation.tick, "sensors": observation.sensors, "internal": observation.internal}
    _observation(value)
    return copy.deepcopy(value)


@dataclass(frozen=True)
class Request:
    """A command or observation request; sequence starts at 1 per session.

    Ticks use the endpoint's logical clock. A command must finish no later than
    deadline_tick; retries preserve all fields, including request_id and ticks.
    action=None requests fresh telemetry and never renews the motor watchdog.
    """

    session: str
    request_id: str
    sequence: int
    issued_tick: int
    deadline_tick: int
    action: Action | None = None

    def __post_init__(self) -> None:
        _identifier(self.session, "session")
        _identifier(self.request_id, "request id")
        _integer(self.sequence, "sequence", 1)
        _integer(self.issued_tick, "issued tick")
        _integer(self.deadline_tick, "deadline tick")
        if self.deadline_tick < self.issued_tick:
            raise ProtocolError("deadline precedes issue tick")
        if self.action is not None:
            if not isinstance(self.action, Action):
                raise ProtocolError("expected an Action")
            object.__setattr__(self, "action", _action({"name": self.action.name, "params": self.action.params}))

    @property
    def operation(self) -> str:
        return "command" if self.action is not None else "observe"

    def to_json(self) -> str:
        value = {"version": VERSION, "kind": "request", "operation": self.operation,
                 "session": self.session, "request_id": self.request_id, "sequence": self.sequence,
                 "issued_tick": self.issued_tick, "deadline_tick": self.deadline_tick,
                 "action": {"name": self.action.name, "params": self.action.params} if self.action else None}
        # Revalidate nested mutable Action.params, even after construction.
        if self.action is not None:
            _action(value["action"])
        return _dump(value, 16_384)

    @classmethod
    def from_json(cls, payload: str) -> Request:
        data = _fields(_load(payload, 16_384), {"version", "kind", "operation", "session", "request_id",
                                               "sequence", "issued_tick", "deadline_tick", "action"})
        if type(data["version"]) is not int or data["version"] != VERSION or data["kind"] != "request":
            raise ProtocolError("unsupported request version/kind")
        if data["operation"] not in ("command", "observe"):
            raise ProtocolError("unknown operation")
        if (data["operation"] == "observe") != (data["action"] is None):
            raise ProtocolError("operation and action disagree")
        action = _action(data["action"]) if data["action"] is not None else None
        return cls(data["session"], data["request_id"], data["sequence"], data["issued_tick"], data["deadline_tick"], action)


@dataclass(frozen=True)
class Reply:
    """Outcome ACK. A cached duplicate retains its original sample timestamp."""

    session: str
    request_id: str
    sequence: int
    operation: str
    status: str
    reason: str | None
    server_tick: int
    execution_tick: int | None
    observation: Observation

    def __post_init__(self) -> None:
        _identifier(self.session, "session")
        _identifier(self.request_id, "request id")
        _integer(self.sequence, "sequence", 1)
        _integer(self.server_tick, "server tick")
        if self.operation not in ("command", "observe") or not isinstance(self.status, str) or self.status not in _STATUSES:
            raise ProtocolError("invalid reply operation/status")
        if self.status == "completed":
            if self.reason is not None:
                raise ProtocolError("completed replies have no rejection reason")
        elif not isinstance(self.reason, str) or self.reason not in _REASONS:
            raise ProtocolError("invalid rejection reason")
        elif (self.status == "expired") != (self.reason in {"deadline", "stale"}):
            raise ProtocolError("reply status and reason disagree")
        if self.status == "completed" and self.operation == "command":
            _integer(self.execution_tick, "execution tick")
            if self.execution_tick > self.server_tick:
                raise ProtocolError("execution is after reply timestamp")
        elif self.execution_tick is not None:
            raise ProtocolError("unexecuted requests have no execution tick")
        object.__setattr__(self, "observation", _observation(_observation_dict(self.observation)))
        if self.observation.tick > self.server_tick:
            raise ProtocolError("observation is after reply timestamp")

    def to_json(self) -> str:
        return _dump({"version": VERSION, "kind": "ack", "session": self.session,
                      "request_id": self.request_id, "sequence": self.sequence, "operation": self.operation,
                      "status": self.status, "reason": self.reason, "server_tick": self.server_tick,
                      "execution_tick": self.execution_tick, "observation": _observation_dict(self.observation)}, 2_000_000)

    @classmethod
    def from_json(cls, payload: str) -> Reply:
        data = _fields(_load(payload, 2_000_000), {"version", "kind", "session", "request_id", "sequence",
                                                  "operation", "status", "reason", "server_tick", "execution_tick", "observation"})
        if type(data["version"]) is not int or data["version"] != VERSION or data["kind"] != "ack":
            raise ProtocolError("unsupported reply version/kind")
        return cls(data["session"], data["request_id"], data["sequence"], data["operation"], data["status"],
                   data["reason"], data["server_tick"], data["execution_tick"], _observation(data["observation"]))

    def fresh_observation(self, *, now_tick: int, max_age_ticks: int, session: str | None = None) -> Observation:
        _integer(now_tick, "now tick")
        _integer(max_age_ticks, "maximum observation age")
        if session is not None and self.session != session:
            raise ProtocolError("reply belongs to another session")
        if now_tick < self.server_tick:
            raise ProtocolError("reply timestamp is in the future")
        if now_tick - self.observation.tick > max_age_ticks:
            raise StaleObservation("observation is too old")
        return _observation(_observation_dict(self.observation))


class BridgeBody(Protocol):
    """Minimal endpoint seam. act must complete atomically or raise before commit."""

    @property
    def tick(self) -> int: ...
    def act(self, action: Action) -> None: ...
    def observe(self) -> Observation: ...


class BridgeEndpoint:
    """Session-fenced command executor with bounded pending work and retry cache.

    connect/disconnect perform one explicit stop tick. step performs exactly
    one body tick, even during idle periods; commands never retain velocity.
    Deadlines include completion, not just receipt. The watchdog is a recorded
    timeout state in addition to the unconditional idle stop.
    """

    def __init__(self, body: BridgeBody, *, watchdog_ticks: int = 5, max_command_age_ticks: int = 20,
                 max_pending: int = 8, reply_cache_size: int = 32) -> None:
        self.body = body
        self.watchdog_ticks = _integer(watchdog_ticks, "watchdog ticks", 1)
        self.max_command_age_ticks = _integer(max_command_age_ticks, "maximum command age", 1)
        self.max_pending = _integer(max_pending, "pending capacity", 1)
        self.reply_cache_size = _integer(reply_cache_size, "reply cache capacity", 1)
        self.session: str | None = None
        self._generation = 0
        self._next_sequence = 1
        self._pending: OrderedDict[int, Request] = OrderedDict()
        self._cache: OrderedDict[int, tuple[str, str]] = OrderedDict()
        self._last_command_tick = self.tick
        self.watchdog_tripped = True

    @property
    def tick(self) -> int:
        return _integer(self.body.tick, "body tick")

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def connect(self, client_id: str) -> str:
        _identifier(client_id, "client id")
        if len(client_id) > 32 or self._generation == MAX_INTEGER:
            raise ProtocolError("client id or session generation exceeds limit")
        self.session = None  # Fence old traffic before touching the body.
        self._pending.clear()
        self._cache.clear()
        self.watchdog_tripped = True
        self.body.act(Action("stop"))
        self._generation += 1
        self.session = f"{client_id}:{self._generation}"
        self._next_sequence = 1
        self._last_command_tick = self.tick
        self.watchdog_tripped = False
        return self.session

    def disconnect(self) -> None:
        self.session = None
        self._pending.clear()
        self._cache.clear()
        self.watchdog_tripped = True
        self.body.act(Action("stop"))

    def _reply(self, request: Request, status: str, reason: str | None = None,
               execution_tick: int | None = None) -> str:
        return Reply(request.session, request.request_id, request.sequence, request.operation, status, reason,
                     self.tick, execution_tick, self.body.observe()).to_json()

    def _remember(self, request: Request, reply: str) -> str:
        self._cache[request.sequence] = (request.to_json(), reply)
        while len(self._cache) > self.reply_cache_size:
            self._cache.popitem(last=False)
        return reply

    def _expired(self, request: Request, completion_tick: int) -> str | None:
        if completion_tick > request.deadline_tick:
            return "deadline"
        if completion_tick - request.issued_tick > self.max_command_age_ticks:
            return "stale"
        return None

    def _fence_failure(self) -> None:
        """Prevent retries or pending work from running after an unknown outcome."""
        self.session = None
        self._pending.clear()
        self._cache.clear()
        self.watchdog_tripped = True

    def receive(self, payload: str) -> str | None:
        """Validate and queue a request, or return an immediate outcome ACK.

        Malformed JSON has no trustworthy correlation fields and raises
        ProtocolError. A valid duplicate still pending returns None.
        """
        request = Request.from_json(payload)
        fingerprint = request.to_json()
        try:
            if request.session != self.session:
                return self._reply(request, "rejected", "wrong_session")
            if request.sequence in self._cache:
                original, reply = self._cache[request.sequence]
                return reply if original == fingerprint else self._reply(request, "rejected", "sequence_conflict")
            if request.sequence in self._pending:
                if self._pending[request.sequence].to_json() == fingerprint:
                    return None
                return self._reply(request, "rejected", "sequence_conflict")
            if request.sequence < self._next_sequence:
                return self._reply(request, "rejected", "replay_too_old")
            if request.sequence > self._next_sequence:
                return self._reply(request, "rejected", "sequence_gap")
            self._next_sequence += 1  # Every new in-order request is terminal or reserved.
            if request.issued_tick > self.tick:
                return self._remember(request, self._reply(request, "rejected", "future_tick"))
            if reason := self._expired(request, self.tick + 1):
                return self._remember(request, self._reply(request, "expired", reason))
            if len(self._pending) >= self.max_pending:
                return self._remember(request, self._reply(request, "rejected", "queue_full"))
            self._pending[request.sequence] = request
            return None
        except Exception:
            # A failed terminal ACK must not leave a consumed sequence live.
            # Malformed requests are rejected before this stateful boundary.
            self._fence_failure()
            raise

    def step(self) -> list[str]:
        """Advance one logical/body tick and emit terminal replies for that tick."""
        try:
            replies: list[str] = []
            selected: Request | None = None
            while self._pending:
                _, candidate = self._pending.popitem(last=False)
                if reason := self._expired(candidate, self.tick + 1):
                    replies.append(self._remember(candidate, self._reply(candidate, "expired", reason)))
                else:
                    selected = candidate
                    break
            action = selected.action if selected is not None and selected.action is not None else Action("stop")
            rejected = False
            try:
                self.body.act(action)
            except ValueError:
                # The body rejects out-of-envelope commands before committing state.
                if selected is None or selected.action is None:
                    raise
                rejected = True
                self.body.act(Action("stop"))
            if selected is not None:
                execution_tick = self.tick if selected.action is not None and not rejected else None
                reply = self._reply(selected, "rejected" if rejected else "completed",
                                    "invalid_action" if rejected else None, execution_tick)
                replies.append(self._remember(selected, reply))
                if selected.action is not None and not rejected:
                    self._last_command_tick = self.tick
            self.watchdog_tripped = self.session is None or self.tick - self._last_command_tick >= self.watchdog_ticks
            return replies
        except Exception:
            # act may already have committed before observation or ACK creation
            # fails. Preserve that body state, fence retries, and propagate the
            # failure instead of manufacturing an outcome ACK.
            # A real adapter must provide its own independent emergency stop.
            self._fence_failure()
            raise


class InMemoryTransport:
    """Bounded deterministic duplex link with per-send delay/drop injection.

    Request delay N means N idle endpoint ticks before receipt; execution then
    takes its one body tick. Reply delay starts at ACK creation. Dropped or
    overflowing replies can be recovered by retrying the identical request.
    """

    def __init__(self, endpoint: BridgeEndpoint, *, capacity: int = 16) -> None:
        self.endpoint = endpoint
        self.capacity = _integer(capacity, "transport capacity", 1)
        self._session: str | None = None
        self._order = 0
        self._requests: list[tuple[int, int, str, int, bool]] = []
        self._replies: list[tuple[int, int, str]] = []
        self._routes: dict[tuple[str, int, str], tuple[int, bool]] = {}
        self.request_drops = 0
        self.reply_drops = 0

    @property
    def tick(self) -> int:
        return self.endpoint.tick

    @property
    def connected(self) -> bool:
        return self._session is not None and self.endpoint.session == self._session

    @property
    def queued_counts(self) -> tuple[int, int]:
        return len(self._requests), len(self._replies)

    def _clear(self) -> None:
        self._requests.clear()
        self._replies.clear()
        self._routes.clear()

    def connect(self, client_id: str) -> str:
        self._clear()
        self._session = self.endpoint.connect(client_id)
        return self._session

    def disconnect(self) -> None:
        self._clear()
        if self.connected:
            self.endpoint.disconnect()
        self._session = None

    def send(self, payload: str, *, request_delay_ticks: int = 0, reply_delay_ticks: int = 0,
             drop_request: bool = False, drop_reply: bool = False) -> None:
        if not self.connected:
            raise ConnectionError("transport is disconnected")
        Request.from_json(payload)
        _integer(request_delay_ticks, "request delay")
        _integer(reply_delay_ticks, "reply delay")
        if type(drop_request) is not bool or type(drop_reply) is not bool:
            raise ProtocolError("drop flags must be boolean")
        if drop_request:
            self.request_drops += 1
            return
        if len(self._requests) >= self.capacity:
            raise QueueFull("request transport queue is full")
        self._order += 1
        heapq.heappush(self._requests, (self.tick + request_delay_ticks, self._order, payload,
                                      reply_delay_ticks, drop_reply))

    def _reply(self, payload: str, delay: int, drop: bool) -> None:
        if drop or len(self._replies) >= self.capacity:
            self.reply_drops += 1
            return
        self._order += 1
        heapq.heappush(self._replies, (self.tick + delay, self._order, payload))

    def step(self, ticks: int = 1) -> None:
        _integer(ticks, "step count")
        for _ in range(ticks):
            while self._requests and self._requests[0][0] <= self.tick:
                _, _, payload, delay, drop = heapq.heappop(self._requests)
                request = Request.from_json(payload)
                key = (request.session, request.sequence, request.request_id)
                reply = self.endpoint.receive(payload)
                if reply is None:
                    self._routes.setdefault(key, (delay, drop))
                else:
                    self._reply(reply, delay, drop)
            for payload in self.endpoint.step():
                reply = Reply.from_json(payload)
                key = (reply.session, reply.sequence, reply.request_id)
                delay, drop = self._routes.pop(key, (0, False))
                self._reply(payload, delay, drop)

    def receive(self) -> list[str]:
        result: list[str] = []
        while self._replies and self._replies[0][0] <= self.tick:
            _, _, payload = heapq.heappop(self._replies)
            result.append(payload)
        return result
