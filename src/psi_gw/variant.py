"""Switches for implementation artefacts of the original (ADR 0015, Issue #29).

The reference mode (ADR 0010, stage 1) reproduces the Delphi original with
all its accidents: side effects of the user interface, values left on the
stack, a shadowed variable, Wine's handling of file names. Each switch here
turns one such artefact off. ``Variant()`` is the reference mode; every field
``False`` keeps the original's behaviour.

The switches are independent, so their effects on behaviour can be measured
one at a time against the baseline of the reference mode
(``scripts/baseline.py --variant ...``).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields


@dataclass(frozen=True)
class Variant:
    """Which artefacts of the original are switched off."""

    no_display_side_effects: bool = False
    """The value display at the end of a cycle computes ``EpiKomp`` for all needs,
    which draws random numbers, reinforces goal links and advances age (ADR 0011).
    Switched off: the display has no effect on Psi."""

    clean_direction_names: bool = False
    """``DirArtWert`` reads the third letter of ``lN``/``lS`` from left-over memory
    (stack residue in ``ContinueDirection``, a heap address byte in ``RememberDir``,
    ADR 0014). Switched off: ``lN`` is north, ``lS`` is south."""

    goal_in_current_situation: bool = False
    """``PlanenUndTun``'s parameter ``situation`` shadows the global ``Situation``:
    after a plan with a locomotion, the goal is looked for in the old situation.
    Switched off: in the situation Psi is in."""

    aversion_check_in_aversions: bool = False
    """``Consum`` checks whether an aversion is known in the goal list (``toGoal``)
    and links ``toAvers``; a known aversion is therefore never reinforced.
    Switched off: the check uses the aversion list."""

    background_goals_as_described: bool = False
    """``GoalGen`` takes a background goal if ``random < r - s`` with
    ``s = r - strength * threshold``, which reduces to ``random < strength * threshold``:
    the stronger the current motive, the more background goals. The book describes
    the opposite (``random < BedIn - strength * threshold``, Mechanik des
    Seelenwagens, p. 99). Switched on: ``random < s``."""

    guard_nil_dereferences: bool = False
    """The original follows pointers without checking for nil in several places
    (e.g. ``ActivateAuto`` walking a protocol chain that ends early). There it
    raises an access violation; the cycle is aborted and, because ``StartSimul``
    stays false, the life stops. The port raises ``NilDereference``. Switched on:
    the regulation step ends as failed and the life goes on (counted in
    ``PsiState.n_guarded``)."""

    real_umlaut_bitmaps: bool = False
    """Under Wine the original does not find the bitmap files with an umlaut and
    draws their names as text (ADR 0013). Switched off: the files are used."""

    # --- Global Workspace (ADR 0016, docs/analyseplan-workspace.md) ------------------------------
    # These are extensions, not artefact switches; "all" does not touch them.

    workspace: str = "off"
    """Global Workspace and the bonus of contents already in it:
    ``off`` (no workspace, condition A), ``threshold`` (bonus = selection threshold for
    all kinds of content, B), ``motive_only`` (bonus = selection threshold for motives
    only, C), ``fixed`` (bonus = ``workspace_fixed_bonus`` for all kinds, D), ``none``
    (no bonus, not even for motives, E)."""

    workspace_fixed_bonus: float = 0.0
    """Bonus in condition ``fixed`` (D)."""

    workspace_ties: str = "name"
    """Resolution of equal effective strengths at the capacity boundary: ``name`` (neuron name,
    the rule of the confirmatory study) or ``random`` (ADR 0018, own random stream from the seed)."""

    WORKSPACE_MODES = ("off", "threshold", "motive_only", "fixed", "none")

    def __post_init__(self) -> None:
        if self.workspace not in self.WORKSPACE_MODES:
            raise ValueError(f"workspace must be one of {self.WORKSPACE_MODES}, not {self.workspace!r}")
        if self.workspace_ties not in ("name", "random"):
            raise ValueError(f"workspace_ties must be 'name' or 'random', not {self.workspace_ties!r}")

    def active(self) -> list[str]:
        out = [f.name for f in fields(self) if isinstance(getattr(self, f.name), bool) and getattr(self, f.name)]
        if self.workspace != "off":
            out.append(f"workspace={self.workspace}")
            if self.workspace == "fixed":
                out.append(f"workspace_fixed_bonus={self.workspace_fixed_bonus!r}")
            if self.workspace_ties != "name":
                out.append(f"workspace_ties={self.workspace_ties}")
        return out

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_names(cls, names: list[str] | str) -> "Variant":
        """``"all"``, a comma-separated list or a list of field names.

        Boolean switches are given by name, ``"all"`` sets all of them. The
        workspace is given as ``workspace=<mode>`` and ``workspace_fixed_bonus=<value>``,
        e.g. ``"all,workspace=threshold"``.
        """
        if isinstance(names, str):
            names = [n for n in names.split(",") if n]
        switches = [f.name for f in fields(cls) if f.type in (bool, "bool")]
        kwargs: dict = {}
        for name in names:
            if name == "all":
                kwargs.update({n: True for n in switches})
            elif name.startswith("workspace="):
                kwargs["workspace"] = name.split("=", 1)[1]
            elif name.startswith("workspace_ties="):
                kwargs["workspace_ties"] = name.split("=", 1)[1]
            elif name.startswith("workspace_fixed_bonus="):
                kwargs["workspace_fixed_bonus"] = float(name.split("=", 1)[1])
            elif name in switches:
                kwargs[name] = True
            else:
                raise ValueError(f"unknown switch {name!r}; known: {switches}, workspace=<mode>")
        return cls(**kwargs)


REFERENCE = Variant()
