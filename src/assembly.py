"""Dynamic Lens Assembly — summon, interrogate, resolve, release.

Implements the 5-step assembly protocol from the universal hierarchy synthesis:
1. IDENTIFY the task's stratum
2. SUMMON 2-3 appropriate lenses
3. INTERROGATE through each summoned lens
4. RESOLVE conflicts between lenses
5. RELEASE the lenses

The guard: no more than one assembly per task. Summon, interrogate, resolve,
release, act. The lenses serve the work; the work does not serve the lenses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .hierarchy import (
    LENS_BY_ID,
    LENSES_BY_CATEGORY,
    LensCategory,
    Stratum,
    SystemHouse,
)


class ConflictResolution(Enum):
    """Resolution strategies for inter-lens conflicts."""

    DYNAMIC_SCOPING = "dynamic_scoping"      # Conflict 1: reduce active set, keep full reservoir
    PHASE_DIAGNOSIS = "phase_diagnosis"      # Conflict 2: time-dependent, not permanent
    STRATUM_SEPARATION = "stratum_separation"  # Conflict 3: different layers, not competing


@dataclass
class LensInsight:
    """What a lens reveals when interrogated against a task."""

    lens_id: str
    adds: str       # What the lens reveals about this task
    strips: str     # What the lens says to ignore
    demands: str    # What the lens says is irreducible
    critique: str   # What the lens challenges about the current approach


@dataclass
class ConflictRecord:
    """A detected conflict between two lens perspectives."""

    lens_a: str
    lens_b: str
    description: str
    resolution: ConflictResolution
    resolution_detail: str


@dataclass
class AssemblyResult:
    """The output of a complete lens assembly cycle."""

    task_description: str
    identified_stratum: Stratum
    identified_category: LensCategory
    summoned_lenses: list[SystemHouse]
    insights: list[LensInsight]
    conflicts: list[ConflictRecord]
    synthesis: str = ""
    released: bool = False

    def release(self) -> None:
        """Mark the assembly as released — insights absorbed, lenses dismissed."""
        self.released = True

    def to_dict(self) -> dict[str, Any]:
        """Export assembly result as dictionary."""
        return {
            "task": self.task_description,
            "stratum": self.identified_stratum.value,
            "category": self.identified_category.value,
            "lenses": [lens.lens_id for lens in self.summoned_lenses],
            "insights": [
                {"lens": i.lens_id, "adds": i.adds, "strips": i.strips,
                 "demands": i.demands, "critique": i.critique}
                for i in self.insights
            ],
            "conflicts": [
                {"lens_a": c.lens_a, "lens_b": c.lens_b,
                 "description": c.description,
                 "resolution": c.resolution.value,
                 "detail": c.resolution_detail}
                for c in self.conflicts
            ],
            "synthesis": self.synthesis,
            "released": self.released,
        }


# ---------------------------------------------------------------------------
# Stratum keywords for automatic identification
# ---------------------------------------------------------------------------

_STRATUM_KEYWORDS: dict[LensCategory, list[str]] = {
    LensCategory.TOOLING: [
        "implementation", "code", "build", "deploy", "ci", "test", "refactor",
        "debug", "fix", "tool", "pipeline", "schema", "config",
    ],
    LensCategory.STRUCTURE: [
        "architecture", "design", "dependency", "graph", "organ", "module",
        "structure", "layout", "hierarchy", "topology", "health",
    ],
    LensCategory.AUTHORITY: [
        "governance", "promotion", "rule", "policy", "budget", "allocat",
        "decision", "review", "approve", "enforce", "standard",
    ],
    LensCategory.FOUNDATION: [
        "philosophy", "ontolog", "meaning", "purpose", "identity", "vision",
        "mission", "principle", "belief", "doctrine", "meta",
    ],
    LensCategory.GENERATIVE: [
        "creative", "art", "aesthetic", "novel", "experiment", "chaos",
        "generate", "compose", "innovate", "explore", "play",
    ],
}


def identify_category(task_description: str) -> LensCategory:
    """Identify the appropriate lens category for a task.

    Matches task description keywords against category patterns.
    Falls back to STRUCTURE as the most general category.

    Args:
        task_description: Natural language description of the task.

    Returns:
        The most appropriate LensCategory.
    """
    desc_lower = task_description.lower()
    scores: dict[LensCategory, int] = {cat: 0 for cat in LensCategory}

    for category, keywords in _STRATUM_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                scores[category] += 1

    best = max(scores, key=lambda c: scores[c])
    if scores[best] == 0:
        return LensCategory.STRUCTURE  # default
    return best


def identify_stratum(category: LensCategory) -> Stratum:
    """Map a lens category to its primary stratum.

    Args:
        category: The identified LensCategory.

    Returns:
        The primary Stratum for this category.
    """
    mapping = {
        LensCategory.TOOLING: Stratum.SYS,
        LensCategory.STRUCTURE: Stratum.BIN,
        LensCategory.AUTHORITY: Stratum.USR,
        LensCategory.FOUNDATION: Stratum.BOOT,
        LensCategory.GENERATIVE: Stratum.DEV,
    }
    return mapping[category]


def select_lenses(
    category: LensCategory,
    max_lenses: int = 3,
    require_critic: bool = True,
    exclude: list[str] | None = None,
) -> list[SystemHouse]:
    """Select 2-3 lenses appropriate to the task category.

    Protocol rules:
    - Never more than 3 simultaneously (cognitive load)
    - Always include one that will CRITIQUE, not just affirm
    - Prefer lenses with high consilience on the question

    Args:
        category: The task's identified LensCategory.
        max_lenses: Maximum lenses to summon (default 3, never exceed).
        require_critic: Always include a lens from a different category.
        exclude: Lens IDs to exclude from selection.

    Returns:
        List of 2-3 SystemHouse lenses.
    """
    max_lenses = min(max_lenses, 3)  # hard cap
    excluded = set(exclude or [])

    # Primary: lenses matching the category
    primary = [h for h in LENSES_BY_CATEGORY.get(category, [])
               if h.lens_id not in excluded]

    selected: list[SystemHouse] = []

    # Take up to max_lenses - 1 from primary (leave room for critic)
    primary_count = max_lenses - 1 if require_critic else max_lenses
    selected.extend(primary[:primary_count])

    # Add a critic from a different category
    if require_critic and len(selected) < max_lenses:
        critic_candidates = [
            h for h in _get_critic_lenses(category)
            if h.lens_id not in excluded and h not in selected
        ]
        if critic_candidates:
            selected.append(critic_candidates[0])

    # Fill remaining slots if needed
    while len(selected) < 2 and primary:
        for h in primary:
            if h not in selected:
                selected.append(h)
                break
        else:
            break

    return selected[:max_lenses]


def _get_critic_lenses(category: LensCategory) -> list[SystemHouse]:
    """Get lenses that serve as effective critics for a given category.

    The best critic comes from a category with fundamentally different
    assumptions.
    """
    critic_mapping: dict[LensCategory, list[LensCategory]] = {
        LensCategory.TOOLING: [LensCategory.FOUNDATION, LensCategory.GENERATIVE],
        LensCategory.STRUCTURE: [LensCategory.GENERATIVE, LensCategory.AUTHORITY],
        LensCategory.AUTHORITY: [LensCategory.GENERATIVE, LensCategory.TOOLING],
        LensCategory.FOUNDATION: [LensCategory.TOOLING, LensCategory.AUTHORITY],
        LensCategory.GENERATIVE: [LensCategory.AUTHORITY, LensCategory.STRUCTURE],
    }
    critics: list[SystemHouse] = []
    for cat in critic_mapping.get(category, []):
        critics.extend(LENSES_BY_CATEGORY.get(cat, []))
    return critics


def interrogate(lens: SystemHouse, task_description: str) -> LensInsight:
    """Interrogate a task through a specific lens.

    Produces a structured insight based on the lens's built-in
    adds/strips/critique properties applied to the task context.

    Args:
        lens: The SystemHouse lens to interrogate through.
        task_description: Description of the task being analyzed.

    Returns:
        A LensInsight with the lens's perspective on the task.
    """
    return LensInsight(
        lens_id=lens.lens_id,
        adds=lens.adds,
        strips=lens.strips,
        demands=f"{lens.name} demands: {lens.adds}",
        critique=lens.critique,
    )


def detect_conflicts(insights: list[LensInsight]) -> list[ConflictRecord]:
    """Detect conflicts between lens insights.

    Uses the three canonical conflict patterns from the synthesis:
    1. Reduce vs. Preserve (dynamic scoping)
    2. More Governance vs. Ship Products (phase diagnosis)
    3. Internal Rigor vs. External Impact (stratum separation)

    Args:
        insights: List of insights from summoned lenses.

    Returns:
        List of detected conflicts with resolution strategies.
    """
    conflicts: list[ConflictRecord] = []

    # Check each pair
    for i, a in enumerate(insights):
        for b in insights[i + 1:]:
            conflict = _check_pair_conflict(a, b)
            if conflict:
                conflicts.append(conflict)

    return conflicts


def _check_pair_conflict(a: LensInsight, b: LensInsight) -> ConflictRecord | None:
    """Check if two lens insights conflict."""
    lens_a = LENS_BY_ID.get(a.lens_id)
    lens_b = LENS_BY_ID.get(b.lens_id)

    if not lens_a or not lens_b:
        return None

    # Pattern 1: Complexity reduction vs. diversity preservation
    reduction_ids = {"neuroscience", "economics", "thermodynamics"}
    diversity_ids = {"ecology", "cultural_expression", "chaos"}
    if (a.lens_id in reduction_ids and b.lens_id in diversity_ids) or \
       (b.lens_id in reduction_ids and a.lens_id in diversity_ids):
        return ConflictRecord(
            lens_a=a.lens_id,
            lens_b=b.lens_id,
            description="Reduce complexity vs. preserve diversity",
            resolution=ConflictResolution.DYNAMIC_SCOPING,
            resolution_detail=(
                "Hold 7±2 active at any moment, keep full set as reservoir. "
                "Dynamic assemblies form and dissolve per-task."
            ),
        )

    # Pattern 2: Governance vs. shipping
    governance_ids = {"governance", "academia", "sociology"}
    shipping_ids = {"economics", "the_technium", "infrastructure"}
    if (a.lens_id in governance_ids and b.lens_id in shipping_ids) or \
       (b.lens_id in governance_ids and a.lens_id in shipping_ids):
        return ConflictRecord(
            lens_a=a.lens_id,
            lens_b=b.lens_id,
            description="More governance vs. ship products",
            resolution=ConflictResolution.PHASE_DIAGNOSIS,
            resolution_detail=(
                "This is a phase transition, not a permanent conflict. "
                "Diagnose current phase and adjust governance-to-production ratio."
            ),
        )

    # Pattern 3: Internal rigor vs. external impact
    internal_ids = {"belief_systems", "metaphysics", "mathematics"}
    external_ids = {"the_noosphere", "cultural_expression"}
    if (a.lens_id in internal_ids and b.lens_id in external_ids) or \
       (b.lens_id in internal_ids and a.lens_id in external_ids):
        return ConflictRecord(
            lens_a=a.lens_id,
            lens_b=b.lens_id,
            description="Internal rigor vs. external impact",
            resolution=ConflictResolution.STRATUM_SEPARATION,
            resolution_detail=(
                "These serve different strata. Documentation is Layer 0 "
                "(architectural coherence). Products are Layer +1 "
                "(emergent value). Not competing — different mount points."
            ),
        )

    return None


def assemble(
    task_description: str,
    max_lenses: int = 3,
    exclude: list[str] | None = None,
) -> AssemblyResult:
    """Execute the full 5-step assembly protocol for a task.

    1. IDENTIFY the task's category and stratum
    2. SUMMON 2-3 appropriate lenses
    3. INTERROGATE through each summoned lens
    4. RESOLVE conflicts between lenses
    5. Return the assembly (caller RELEASES when done)

    The guard: no more than one assembly per task.

    Args:
        task_description: Natural language description of the task.
        max_lenses: Maximum lenses to summon (hard cap: 3).
        exclude: Lens IDs to exclude from selection.

    Returns:
        AssemblyResult with insights, conflicts, and resolution strategies.
    """
    # Step 1: IDENTIFY
    category = identify_category(task_description)
    stratum = identify_stratum(category)

    # Step 2: SUMMON
    lenses = select_lenses(category, max_lenses=max_lenses, exclude=exclude)

    # Step 3: INTERROGATE
    insights = [interrogate(lens, task_description) for lens in lenses]

    # Step 4: RESOLVE
    conflicts = detect_conflicts(insights)

    # Step 5: Package (release is caller's responsibility)
    synthesis_parts = [f"{i.lens_id}: {i.adds}" for i in insights]
    synthesis = " | ".join(synthesis_parts)

    return AssemblyResult(
        task_description=task_description,
        identified_stratum=stratum,
        identified_category=category,
        summoned_lenses=lenses,
        insights=insights,
        conflicts=conflicts,
        synthesis=synthesis,
    )
