from argparse import Namespace
from pathlib import Path

from conda.base.context import Context

from conda_features.cli.common import confirm_and_apply
from conda_features.models import Feature
from conda_features.operations.validation import validate_catalog


class FileFeature(Feature):
    """Small real deployment used to test dispatch without installing packages."""

    def status(self, catalog, ctx, scope, visiting=(), *, path=None):
        return {
            "effective": "enabled"
            if path.with_suffix(".deployed").exists()
            else "disabled"
        }

    def enable(self, catalog, ctx, path, scope):
        return {
            "features": [self.name],
            "path": str(path),
            "scope": scope,
            "changes": {"deployment": "create file"},
        }

    def disable(self, catalog, ctx, path, scope):
        return self.enable(catalog, ctx, path, scope)

    def apply(self, plan, ctx):
        Path(plan["path"]).with_suffix(".deployed").write_text("deployed")


def test_provider_owned_apply_and_preview(tmp_path, monkeypatch):
    from conda.base.context import context

    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    feature = FileFeature("deploy", "Deploy a file")
    catalog = {feature.name: ("test", feature)}
    ctx = Context(search_path=(path,))
    validate_catalog(catalog, ctx)
    args = Namespace(file=str(path), prefix=None, system=False, dry_run=True)
    plan = feature.enable(catalog, ctx, path, "user")
    confirm_and_apply(args, catalog, ctx, plan)
    assert not path.with_suffix(".deployed").exists()
    args.dry_run = False
    monkeypatch.setattr(
        type(context), "always_yes", property(lambda self: True), raising=False
    )
    result = confirm_and_apply(args, catalog, ctx, plan)
    assert path.with_suffix(".deployed").read_text() == "deployed"
    assert result["status"][0]["effective"] == "enabled"
