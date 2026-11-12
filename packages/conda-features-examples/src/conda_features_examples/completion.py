"""The upstream-specific part of deploying conda-completion 0.3.2."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from conda import CondaError

from conda_features.steps.block import ManagedBlock
from conda_features.steps.storage import run_conda

BLOCK = re.compile(
    r"# >>> conda-completion >>>\n.*?# <<< conda-completion <<<\n?", re.S
)


class InstallCompletionHook(ManagedBlock):
    id = "completion-hook"

    def target(self, ctx):
        shell = ctx.plugins.feature_completion_shell
        home = Path.home()
        targets = {
            "bash": next(
                (
                    home / name
                    for name in (".bashrc", ".bash_profile")
                    if (home / name).exists()
                ),
                home / ".bashrc",
            ),
            "zsh": home / ".zshrc",
            "fish": home / ".config/fish/completions/conda.fish",
            "powershell": home / ".config/powershell/Microsoft.PowerShell_profile.ps1",
        }
        if os.name == "nt":
            targets["powershell"] = next(
                (
                    home / "Documents" / directory / "Microsoft.PowerShell_profile.ps1"
                    for directory in ("PowerShell", "WindowsPowerShell")
                    if (
                        home
                        / "Documents"
                        / directory
                        / "Microsoft.PowerShell_profile.ps1"
                    ).exists()
                ),
                home / "Documents/PowerShell/Microsoft.PowerShell_profile.ps1",
            )
        return targets[shell], {
            "shell": shell,
            "cache": str(home / ".cache/conda-features/completion"),
            "target": str(targets[shell]),
        }

    def blocks(self, content):
        return BLOCK.findall(content)

    def has_marker(self, content):
        return "conda-completion" in content

    def check(self, ctx, path):
        target, options = self.target(ctx)
        reasons = (
            []
            if target.exists() and self.blocks(target.read_text())
            else ["Install the shell completion hook."]
        )
        if not (Path(options["cache"]) / "completion.msgpack").is_file():
            reasons.append("Generate shell completion data.")
        return reasons

    def render(self, options):
        run_conda(
            ["completion", "--cache-dir", options["cache"], "generate", "--no-repodata"]
        )
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from conda_completion.shell import get_shell_registry; import json, sys; shell = get_shell_registry()[sys.argv[1]]; print(json.dumps({'path': str(shell.rc_path('conda')), 'body': shell.install_body(sys.argv[2], 'conda')}))",
                options["shell"],
                options["cache"],
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise CondaError(
                "Cannot render the completion hook. No shell changes made."
            )
        hook = json.loads(result.stdout)
        # The resolver lives upstream after installation. Verify the preview path.
        if hook["path"] != options["target"]:
            raise CondaError("Upstream shell destination differs from the preview.")
        return (
            "# >>> conda-completion >>>\n"
            + hook["body"]
            + "# <<< conda-completion <<<\n"
        )

    def install(self, options):
        run_conda(
            [
                "completion",
                "--cache-dir",
                options["cache"],
                "install",
                options["shell"],
                "--no-repodata",
                "--command-name",
                "conda",
                "--yes",
            ]
        )
