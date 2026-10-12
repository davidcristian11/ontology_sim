from ontologysim.generator.scenarios.registry import (
    SCENARIOS,
    allocate_test_executions,
    plan_from_toml,
)


def test_catalog_has_eight_scenarios() -> None:
    assert len(SCENARIOS) == 8

    assert sum(definition.implemented for definition in SCENARIOS.values()) == 1


def test_allocation_exact_and_order_independent() -> None:
    weights = {
        "bluetooth_reconnect_after_wake": 2,
        "online_service_network_handover": 1,
        "charging_session_failure": 1,
    }

    forward = allocate_test_executions(
        103,
        weights,
        seed=20261001,
    )

    reverse = allocate_test_executions(
        103,
        dict(reversed(list(weights.items()))),
        seed=20261001,
    )

    assert forward == reverse
    assert sum(forward.values()) == 103

    assert all(count >= 0 for count in forward.values())


def test_bluetooth_only_legacy_config(
    tmp_path,
) -> None:
    path = tmp_path / "legacy.toml"

    path.write_text(
        "[generator]\n"
        'profile = "smoke"\n'
        'scenario = "bluetooth_reconnect_after_wake"\n'
        "seed = 123\n"
        "\n"
        "[profiles.smoke]\n"
        "test_executions = 20\n",
        encoding="utf-8",
    )

    assert plan_from_toml(path) == {"bluetooth_reconnect_after_wake": 20}


def test_multi_scenario_config_preview(
    tmp_path,
) -> None:
    path = tmp_path / "multi.toml"

    path.write_text(
        "[generator]\n"
        'profile = "dev"\n'
        'scenario = "bluetooth_reconnect_after_wake"\n'
        "seed = 123\n"
        "\n"
        "[profiles.dev]\n"
        "test_executions = 100\n"
        "\n"
        "[scenario_distribution.weights]\n"
        "bluetooth_reconnect_after_wake = 2\n"
        "online_service_network_handover = 1\n"
        "charging_session_failure = 1\n",
        encoding="utf-8",
    )

    assert plan_from_toml(path) == {
        "bluetooth_reconnect_after_wake": 50,
        "online_service_network_handover": 25,
        "charging_session_failure": 25,
    }
