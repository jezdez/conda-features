from dataclasses import replace

import pytest
from conda import CondaError
from conda.base.context import Context

from conda_features.models import Feature
from conda_features.operations.discovery import validate_catalog


@pytest.mark.parametrize(
    "updates, message",
    [
        ({"name": "bad id"}, "Invalid feature ID"),
        ({"maturity": "unknown"}, "Invalid maturity"),
        ({"scopes": ()}, "Invalid scopes"),
        ({"scopes": ("global",)}, "Invalid scopes"),
        ({"required_settings": ("channel_alias",)}, "Required settings"),
        ({"settings": ("offline",)}, "Use enable/disable"),
        ({"enabled_setting": "nonexistent"}, "not registered"),
        ({"enabled_setting": "channels"}, "boolean"),
        ({"settings": ("channels",)}, "must be scalar"),
        ({"settings": ("channel_alias", "channel_alias")}, "declared more than once"),
        ({"conda_version": ">>invalid"}, "Invalid conda version"),
    ],
)
def test_invalid_declarations_are_actionable(updates, message):
    feature = replace(Feature("sample", "Sample", "offline"), **updates)
    with pytest.raises(CondaError, match=message):
        validate_catalog({feature.name: ("test", feature)}, Context(search_path=()))


def test_two_features_cannot_own_the_same_setting():
    catalog = {
        name: ("test", Feature(name, name, "offline")) for name in ("first", "second")
    }
    with pytest.raises(CondaError, match="first, second"):
        validate_catalog(catalog, Context(search_path=()))
