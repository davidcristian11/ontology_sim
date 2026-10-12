"""Scenario catalog and deterministic V2 execution planning.

Planning is separate from generation.
The existing V1 pipeline continues to generate Bluetooth data.
"""

import argparse
import hashlib
import math
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    scenario_id: str
    ecus: tuple[str, ...]
    implemented: bool = False


SCENARIOS: dict[str, ScenarioDefinition] = {
    item.scenario_id: item
    for item in (
        ScenarioDefinition(
            "bluetooth_reconnect_after_wake",
            ("HCP3", "HCP5", "ConMod"),
            True,
        ),
        ScenarioDefinition(
            "online_service_network_handover",
            ("HCP3", "ConMod"),
        ),
        ScenarioDefinition(
            "charging_session_failure",
            ("HCP5", "ConMod"),
        ),
        ScenarioDefinition(
            "infotainment_startup_sequence",
            ("HCP3", "HCP5"),
        ),
        ScenarioDefinition(
            "stale_navigation_position",
            ("HCP3", "ConMod"),
        ),
        ScenarioDefinition(
            "extended_vehicle_awake",
            ("HCP3", "HCP5", "ConMod"),
        ),
        ScenarioDefinition(
            "software_update_compatibility",
            ("HCP3", "HCP5", "ConMod"),
        ),
        ScenarioDefinition(
            "poor_network_connectivity",
            ("HCP3", "ConMod"),
        ),
    )
}


def allocate_test_executions(
    total: int,
    weights: Mapping[str, int | float],
    *,
    seed: int,
) -> dict[str, int]:
    """Allocate an exact execution budget using scenario weights.

    Weight order does not affect the result.
    The seed provides deterministic tie-breaking.
    """

    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ValueError("total must be a non-negative integer")

    if not weights:
        raise ValueError("At least one scenario weight is required")

    unknown = set(weights) - set(SCENARIOS)

    if unknown:
        raise ValueError(f"Unknown scenarios: {', '.join(sorted(unknown))}")

    for name, weight in weights.items():
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or weight < 0
        ):
            raise ValueError(f"Invalid non-negative weight for {name}: {weight!r}")

    weight_sum = math.fsum(weights.values())

    if weight_sum <= 0:
        raise ValueError("At least one scenario weight must be positive")

    names = [name for name in SCENARIOS if name in weights]

    exact = {name: total * weights[name] / weight_sum for name in names}

    counts = {name: math.floor(exact[name]) for name in names}

    remainder = total - sum(counts.values())

    def tie_break(name: str) -> str:
        payload = (f"{seed}:scenario-allocation:{name}").encode()

        return hashlib.sha256(payload).hexdigest()

    priority = sorted(
        names,
        key=lambda name: (
            -(exact[name] - counts[name]),
            tie_break(name),
            name,
        ),
    )

    for name in priority[:remainder]:
        counts[name] += 1

    return counts


def plan_from_toml(
    config_path: str | Path,
) -> dict[str, int]:
    """Preview scenario allocation without generating data."""

    with Path(config_path).open("rb") as file:
        document = tomllib.load(file)

    generator = document["generator"]

    profile_name = generator["profile"]

    total = document["profiles"][profile_name]["test_executions"]

    seed = generator["seed"]

    distribution = document.get(
        "scenario_distribution",
        {},
    )

    weights = distribution.get("weights")

    if weights is None:
        weights = {generator["scenario"]: 1}

    if not isinstance(weights, dict):
        raise TypeError("scenario_distribution.weights must be a TOML table")

    return allocate_test_executions(
        total,
        weights,
        seed=seed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview V2 scenario allocation")

    parser.add_argument(
        "--config",
        default="config/generator.toml",
    )

    args = parser.parse_args()

    counts = plan_from_toml(args.config)

    print("Scenario allocation preview (no dataset generated):")

    for name, count in counts.items():
        print(f"  {name}: {count:,}")

    print(f"Total: {sum(counts.values()):,}")


if __name__ == "__main__":
    main()
