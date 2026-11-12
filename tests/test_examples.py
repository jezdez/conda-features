import importlib.util
import json
import os

import pytest
from conda.base.context import Context
from conda.common.configuration import YamlRawParameter

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("conda_features_examples") is None,
    reason="Run in the examples or integration environment",
)


def test_real_provider_catalog(conda_cli, tmp_path):
    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    out, err, code = conda_cli("feature", "list", "--file", path, "--json")
    assert code == 0, out + err
    assert {item["name"] for item in json.loads(out)["features"]} == {
        "conda-pypi",
        "conda-completion",
    }


@pytest.mark.skipif(
    importlib.util.find_spec("conda_pypi") is None,
    reason="Real provider integration environment required",
)
def test_real_pypi_enable_disable_preserves_user_configuration(conda_cli, tmp_path):
    path = tmp_path / ".condarc"
    path.write_text("# preserve\nsolver: libmamba\nchannels:\n  - conda-forge\n")

    def run(*args):
        out, err, code = conda_cli("feature", *args, "--file", path, "--json")
        assert code == 0, out + err
        return json.loads(out)

    before = path.read_bytes()
    plan = run("enable", "conda-pypi", "--dry-run")
    assert plan["changes"]["setting:solver"] == "set solver to rattler"
    assert path.read_bytes() == before
    run("enable", "conda-pypi", "--yes")
    YamlRawParameter.cache_clear()
    ctx = Context(search_path=(path,))
    assert ctx.solver == "rattler"
    assert "conda-pypi" in ctx.channels
    assert "conda-forge" in ctx.channels
    assert run("enable", "conda-pypi", "--yes")["changes"] == {}
    run("disable", "conda-pypi", "--yes")
    YamlRawParameter.cache_clear()
    ctx = Context(search_path=(path,))
    assert ctx.solver == "libmamba"
    assert "conda-pypi" not in ctx.channels
    assert "# preserve" in path.read_text()


@pytest.mark.skipif(
    importlib.util.find_spec("conda_completion") is None,
    reason="Real provider integration environment required",
)
def test_real_completion_install_and_uninstall(conda_cli, tmp_path):
    from pathlib import Path

    path = tmp_path / ".condarc"
    path.write_text("plugins:\n  feature_completion_shell: zsh\n")
    rc = Path.home() / ".zshrc"
    rc.write_text("# original shell configuration\n")

    def run(*args):
        out, err, code = conda_cli("feature", *args, "--file", path, "--json")
        assert code == 0, out + err
        return json.loads(out)

    before = rc.read_bytes()
    run("enable", "conda-completion", "--dry-run")
    assert rc.read_bytes() == before
    run("enable", "conda-completion", "--yes")
    assert "# >>> conda-completion >>>" in rc.read_text()
    assert "# original shell configuration" in rc.read_text()
    run("enable", "conda-completion", "--yes")
    rc.write_text(rc.read_text() + "# later user edit\n")
    run("disable", "conda-completion", "--yes")
    assert "conda-completion" not in rc.read_text()
    assert "# later user edit" in rc.read_text()


def test_exact_transaction_execution_and_stale_guard(monkeypatch):
    from conda import CondaError

    from conda_features.steps import InstallPackages, StepPlan, packages

    calls = []

    class Transaction:
        def download_and_extract(self):
            calls.append("download")

        def execute(self):
            calls.append("execute")

    plan = StepPlan(
        change="install", data={"installed": [], "transaction": Transaction()}
    )
    monkeypatch.setattr(packages, "installed_records", lambda: [("changed", "1", "0")])
    with pytest.raises(CondaError, match="changed"):
        InstallPackages("conda-completion").apply(plan, None, lambda state: None)
    assert calls == []
    monkeypatch.setattr(packages, "installed_records", lambda: [])
    InstallPackages("conda-completion").apply(plan, None, lambda state: None)
    assert calls == ["download", "execute"]


def test_pypi_retry_after_package_failure(tmp_path, monkeypatch):
    from conda import CondaError
    from conda_features_examples.features import conda_features

    from conda_features.steps import InstallPackages, StepPlan
    from conda_features.steps.storage import receipt_path

    feature = next(item for item in conda_features() if item.name == "conda-pypi")
    catalog = {feature.name: ("test", feature)}
    path = tmp_path / ".condarc"
    path.write_text(
        "solver: libmamba\nchannels: [conda-forge]\nproxy_servers: {https: private-value}\n"
    )
    original = path.read_bytes()
    monkeypatch.setattr(
        InstallPackages, "plan", lambda *args: StepPlan(change="install")
    )

    def fail(*args):
        raise CondaError("package failure")

    monkeypatch.setattr(InstallPackages, "apply", fail)
    ctx = Context(search_path=(path,))
    plan = feature.enable(catalog, ctx, path, "user")
    with pytest.raises(CondaError, match="package failure"):
        feature.apply(plan, ctx)
    assert path.read_bytes() == original
    assert receipt_path(path, feature.name).exists()
    monkeypatch.setattr(InstallPackages, "apply", lambda *args: None)
    feature.apply(feature.enable(catalog, ctx, path, "user"), ctx)
    assert "private-value" not in receipt_path(path, feature.name).read_text()


