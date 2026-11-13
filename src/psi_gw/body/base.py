"""Body interface shared by the island world, 3D simulation and the PiCrawler.

The cognitive core never talks to hardware or a simulator directly. Each tick it
calls ``observe()`` once and ``act()`` once. This keeps a single PSI instance
usable across bodies without changes to the core (see docs/architecture.md).

This is a first draft. The concrete contents of observations and actions will be
fixed during the port of the island world (Inselwelt) in phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Observation:
    """What the body reports in one tick.

    Attributes:
        tick: Discrete time step the observation belongs to.
        sensors: Raw or preprocessed sensor values keyed by sensor name.
        internal: Body-internal states that feed need indicators
            (Bedürfnisindikatoren), e.g. energy or water level.
    """

    tick: int
    sensors: dict[str, Any] = field(default_factory=dict)
    internal: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """A motor command chosen by action organisation (Handlungsorganisation).

    Attributes:
        name: Symbolic action name, e.g. ``"move_north"`` or ``"drink"``.
        params: Optional parameters, e.g. speed or target position.
    """

    name: str
    params: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Body(Protocol):
    """Interface every body adapter implements."""

    def reset(self, seed: int) -> Observation:
        """Reset the body to its start state and return the first observation."""
        ...

    def observe(self) -> Observation:
        """Return the observation for the current tick."""
        ...

    def act(self, action: Action) -> None:
        """Execute an action and advance the body by one tick."""
        ...

    def available_actions(self) -> list[str]:
        """Return the names of actions this body can execute."""
        ...
