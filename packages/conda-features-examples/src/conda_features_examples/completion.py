"""Install real shell completion through conda-completion's CLI."""

import os
import re
import subprocess
import sys
from pathlib import Path

from conda import CondaError
from filelock import FileLock

from conda_features.models import Feature
from conda_features.operations.configuration import fingerprint

from .deployment import (
    install_packages,
    missing_packages,
    package_plan,
    read_receipt,
    receipt_path,
    run_conda,
    summary,
    write_receipt,
)

BLOCK = re.compile(
    r"# >>> conda-completion >>>\n.*?# <<< conda-completion <<<\n?", re.S
)


def shell_path(shell):
    home = Path.home()
    if shell == "bash":
        return next(
            (
                home / name
                for name in (".bashrc", ".bash_profile")
                if (home / name).exists()
            ),
            home / ".bashrc",
        )
    if shell == "zsh":
        return home / ".zshrc"
    if shell == "fish":
        return home / ".config/fish/completions/conda.fish"
    if os.name == "nt":
        return next(
            (
                home / "Documents" / directory / "Microsoft.PowerShell_profile.ps1"
                for directory in ("PowerShell", "WindowsPowerShell")
                if (
                    home / "Documents" / directory / "Microsoft.PowerShell_profile.ps1"
                ).exists()
            ),
            home / "Documents/PowerShell/Microsoft.PowerShell_profile.ps1",
        )
    return home / ".config/powershell/Microsoft.PowerShell_profile.ps1"


