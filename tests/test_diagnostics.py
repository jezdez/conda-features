from __future__ import annotations

import json

import pytest
from conda import CondaError
from conda.base.context import Context
from conda.common.configuration import YamlRawParameter

from conda_features.models import Feature
from conda_features.steps import SetSetting


@pytest.fixture
def diagnostic_catalog(monkeypatch):
    from conda_features.cli import commands

    feature = Feature(
        "sample",
        "Sample",
        steps=(SetSetting("offline", True),),
        scopes=("user", "environment"),
    )
    catalog = {feature.name: ("test", feature)}
    monkeypatch.setattr(commands, "discover", lambda: catalog)
    return catalog


def test_diagnose_finds_removed_provider_from_receipt(
    conda_cli, diagnostic_catalog, tmp_path
):
    path = tmp_path / ".condarc"
    path.write_text("offline: false\n")
    feature = diagnostic_catalog["sample"][1]
    ctx = Context(search_path=(path,))
    feature.apply(feature.enable(diagnostic_catalog, ctx, path, "user"), ctx)
    diagnostic_catalog.clear()
    out, err, code = conda_cli("feature", "diagnose", "--file", path, "--json")
    assert code == 0, out + err
    (problem,) = json.loads(out)["problems"]
    assert problem["feature"] == "sample"
    assert problem["kind"] == "missing-provider"
    assert "Reinstall" in problem["message"]


def test_diagnose_reports_drift_and_repair_preserves_user_edit(
    conda_cli, diagnostic_catalog, tmp_path
):
    path = tmp_path / ".condarc"
    path.write_text("offline: false\n")
    feature = diagnostic_catalog["sample"][1]
    ctx = Context(search_path=(path,))
    feature.apply(feature.enable(diagnostic_catalog, ctx, path, "user"), ctx)
    path.write_text("offline: false\nquiet: true\n")
    YamlRawParameter.cache_clear()
    out, err, code = conda_cli("feature", "diagnose", "--file", path, "--json")
    assert code == 0, out + err
    assert json.loads(out)["problems"][0]["feature"] == "sample"
    before = path.read_bytes()
    out, _, code = conda_cli(
        "feature", "repair", "sample", "--file", path, "--yes", "--json"
    )
    assert code == 1 and "changed" in out
    assert path.read_bytes() == before


