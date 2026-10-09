"""Trust substrate: DB, audit chain, policy floor, kill switch, verify, plan, sign-off, recon.

FINAL.md §5.1. No network I/O belongs in this package, and it must never import
from ``app.integrations`` (asserted by an import-graph test).
"""