class CompletionFeature(Feature):
    def status(self, catalog, ctx, scope, visiting=(), *, path=None):
        shell = ctx.plugins.feature_completion_shell
        target = shell_path(shell)
        content = target.read_text() if target.exists() else ""
        enabled = bool(BLOCK.search(content))
        receipt = read_receipt(receipt_path(path, self.name)) if path else None
        reasons = (
            []
            if enabled
            else ["Enable to install the shell hook and generate completion data."]
        )
        reasons.extend(
            f"Install required package: {spec}"
            for spec in missing_packages(("conda-completion==0.3.2",))
        )
        if not (
            Path.home() / ".cache/conda-features/completion/completion.msgpack"
        ).is_file():
            reasons.append(
                "Completion manifest is missing. Generate completion data before using the hook."
            )
        return summary(
            self,
            catalog,
            enabled=enabled,
            reasons=reasons,
            requested="enabled" if receipt else "unset",
        )

    def enable(self, catalog, ctx, path, scope):
        return self.plan(ctx, path, scope, "enable")

    def disable(self, catalog, ctx, path, scope):
        return self.plan(ctx, path, scope, "disable")

    def plan(self, ctx, path, scope, operation):
        if scope != "user":
            raise CondaError("Shell completion supports user scope only.")
        shell = ctx.plugins.feature_completion_shell
        target = shell_path(shell)
        receipt = receipt_path(path, self.name)
        saved = read_receipt(receipt)
        fingerprint(target)
        content = target.read_text() if target.exists() else ""
        blocks = BLOCK.findall(content)
        if saved and (saved["shell"] != shell or saved["target"] != str(target)):
            raise CondaError(
                "Shell destination changed. Restore the original shell selection before disabling or retrying."
            )
        if "conda-completion" in content and not saved:
            raise CondaError(
                "A pre-existing completion hook was found. It is not owned by this provider and will be preserved."
            )
        if saved and blocks and blocks != [saved.get("block")]:
            raise CondaError(
                "Completion hook changed since deployment. User edits are preserved."
            )
        if operation == "disable" and not saved:
            raise CondaError("No owned completion deployment to disable.")
        packages = (
            package_plan(("conda-completion==0.3.2",))
            if operation == "enable"
            else {"arguments": [], "actions": {}}
        )
        cache = Path.home() / ".cache/conda-features/completion"
        changes = {}
        if packages["arguments"]:
            changes["packages"] = packages["actions"]
        if (
            operation == "disable"
            or not blocks
            or not (cache / "completion.msgpack").is_file()
        ):
            changes["shell_hook"] = f"{operation} {shell} hook in {target}"
            changes["completion_cache"] = str(cache)
        return {
            "features": [self.name],
            "operation": operation,
            "scope": scope,
            "path": str(path),
            "changes": changes,
            "packages": packages,
            "shell": shell,
            "target": str(target),
            "cache": str(cache),
            "receipt": str(receipt),
            "fingerprint": fingerprint(target),
            "receipt_fingerprint": fingerprint(receipt),
        }

    def configure(self, catalog, ctx, path, scope, settings):
        if read_receipt(receipt_path(path, self.name)):
            raise CondaError("Disable the installed hook before changing shells.")
        return super().configure(catalog, ctx, path, scope, settings)

    def apply(self, plan, ctx):
        if plan["operation"] == "configure":
            return super().apply(plan, ctx)
        target, receipt = Path(plan["target"]), Path(plan["receipt"])
        with FileLock(str(receipt) + ".lock", timeout=5):
            if (
                fingerprint(target) != plan["fingerprint"]
                or fingerprint(receipt) != plan["receipt_fingerprint"]
            ):
                raise CondaError("Shell file or receipt changed after preview. Retry.")
            install_packages(plan["packages"])
            if fingerprint(target) != plan["fingerprint"]:
                raise CondaError(
                    "Shell file changed during package installation. Packages were retained. Retry to review the new plan."
                )
            # Resolve through the newly installed provider in a fresh process.
            if plan["operation"] == "enable":
                run_conda(
                    [
                        "completion",
                        "--cache-dir",
                        plan["cache"],
                        "generate",
                        "--no-repodata",
                    ]
                )
                rendered = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from conda_completion.shell import get_shell_registry; import json, sys; shell = get_shell_registry()[sys.argv[1]]; print(json.dumps({'path': str(shell.rc_path('conda')), 'body': shell.install_body(sys.argv[2], 'conda')}))",
                        plan["shell"],
                        plan["cache"],
                    ],
                    capture_output=True,
                    text=True,
                )
                if rendered.returncode:
                    raise CondaError(
                        "Cannot render the installed completion provider's shell hook. No shell changes made."
                    )
                import json

                hook = json.loads(rendered.stdout)
                if (
                    hook["path"] != str(target)
                    or fingerprint(target) != plan["fingerprint"]
                ):
                    raise CondaError(
                        "Shell destination changed during setup. Retry to review it."
                    )
                body = hook["body"]
                expected = (
                    "# >>> conda-completion >>>\n"
                    + body
                    + "# <<< conda-completion <<<\n"
                )
                if not receipt.exists():
                    write_receipt(
                        receipt,
                        {
                            "shell": plan["shell"],
                            "target": str(target),
                            "block": expected,
                        },
                    )
                run_conda(
                    [
                        "completion",
                        "--cache-dir",
                        plan["cache"],
                        "install",
                        plan["shell"],
                        "--no-repodata",
                        "--command-name",
                        "conda",
                        "--yes",
                    ]
                )
                blocks = BLOCK.findall(target.read_text())
                if len(blocks) != 1:
                    raise CondaError(
                        "Completion command did not create one expected hook. Inspect the shell file before retrying."
                    )
                if blocks[0] != expected:
                    raise CondaError(
                        "Installed shell hook differs from the recorded hook. Preserve it for manual inspection."
                    )
                write_receipt(
                    receipt,
                    {"shell": plan["shell"], "target": str(target), "block": blocks[0]},
                )
            else:
                from .deployment import write_text

                saved = read_receipt(receipt)
                if target.exists():
                    content = target.read_text()
                    if BLOCK.findall(content) != [saved["block"]]:
                        raise CondaError(
                            "Owned shell hook changed. User edits are preserved."
                        )
                    write_text(target, content.replace(saved["block"], "", 1))
                receipt.unlink()