def test_existing_completion_hook_is_preserved(tmp_path):
    from pathlib import Path

    from conda import CondaError
    from conda_features_examples.features import conda_features

    feature = next(item for item in conda_features() if item.name == "conda-completion")
    path = tmp_path / ".condarc"
    path.write_text("plugins:\n  feature_completion_shell: zsh\n")
    rc = Path.home() / ".zshrc"
    rc.write_text("# >>> conda-completion >>>\nexisting\n# <<< conda-completion <<<\n")
    before = rc.read_bytes()
    with pytest.raises(CondaError, match="pre-existing"):
        feature.enable(
            {feature.name: ("test", feature)},
            Context(search_path=(path,)),
            path,
            "user",
        )
    assert rc.read_bytes() == before


def test_pypi_preview_hides_channel_credentials(conda_cli, tmp_path, monkeypatch):
    from conda_features.steps import InstallPackages, StepPlan

    monkeypatch.setattr(InstallPackages, "plan", lambda *args: StepPlan())
    path = tmp_path / ".condarc"
    path.write_text(
        "solver: libmamba\nchannels: ['https://user:password@example.test/private']\n"
    )
    out, err, code = conda_cli(
        "feature", "enable", "conda-pypi", "--dry-run", "--file", path, "--json"
    )
    assert code == 0, out + err
    assert "password" not in out + err
    assert "user:" not in out + err


@pytest.mark.skipif(
    importlib.util.find_spec("conda_pypi") is None,
    reason="Integration environment required",
)
def test_pypi_retry_after_configuration_write_failure(conda_cli, tmp_path, monkeypatch):
    from conda_features.steps import configuration

    path = tmp_path / ".condarc"
    path.write_text("solver: libmamba\nchannels: [conda-forge]\n")
    original = configuration.write_configuration

    def fail(*args):
        raise OSError("write failure")

    monkeypatch.setattr(configuration, "write_configuration", fail)
    _, _, code = conda_cli(
        "feature", "enable", "conda-pypi", "--file", path, "--yes", "--json"
    )
    assert code == 1
    monkeypatch.setattr(configuration, "write_configuration", original)
    out, err, code = conda_cli(
        "feature", "enable", "conda-pypi", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert "rattler" in path.read_text()


def test_bulk_disable_lists_deployments_without_blocking(conda_cli, tmp_path):
    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    out, err, code = conda_cli(
        "feature", "disable", "--all", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert "Disable deployment features individually" in json.loads(out)["message"]


@pytest.mark.skipif(
    importlib.util.find_spec("conda_completion") is None,
    reason="Integration environment required",
)
def test_completion_recovers_after_final_receipt_failure(
    conda_cli, tmp_path, monkeypatch
):
    from pathlib import Path

    from conda.base.context import context

    from conda_features.steps import runner

    path = tmp_path / ".condarc"
    path.write_text("plugins:\n  feature_completion_shell: zsh\n")
    original = runner.write_receipt
    calls = 0

    def fail_second(path, data):
        nonlocal calls
        calls += 1
        if calls == 5:
            raise OSError("receipt write failed")
        original(path, data)

    monkeypatch.setattr(runner, "write_receipt", fail_second)
    _, _, code = conda_cli(
        "feature", "enable", "conda-completion", "--file", path, "--yes", "--json"
    )
    assert code == 1
    assert "conda-completion" in (Path.home() / ".zshrc").read_text()
    monkeypatch.setattr(
        type(context.plugin_manager),
        "get_solver_backend",
        lambda *args: (_ for _ in ()).throw(AssertionError("disable must not solve")),
    )
    out, err, code = conda_cli(
        "feature", "disable", "conda-completion", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert "conda-completion" not in (Path.home() / ".zshrc").read_text()


@pytest.mark.skipif(
    importlib.util.find_spec("conda_pypi") is None,
    reason="Integration environment required",
)
def test_pypi_reenable_refuses_new_ownership(conda_cli, tmp_path):
    path = tmp_path / ".condarc"
    path.write_text("solver: rattler\nchannels: [conda-forge]\n")
    _, _, code = conda_cli(
        "feature", "enable", "conda-pypi", "--file", path, "--yes", "--json"
    )
    assert code == 0
    path.write_text(path.read_text().replace("rattler", "libmamba"))
    before = path.read_bytes()
    out, _, code = conda_cli(
        "feature", "enable", "conda-pypi", "--file", path, "--yes", "--json"
    )
    assert code == 1
    assert "receipt" in json.loads(out)["error"]
    assert path.read_bytes() == before


@pytest.mark.skipif(
    os.environ.get("CONDA_FEATURES_TEST_INSTALL") != "1",
    reason="Opt-in test installs packages into its disposable test runtime",
)
def test_real_missing_package_installation(conda_cli, tmp_path):
    from pathlib import Path

    from conda_features.steps.packages import missing_packages

    assert missing_packages(("conda-completion==0.3.2",)), (
        "Use a fresh examples environment"
    )
    path = tmp_path / ".condarc"
    path.write_text("plugins:\n  feature_completion_shell: zsh\n")
    out, err, code = conda_cli(
        "feature", "enable", "conda-completion", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert not missing_packages(("conda-completion==0.3.2",))
    assert "# >>> conda-completion >>>" in (Path.home() / ".zshrc").read_text()
