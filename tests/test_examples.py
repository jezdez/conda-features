import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("conda_features_examples") is None,
    reason="Run with pixi run -e examples test-examples",
)


def test_example_catalog_and_configuration(conda_cli, tmp_path):
    path = tmp_path / ".condarc"
    path.write_text("{}\n")

    def run(*args):
        out, err, code = conda_cli("feature", *args, "--file", path, "--json")
        assert code == 0, out + err
        return json.loads(out)

    features = run("list")["features"]
    assert {feature["name"] for feature in features} == {
        "conda-pypi",
        "conda-completions",
    }
    assert all("UX example" in feature["description"] for feature in features)
    before = path.read_bytes()
    assert run("enable", "conda-pypi", "--dry-run")["changes"] == {
        "plugins.example_pypi_enabled": True
    }
    assert path.read_bytes() == before
    run("enable", "conda-pypi", "--yes")
    assert run("explain", "conda-pypi")["effective"] == "enabled"
    run(
        "configure",
        "conda-completions",
        "plugins.example_completions_shell=zsh",
        "--yes",
    )
    run("enable", "conda-completions", "--yes")
    assert run("explain", "conda-completions")["runtime"] == "unknown"
    out, _, code = conda_cli(
        "feature",
        "configure",
        "conda-completions",
        "plugins.example_completions_shell=invalid",
        "--file",
        path,
        "--yes",
        "--json",
    )
    assert code == 1 and "error" in json.loads(out)
    run("disable", "--all", "--yes")
    assert all(
        feature["effective"] == "disabled" for feature in run("list")["features"]
    )
    assert "example_completions_shell: zsh" in path.read_text()
    assert not (tmp_path / ".zshrc").exists()
