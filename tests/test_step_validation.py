import json

import pytest
from conda import CondaError
from conda.base.context import Context
from conda.common.serialize import yaml

from conda_features.models import Feature
from conda_features.operations.discovery import validate_catalog
from conda_features.steps import EnsureChannel, SetSetting


def test_combined_settings_fail_before_mutation(tmp_path):
    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    feature = Feature(
        "invalid",
        "Invalid",
        steps=(SetSetting("always_copy", True), SetSetting("always_softlink", True)),
    )
    with pytest.raises(CondaError, match="mutually exclusive"):
        feature.enable(
            {feature.name: ("test", feature)},
            Context(search_path=(path,)),
            path,
            "user",
        )
    assert path.read_text() == "{}\n"
    assert not path.with_name(path.name + ".invalid.json").exists()


def test_channel_receipt_does_not_store_inherited_credentials(tmp_path):
    inherited = tmp_path / "inherited.yaml"
    inherited.write_text("channels: ['https://user:password@example.test/private']\n")
    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    feature = Feature("channel", "Channel", steps=(EnsureChannel("public"),))
    catalog = {feature.name: ("test", feature)}
    ctx = Context(search_path=(inherited, path))
    feature.apply(feature.enable(catalog, ctx, path, "user"), ctx)
    receipt = path.with_name(path.name + ".channel.json").read_text()
    assert "password" not in receipt
    assert "example.test" not in receipt
    ctx = Context(search_path=(inherited, path))
    feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)
    assert "channels" not in yaml.read(path=path)


def test_channel_claims_are_unique_across_features():
    features = [
        Feature(name, name, steps=(EnsureChannel("shared"),))
        for name in ("first", "second")
    ]
    with pytest.raises(CondaError, match="Channel shared.*first.*second"):
        validate_catalog(
            {feature.name: ("test", feature) for feature in features},
            Context(search_path=()),
        )


@pytest.mark.parametrize("target", [True, "true"], ids=["typed", "text"])
def test_setting_normalizes_boolean_for_check_apply_and_cleanup(tmp_path, target):
    path = tmp_path / ".condarc"
    path.write_text("offline: false\n")
    feature = Feature(
        "normalized", "Normalized", steps=(SetSetting("offline", target),)
    )
    catalog = {feature.name: ("test", feature)}
    ctx = Context(search_path=(path,))
    feature.apply(feature.enable(catalog, ctx, path, "user"), ctx)
    ctx = Context(search_path=(path,))
    assert ctx.offline is True
    assert feature.status(catalog, ctx, "user", path=path)["readiness"] == "ready"
    assert feature.enable(catalog, ctx, path, "user")["changes"] == {}
    receipt = json.loads(path.with_name(path.name + ".normalized.json").read_text())
    assert receipt["steps"]["setting:offline"]["target"] is True
    feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)
    assert Context(search_path=(path,)).offline is False


@pytest.mark.parametrize(
    "key,target,previous",
    [
        ("channel_priority", "strict", "flexible"),
        ("safety_checks", "warn", "enabled"),
        ("path_conflict", "prevent", "clobber"),
    ],
)
def test_enum_receipts_support_retry_and_reverse(tmp_path, key, target, previous):
    path = tmp_path / ".condarc"
    path.write_text(f"offline: false\n{key}: {previous}\n")
    feature = Feature(
        "enum", "Enum", steps=(SetSetting("offline", True), SetSetting(key, target))
    )
    catalog = {feature.name: ("test", feature)}
    ctx = Context(search_path=(path,))
    feature.apply(feature.enable(catalog, ctx, path, "user"), ctx)
    ctx = Context(search_path=(path,))
    assert str(getattr(ctx, key)) == target
    assert feature.enable(catalog, ctx, path, "user")["changes"] == {}
    receipt = json.loads(path.with_name(path.name + ".enum.json").read_text())
    assert receipt["steps"][f"setting:{key}"]["target"] == target
    feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)
    ctx = Context(search_path=(path,))
    assert str(getattr(ctx, key)) == previous
    assert ctx.offline is False


def test_nonserializable_step_state_rejected_before_apply(tmp_path):
    from conda_features.steps import Step, StepPlan

    class InvalidState(Step):
        id = "invalid-state"

        def check(self, ctx, path):
            return []

        def plan(self, ctx, path, operation, saved):
            return StepPlan(state={"unsupported": object()})

        def apply(self, plan, ctx, checkpoint):
            pytest.fail("Invalid state must be rejected during planning")

    path = tmp_path / ".condarc"
    path.write_text("offline: false\n")
    feature = Feature(
        "invalid", "Invalid", steps=(SetSetting("offline", True), InvalidState())
    )
    with pytest.raises(CondaError, match="invalid-state.*non-serializable"):
        feature.enable(
            {feature.name: ("test", feature)},
            Context(search_path=(path,)),
            path,
            "user",
        )
    assert path.read_text() == "offline: false\n"
    assert not path.with_name(path.name + ".invalid.json").exists()