def test_repair_incomplete_setup_requires_confirmation(
    conda_cli, diagnostic_catalog, tmp_path, monkeypatch
):
    from conda_features.steps import configuration

    path = tmp_path / ".condarc"
    path.write_text("offline: false\n")
    feature = diagnostic_catalog["sample"][1]
    ctx = Context(search_path=(path,))
    write = configuration.write_configuration

    def fail(*args):
        raise OSError("interrupted")

    monkeypatch.setattr(configuration, "write_configuration", fail)
    with pytest.raises(CondaError, match="interrupted"):
        feature.apply(feature.enable(diagnostic_catalog, ctx, path, "user"), ctx)
    monkeypatch.setattr(configuration, "write_configuration", write)
    out, _, code = conda_cli("feature", "repair", "sample", "--file", path, "--json")
    assert code == 1 and "--yes" in out
    assert path.read_text() == "offline: false\n"
    out, err, code = conda_cli(
        "feature", "repair", "sample", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert Context(search_path=(path,)).offline


def test_doctor_registration_is_available(conda_cli):
    out, err, code = conda_cli("doctor", "--list")
    assert code == 0, err
    assert "features:" in out


def test_diagnostics_report_incompatible_version_and_dependency(
    conda_cli, diagnostic_catalog, tmp_path
):
    from dataclasses import replace

    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    provider, feature = diagnostic_catalog["sample"]
    diagnostic_catalog["sample"] = (
        provider,
        replace(feature, conda_version=">=999", requires=("missing",)),
    )
    out, err, code = conda_cli("feature", "diagnose", "--file", path, "--json")
    assert code == 0, out + err
    message = json.loads(out)["problems"][0]["message"]
    assert "Requires conda" in message
    assert "Missing dependency" in message


def test_doctor_fixer_respects_declined_confirmation(
    diagnostic_catalog, empty_env, monkeypatch
):
    from argparse import Namespace

    from conda_features.operations import doctor
    from conda_features.steps import configuration

    path = empty_env / ".condarc"
    path.write_text("offline: false\n")
    feature = diagnostic_catalog["sample"][1]
    ctx = Context(argparse_args=Namespace(prefix=str(empty_env)))
    write = configuration.write_configuration

    def fail(*args):
        raise OSError("interrupted")

    monkeypatch.setattr(configuration, "write_configuration", fail)
    with pytest.raises(CondaError):
        feature.apply(feature.enable(diagnostic_catalog, ctx, path, "environment"), ctx)
    monkeypatch.setattr(configuration, "write_configuration", write)
    monkeypatch.setattr(doctor, "discover", lambda: diagnostic_catalog)
    prompts = []

    def decline(message):
        from conda.exceptions import CondaSystemExit

        prompts.append(message)
        raise CondaSystemExit("Cancelled")

    from conda.exceptions import CondaSystemExit

    with pytest.raises(CondaSystemExit):
        doctor.fix(str(empty_env), Namespace(dry_run=False), decline)
    assert prompts
    assert path.read_text() == "offline: false\n"
    assert (
        doctor.fix(str(empty_env), Namespace(dry_run=False), lambda message: None) == 0
    )
    assert Context(search_path=(path,)).offline


def test_diagnostic_inspection_does_not_run_package_solver(
    conda_cli, diagnostic_catalog, tmp_path, monkeypatch
):
    from conda_features.steps import InstallPackages, packages

    diagnostic_catalog["sample"] = (
        "test",
        Feature("sample", "Sample", steps=(InstallPackages("missing"),)),
    )
    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    (tmp_path / ".condarc.sample.json").write_text('{"version": 2, "steps": {}}')
    monkeypatch.setattr(packages, "missing_packages", lambda specs: ["missing"])

    def no_plan(*args):
        pytest.fail("Diagnostics must not solve packages")

    monkeypatch.setattr(InstallPackages, "plan", no_plan)
    out, err, code = conda_cli("feature", "diagnose", "--file", path, "--json")
    assert code == 0, out + err
    assert "Install required package" in json.loads(out)["problems"][0]["message"]


@pytest.mark.parametrize(
    "saved",
    [[], {"version": 2, "steps": {"setting:offline": None}}],
    ids=["not-object", "null-step"],
)
def test_invalid_receipt_does_not_abort_diagnosis(
    conda_cli, diagnostic_catalog, tmp_path, saved
):
    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    (tmp_path / ".condarc.sample.json").write_text(json.dumps(saved))
    out, err, code = conda_cli("feature", "diagnose", "--file", path, "--json")
    assert code == 0, out + err
    assert json.loads(out)["problems"][0]["kind"] == "inspection-error"


@pytest.mark.parametrize(
    "saved",
    [[], {"version": 1, "steps": {}}, {"version": 2, "steps": {"anything": None}}],
)
def test_removed_provider_invalid_receipt_is_reported(
    conda_cli, diagnostic_catalog, tmp_path, saved
):
    diagnostic_catalog.clear()
    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    (tmp_path / ".condarc.removed.json").write_text(json.dumps(saved))
    out, err, code = conda_cli("feature", "diagnose", "--file", path, "--json")
    assert code == 0, out + err
    assert json.loads(out)["problems"][0]["kind"] == "invalid-receipt"


def test_repair_completes_unfinished_receipt_without_rewriting_resources(
    conda_cli, diagnostic_catalog, tmp_path
):
    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    receipt = tmp_path / ".condarc.sample.json"
    receipt.write_text(
        json.dumps(
            {
                "version": 2,
                "steps": {
                    "setting:offline": {
                        "owned": True,
                        "before": {"present": True, "value": False},
                        "target": True,
                    }
                },
            }
        )
    )
    before = path.read_bytes()
    out, err, code = conda_cli(
        "feature", "repair", "sample", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert (
        json.loads(receipt.read_text())["steps"]["setting:offline"]["completed"] is True
    )
    assert path.read_bytes() == before
    out, _, _ = conda_cli("feature", "diagnose", "--file", path, "--json")
    assert json.loads(out)["problems"] == []


def test_boolean_override_is_diagnosed(
    conda_cli, diagnostic_catalog, tmp_path, monkeypatch
):
    diagnostic_catalog["sample"] = ("test", Feature("sample", "Sample", "offline"))
    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    monkeypatch.setenv("CONDA_OFFLINE", "false")
    out, err, code = conda_cli("feature", "diagnose", "--file", path, "--json")
    assert code == 0, out + err
    assert json.loads(out)["problems"][0]["kind"] == "overridden"
    assert "envvars" in json.loads(out)["problems"][0]["message"]


def test_real_doctor_command_reports_local_issues_without_network(
    conda_cli, diagnostic_catalog, empty_env, monkeypatch
):
    import socket

    from conda_features.operations import doctor

    path = empty_env / ".condarc"
    path.write_text("offline: false\n")
    path.with_name(path.name + ".sample.json").write_text('{"version": 2, "steps": {}}')
    monkeypatch.setattr(doctor, "discover", lambda: diagnostic_catalog)

    def no_network(*args, **kwargs):
        pytest.fail("Doctor inspection must not contact services")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    out, err, code = conda_cli("doctor", "features", "--prefix", empty_env)
    assert code == 0, err
    assert "sample:" in out
    assert "Runtime execution and authentication were not verified" in out


def test_repair_refuses_effective_override(conda_cli, empty_env, tmp_path, monkeypatch):
    from conda_features.cli import commands

    shared = tmp_path / ".condarc"
    shared.write_text("offline: true\nquiet: false\n")
    local = empty_env / ".condarc"
    local.write_text("offline: false\nquiet: true\n")
    catalog = {
        "base": ("test", Feature("base", "Base", "offline", conflicts=("other",))),
        "other": ("test", Feature("other", "Other", "quiet")),
    }
    monkeypatch.setattr(commands, "discover", lambda: catalog)
    # Repair is refused at planning when the saved choice is already overridden.
    monkeypatch.setenv("CONDA_OFFLINE", "false")
    out, _, code = conda_cli(
        "feature", "repair", "base", "--file", shared, "--yes", "--json"
    )
    assert code == 1
    assert "overridden" in out
    assert local.read_text() == "offline: false\nquiet: true\n"


def test_missing_checkpoint_for_satisfied_step_is_diagnosed(
    conda_cli, diagnostic_catalog, tmp_path
):
    path = tmp_path / ".condarc"
    path.write_text("offline: true\nquiet: true\n")
    diagnostic_catalog["sample"] = (
        "test",
        Feature(
            "sample",
            "Sample",
            steps=(SetSetting("offline", True), SetSetting("quiet", True)),
        ),
    )
    receipt = tmp_path / ".condarc.sample.json"
    receipt.write_text(
        json.dumps(
            {
                "version": 2,
                "steps": {
                    "setting:offline": {
                        "owned": False,
                        "completed": True,
                        "target": True,
                    }
                },
            }
        )
    )
    out, err, code = conda_cli("feature", "diagnose", "--file", path, "--json")
    assert code == 0, out + err
    assert json.loads(out)["problems"][0]["kind"] == "incomplete"
