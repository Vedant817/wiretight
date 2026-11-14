"""Shared validated policy value types and safe parsing; authority is WebAuthn only."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class PolicyError(RuntimeError):
    """A policy was refused. Fatal: the process must not start on it.

    The message always names the offending control or key, because an operator
    fixing a policy file needs to know which line to change.
    """


@dataclass(frozen=True)
class LoadedPolicy:
    """A policy that passed every gate."""

    path: Path
    policy: dict[str, Any]
    sha256: str
    signatures: tuple[dict[str, Any], ...] = ()

    @property
    def entity_id(self) -> str:
        return str(self.policy["entity_id"])

    @property
    def base_currency(self) -> str:
        return str(self.policy["base_currency"])

    @property
    def t0_enabled(self) -> bool:
        return bool(self.policy.get("t0", {}).get("enabled", False))

    def roster(self) -> list[dict[str, Any]]:
        return list(self.policy.get("roster", []))

    def approvers(self) -> list[dict[str, Any]]:
        return [entry for entry in self.roster() if entry.get("role") == "approver"]

    def reserve_floor(self) -> dict[str, Any]:
        return dict(self.policy.get("reserve_floor", {}))


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _reject_unsafe_yaml(text: str, path: Path) -> dict[str, Any]:
    """Parse with ``safe_load`` and refuse tags and merge keys.

    ``safe_load`` already refuses ``!!python/...`` tags by raising. Anchors and
    merge keys are the subtler case: a policy can be built from an anchor whose
    contents the floor never sees as an explicit key, so they are refused
    outright rather than trusted.
    """
    if "<<" in text and ":" in text:
        raise PolicyError(f"{path}: YAML merge keys are not allowed in a policy file")
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PolicyError(f"{path}: not valid YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise PolicyError(f"{path}: a policy must be a mapping, got {type(parsed).__name__}")
    return parsed
