"""Check the static boundary between application code and recording/test doubles."""

import ast
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    checked = 0
    for path in (root / "app").rglob("*.py"):
        relative = path.relative_to(root).as_posix()
        if relative.startswith("app/demo/"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
                if node.module == "app":
                    names.extend("app." + alias.name for alias in node.names)
            else:
                names = []
            assert not any(
                name == prefix or name.startswith(prefix + ".")
                for name in names
                for prefix in ("app.demo", "tests", "unittest.mock")
            ), relative
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"MockTransport", "MockAirwallexClient"}, relative
                if relative.startswith(("app/api/", "app/workers/")) and isinstance(
                    node.func.value, ast.Name
                ):
                    assert (node.func.value.id, node.func.attr) not in {
                        ("killswitch", "clear"),
                        ("ks", "clear"),
                        ("policy", "load_policy"),
                        ("policy", "sign_policy_bytes"),
                    }, relative
            if (
                relative.startswith(("app/api/", "app/workers/"))
                and isinstance(node, ast.ImportFrom)
                and node.module in {"app.core.policy", "app.core.killswitch"}
            ):
                assert not {alias.name for alias in node.names} & {
                    "load_policy",
                    "sign_policy_bytes",
                    "sign_clear",
                    "clear",
                }, relative
        checked += 1
    print(
        f"PASS: {checked} product modules; no recording/test imports, "
        "mock transport or legacy authority calls"
    )


if __name__ == "__main__":
    main()
