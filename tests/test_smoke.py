"""Smoke tests: the package imports and the Body protocol is usable."""

import psi_gw
from psi_gw.body import Action, Body, Observation


class _NullBody:
    """Minimal body used to check the protocol, not a real environment."""

    def __init__(self) -> None:
        self._tick = 0

    def reset(self, seed: int) -> Observation:
        self._tick = 0
        return self.observe()

    def observe(self) -> Observation:
        return Observation(tick=self._tick)

    def act(self, action: Action) -> None:
        self._tick += 1

    def available_actions(self) -> list[str]:
        return ["wait"]


def test_version() -> None:
    assert psi_gw.__version__


def test_null_body_satisfies_protocol() -> None:
    body = _NullBody()
    assert isinstance(body, Body)

    first = body.reset(seed=42)
    assert first.tick == 0

    body.act(Action(name="wait"))
    assert body.observe().tick == 1
