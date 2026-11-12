import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "args", [("feature", "list", "--json"), ("--json", "feature", "list")]
)
def test_installed_command_lists_empty_catalog(conda_cli, args):
    stdout, stderr, code = conda_cli(*args)
    assert code == 0, stderr
    assert json.loads(stdout)["features"] == []


def test_unknown_feature_fails_without_claiming_success(conda_cli):
    stdout, _, code = conda_cli("feature", "explain", "missing", "--json")
    assert code == 1
    assert "Unknown feature" in json.loads(stdout)["error"]


def test_registration_does_not_import_operations(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import argparse
import sys
from conda.plugins.hookspec import CondaSpecs
from conda.plugins.manager import CondaPluginManager
manager = CondaPluginManager()
manager.add_hookspecs(CondaSpecs)
assert manager.load_entrypoints('conda', name='conda-features') == 1
command, = manager.get_hook_results('subcommands')
command.configure_parser(argparse.ArgumentParser())
assert 'conda_features.operations' not in sys.modules
assert 'conda_features.operations.configuration' not in sys.modules
assert 'conda_features.cli.commands' not in sys.modules
""",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def provider_cli(tmp_path):
    # Fresh processes need the same source isolation as conda_cli tests.
    (tmp_path / "sitecustomize.py").write_text(
        "import importlib\n"
        "module = importlib.import_module('conda.base.context')\n"
        "module.SEARCH_PATH = ('~/.condarc', '$CONDA_PREFIX/.condarc', '$CONDARC')\n"
        "module.reset_context(search_path=())\n"
    )
    metadata = tmp_path / "sample_provider-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: sample-provider\nVersion: 1.0\n"
    )
    (metadata / "entry_points.txt").write_text(
        "[conda]\nsample-provider = fixture_provider\n[conda_features]\nsample-provider = fixture_provider:FEATURES\n"
    )
    rc = tmp_path / ".condarc"
    rc.write_text("{}\n")
    env = os.environ.copy()
    env.update(
        PYTHONPATH=os.pathsep.join((str(tmp_path), str(Path(__file__).parent))),
        CONDARC=str(rc),
    )

    def run(*args, target=None, json_output=True, **overrides):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "conda",
                "feature",
                *args,
                *(target or ("--file", str(rc))),
                *(("--json",) if json_output else ()),
            ],
            cwd=tmp_path,
            env={**env, **overrides},
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )

    return run, rc


def test_installed_provider_lifecycle_and_idempotence(provider_cli):
    run, rc = provider_cli
    original = rc.read_bytes()
    result = run("list")
    assert result.returncode == 0, result.stderr
    (feature,) = json.loads(result.stdout)["features"]
    assert feature["name"] == "sample"
    assert feature["requested"] == "unset"
    preview = run("enable", "sample", "--dry-run")
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert json.loads(preview.stdout)["changes"] == {"plugins.sample_enabled": True}
    assert rc.read_bytes() == original
    assert run("enable", "sample").returncode == 1
    assert rc.read_bytes() == original
    enabled = run("enable", "sample", "--yes")
    assert enabled.returncode == 0, enabled.stdout + enabled.stderr
    status = json.loads(run("explain", "sample").stdout)
    assert status["requested"] == "enabled"
    assert status["effective"] == "enabled"
    assert status["runtime"] == "unknown"
    assert status["sources"]["plugins.sample_enabled"] == [str(rc)]
    assert json.loads(run("enable", "sample", "--yes").stdout)["changes"] == {}
    configured = run("configure", "sample", "plugins.sample_limit=4", "--yes")
    assert configured.returncode == 0, configured.stdout + configured.stderr
    before = rc.read_bytes()
    assert (
        run("configure", "sample", "plugins.sample_limit=-1", "--yes").returncode == 1
    )
    assert rc.read_bytes() == before
    disabled = run("disable", "--all", "--yes")
    assert disabled.returncode == 0, disabled.stdout + disabled.stderr
    assert json.loads(run("explain", "sample").stdout)["effective"] == "disabled"
    assert "sample_limit: 4" in rc.read_text()


@pytest.mark.parametrize(
    "operation, stored, overriding",
    [("enable", True, "false"), ("disable", False, "true")],
)
@pytest.mark.parametrize("json_output", [False, True])
def test_noop_override_is_reported_without_writing(
    provider_cli, operation, stored, overriding, json_output
):
    run, rc = provider_cli
    rc.write_text(f"plugins:\n  sample_enabled: {str(stored).lower()}\n")
    before = rc.read_bytes()
    result = run(
        operation,
        "sample",
        "--yes",
        json_output=json_output,
        CONDA_PLUGINS_SAMPLE_ENABLED=overriding,
    )
    assert result.returncode == 1
    message = json.loads(result.stdout)["error"] if json_output else result.stderr
    assert "overridden" in message
    assert "envvars" in message
    assert "Change or remove" in message
    assert "No changes needed" not in result.stdout
    assert rc.read_bytes() == before


@pytest.mark.parametrize(
    "operation, stored, overriding",
    [("enable", "true", "false"), ("disable", "false", "true")],
)
def test_noop_override_in_higher_priority_file(
    provider_cli, empty_env, operation, stored, overriding
):
    run, rc = provider_cli
    destination = empty_env / ".condarc"
    destination.write_text(f"plugins:\n  sample_enabled: {stored}\n")
    rc.write_text(f"plugins:\n  sample_enabled: {overriding}\n")
    before = destination.read_bytes()
    result = run(operation, "sample", "--yes", target=("--prefix", str(empty_env)))
    assert result.returncode == 1
    assert str(rc) in json.loads(result.stdout)["error"]
    assert destination.read_bytes() == before


@pytest.mark.parametrize("extra", ["retired=True", "requires=('missing',)"])
@pytest.mark.parametrize("json_output", [False, True])
def test_blocked_provider_reports_configuration_not_runtime(
    provider_cli, extra, json_output
):
    run, rc = provider_cli
    (rc.parent / "status_provider.py").write_text(
        "from conda_features.models import Feature\n"
        f"FEATURES = (Feature('blocked', 'Blocked feature', 'offline', {extra}),)\n"
    )
    metadata = rc.parent / "status_provider-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: status-provider\nVersion: 1.0\n"
    )
    (metadata / "entry_points.txt").write_text(
        "[conda_features]\nstatus-provider = status_provider:FEATURES\n"
    )
    rc.write_text("offline: true\n")
    result = run("explain", "blocked", json_output=json_output)
    assert result.returncode == 0, result.stderr
    if json_output:
        data = json.loads(result.stdout)
        assert data["requested"] == "enabled"
        assert data["effective"] == "enabled"
        assert data["runtime"] == "unknown"
        assert data["readiness"] == "blocked"
    else:
        assert "Requested: enabled" in result.stdout
        assert "Effective setting: enabled" in result.stdout
        assert "Runtime: unknown" in result.stdout
        assert "Readiness: blocked" in result.stdout
        assert "inactive" not in result.stdout


def test_provider_environment_override_is_reported(provider_cli):
    run, rc = provider_cli
    original = rc.read_bytes()
    result = run("enable", "sample", "--yes", CONDA_PLUGINS_SAMPLE_ENABLED="false")
    assert result.returncode == 1
    assert "overrid" in json.loads(result.stdout)["error"]
    assert rc.read_bytes() == original


def test_configure_preserves_scalar_text_without_shell_interpretation(provider_cli):
    run, rc = provider_cli
    label = "a value with spaces, 'quotes', $HOME and = signs"
    result = run("configure", "sample", f"plugins.sample_label={label}", "--yes")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["changes"]["plugins.sample_label"] == label
    from conda.common.serialize import yaml

    assert yaml.read(path=rc)["plugins"]["sample_label"] == label


@pytest.mark.parametrize(
    "args",
    [
        ("disable",),
        ("disable", "sample", "--all"),
        ("configure", "sample", "invalid"),
        ("enable", "sample", "--unknown"),
    ],
)
def test_bad_arguments_do_not_mutate_config(provider_cli, args):
    run, rc = provider_cli
    original = rc.read_bytes()
    result = run(*args)
    assert result.returncode != 0
    assert rc.read_bytes() == original


def test_environment_scope_writes_only_target_prefix(provider_cli, empty_env):
    run, user_rc = provider_cli
    prefix = empty_env
    original = user_rc.read_bytes()
    enabled = run("enable", "sample", "--yes", target=("--prefix", str(prefix)))
    assert enabled.returncode == 0, enabled.stdout + enabled.stderr
    assert "sample_enabled: true" in (prefix / ".condarc").read_text()
    assert user_rc.read_bytes() == original
    result = run("explain", "sample", target=("--prefix", str(prefix)))
    assert json.loads(result.stdout)["effective"] == "enabled"


def test_invalid_prefix_is_not_created(provider_cli, tmp_path):
    run, _ = provider_cli
    prefix = tmp_path / "missing"
    result = run("enable", "sample", "--yes", target=("--prefix", str(prefix)))
    assert result.returncode == 1
    assert not prefix.exists()


def test_unrecognized_config_filename_is_rejected(provider_cli, tmp_path):
    run, _ = provider_cli
    path = tmp_path / "feature-config"
    result = run("enable", "sample", "--yes", target=("--file", str(path)))
    assert result.returncode == 1
    assert not path.exists()


@pytest.mark.parametrize(
    "entry", ["fixture_provider:FEATURES", "fixture_provider:MISSING"]
)
def test_duplicate_or_broken_provider_fails_cleanly(provider_cli, entry):
    run, rc = provider_cli
    metadata = rc.parent / "other_provider-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: other-provider\nVersion: 1.0\n"
    )
    (metadata / "entry_points.txt").write_text(
        f"[conda_features]\nother-provider = {entry}\n"
    )
    original = rc.read_bytes()
    result = run("list")
    assert result.returncode == 1
    assert "error" in json.loads(result.stdout)
    assert "Traceback" not in result.stderr
    assert rc.read_bytes() == original


@pytest.mark.parametrize(
    "declaration, message",
    [
        ("[]", "must expose a tuple"),
        ("('invalid',)", "Invalid feature declaration"),
    ],
)
def test_malformed_provider_declarations_fail_without_mutation(
    provider_cli, declaration, message
):
    run, rc = provider_cli
    (rc.parent / "invalid_provider.py").write_text(f"FEATURES = {declaration}\n")
    metadata = rc.parent / "invalid_provider-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: invalid-provider\nVersion: 1.0\n"
    )
    (metadata / "entry_points.txt").write_text(
        "[conda_features]\ninvalid-provider = invalid_provider:FEATURES\n"
    )
    before = rc.read_bytes()
    result = run("enable", "sample", "--yes")
    assert result.returncode == 1
    assert message in json.loads(result.stdout)["error"]
    assert "Traceback" not in result.stderr
    assert rc.read_bytes() == before
