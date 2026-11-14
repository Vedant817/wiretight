"""Reject test/recording dependencies throughout the product import graph."""

import ast
import importlib.abc
import importlib.util
import subprocess
import sys
from pathlib import Path

FORBIDDEN = ("tests", "scripts", "app.demo", "unittest.mock")
ROOTS = ("app.api.main", "app.workers.service", "app.workers.executor", "app.cli", "app.local")


def check_source(root: Path) -> int:
    checked = 0
    for path in (root / "app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
                names += [(node.module or "") + "." + a.name for a in node.names]
            assert not any(n == p or n.startswith(p + ".") for n in names for p in FORBIDDEN), path
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"MockTransport", "MockAirwallexClient"}, path
        checked += 1
    return checked


class RejectArchive(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == p or fullname.startswith(p + ".") for p in FORBIDDEN):
            raise AssertionError("Product imported archived dependency: " + fullname)
        return


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--import":
        sys.meta_path.insert(0, RejectArchive())
        __import__(sys.argv[2])
        from app.core import killswitch, oob, policy

        for module, names in (
            (killswitch, ("clear", "sign_clear", "TEST_KEY_SEED")),
            (policy, ("load_policy", "sign_policy_bytes", "TEST_KEY_SEED")),
            (oob, ("verify_recorder_signature", "_digest_input")),
        ):
            assert not any(hasattr(module, n) for n in names)
        return
    root = Path(__file__).resolve().parents[2]
    checked = check_source(root)
    for entry in ROOTS:
        # Isolated interpreters catch dynamic and transitive imports as well.
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--import", entry],
            cwd=root,
            check=True,
            capture_output=True,
        )
    print(
        f"PASS: {checked} product modules scanned; {len(ROOTS)} isolated entry imports; "
        "archive imports and legacy signers forbidden"
    )


if __name__ == "__main__":
    main()
