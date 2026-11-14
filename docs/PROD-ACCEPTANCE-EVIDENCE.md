# Acceptance evidence: count reconciliation and invariant checks

## Collection comparison requested for bf575fd versus ba02b6e

```text
git diff --stat bf575fd..HEAD -- tests
 tests/acceptance/test_compliance_index.py | 346 ++++++++-----------------
 tests/support/money_crash_worker.py       |  18 ++
 tests/unit/test_airwallex.py              |  21 ++
 tests/unit/test_config_separation.py      |   1 +
 tests/unit/test_execution_adversaries.py  | 414 ++++++++++++++++++++++++++++++
 tests/unit/test_fx_execution.py           |   9 +-
 tests/unit/test_operators_signing.py      |  30 +++
 tests/unit/test_real_decisions.py         |   2 +
 tests/unit/test_real_executor.py          |   5 +
 tests/unit/test_runtime_boundary.py       |   3 +
 tests/unit/test_worker_process_crash.py   |  59 +++++
 11 files changed, 672 insertions(+), 236 deletions(-)
```

At collection time HEAD was ba02b6e. A detached temporary worktree at bf575fd
was created under the system temporary directory. Both ran `uv run pytest --collect-only -q`;
the final line was selected (PowerShell equivalent of `tail -1`). The worktree
was removed with `git worktree remove`; removal returned exit 0.

```text
bf575fd: 965 tests collected in 5.09s
HEAD: 923 tests collected in 1.77s
```

Exact set reconciliation: **869 unchanged, 96 removed, 54 added**.
`965 - 96 + 54 = 923` collected nodes. Of 96 removals, 95 are registry
bookkeeping/placeholder nodes (59 passing checks and 36 skips), and one is the
old GBP quote-expiry parameterization (passing). The 54 additions are 32
registry checks and 22 behavior-test nodes (all passed in the recorded run).
Thus `928 - 59 - 1 + 32 + 22 = 922` passes; `37 - 36 = 1` skip.
No pre-existing behavior test was dropped: the sole removed behavior node was
expanded into two quote-expiry cases. The old completeness and description
bookkeeping guarantees were missing from the rewrite and have now been restored.

The current stretch adds further mutation-sensitive tests; its final full-suite
total is recorded in PROD-STATUS.md separately from this historical comparison.

## Every removed or merged collected node

| Removed node ID | Reason / replacement |
|---|---|
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-01]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-02]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-03]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-04]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-04b]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-04c]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-05]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-06]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-07]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-08]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-09]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-10]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-10b]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-11]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-12]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-13]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-14]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-15]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-16]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-17]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-18]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-19]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-20]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-21]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-21b]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-22]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-23]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-24]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-25]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-26]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-27]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-28]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-29]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-30]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-31]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-32]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-33]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-34]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-R4a]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-R4b]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-R4c]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-R4d]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_id_has_a_test_or_is_declared_pending[T-R4e]` | Removed placeholder/old regex bookkeeping; see the per-ID replacement or authorized deletion in PROD-AUDIT.md. All active IDs now require actual collected behavior nodes. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_no_id_is_neither_tested_nor_pending` | Merged into active-case collection assertions plus active/removed disjointness and restored historical-universe check. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-01]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-02]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-03]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-04]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-04b]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-04c]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-05]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-06]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-07]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-08]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-09]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-10]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-10b]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-11]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-12]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-13]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-14]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-15]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-16]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-17]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-18]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-19]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-20]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-21]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-21b]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-22]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-23]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-24]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-25]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-26]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-27]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-28]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-29]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-30]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-31]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-32]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-33]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-34]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-R4a]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-R4b]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-R4c]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-R4d]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_pending_ids_still_belong_to_a_real_id[T-R4e]` | Removed redundant tautology: this parameter came directly from ALL_IDS, then asserted membership in ALL_IDS. Replaced by historical-universe and active/removed checks. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_the_never_cut_controls_all_have_tests` | Merged into collected behavior checks for every active ID. The old assertion that unbuilt controls remain pending is obsolete; retired T-21 is explicitly recorded. |
| `tests/acceptance/test_compliance_index.py::TestComplianceCoverage::test_the_pending_list_is_only_shrinking` | Deleted obsolete PENDING bookkeeping. Every active case now requires a collected behavior test. |
| `tests/acceptance/test_compliance_index.py::TestSpecIndexIsFaithful::test_every_id_has_a_description` | Description/milestone validation restored in test_registry_has_no_silent_or_deferred_cases. |
| `tests/acceptance/test_compliance_index.py::TestSpecIndexIsFaithful::test_every_r4_addition_is_present` | Merged into the restored historical-universe check, including R4 and lettered sub-IDs. |
| `tests/acceptance/test_compliance_index.py::TestSpecIndexIsFaithful::test_no_marker_names_an_id_the_index_does_not_contain` | Merged into AST-based registry marker whitelist; class/function decorators only. |
| `tests/acceptance/test_compliance_index.py::TestSpecIndexIsFaithful::test_the_index_covers_t01_through_t34` | Original-ID completeness restored in test_registry_has_no_silent_or_deferred_cases: active plus explicitly removed must equal the historical universe. |
| `tests/acceptance/test_compliance_index.py::TestSpecIndexIsFaithful::test_the_index_has_no_duplicates` | Merged into test_registry_has_no_silent_or_deferred_cases duplicate assertion. |
| `tests/acceptance/test_compliance_index.py::TestSpecIndexIsFaithful::test_the_t09_sub_ids_all_belong_to_t09` | Merged into registry whitelist allowing only T-09a/b/c/d and retaining T-09 in the historical universe. |
| `tests/unit/test_fx_execution.py::test_quote_expiry_requires_new_quote_and_new_human_approval[GBP]` | Expanded into [-1-GBP] and [60-GBP]: preserves expired-quote behavior and adds the safety-margin case. |

## Every added collected node in that comparison

- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-02]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-03]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-04]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-04b]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-04c]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-06]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-07]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-08]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-09]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-10]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-10b]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-11]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-12]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-13]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-15]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-16]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-17]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-19]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-21b]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-23]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-24]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-25]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-27]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-28]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-29]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-31]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-32]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-34]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-R4a]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-R4b]`
- `tests/acceptance/test_compliance_index.py::test_active_case_has_a_collected_behavior_test[T-R4e]`
- `tests/acceptance/test_compliance_index.py::test_registry_has_no_silent_or_deferred_cases`
- `tests/unit/test_airwallex.py::test_redirect_is_never_followed_and_ambient_proxy_is_not_used`
- `tests/unit/test_execution_adversaries.py::test_ambiguous_payout_cannot_be_replanned_in_another_run`
- `tests/unit/test_execution_adversaries.py::test_cancel_racing_executor_has_one_transactional_winner[after_claim]`
- `tests/unit/test_execution_adversaries.py::test_cancel_racing_executor_has_one_transactional_winner[before_claim]`
- `tests/unit/test_execution_adversaries.py::test_compliance_failure_trips_halt_and_holds_the_destination`
- `tests/unit/test_execution_adversaries.py::test_control_change_after_claim_prevents_the_money_post[halt]`
- `tests/unit/test_execution_adversaries.py::test_control_change_after_claim_prevents_the_money_post[policy]`
- `tests/unit/test_execution_adversaries.py::test_control_change_after_claim_prevents_the_money_post[signed_policy]`
- `tests/unit/test_execution_adversaries.py::test_corrupt_provider_beneficiary_last_four_prevents_payout`
- `tests/unit/test_execution_adversaries.py::test_provider_clock_skew_refuses_before_any_create`
- `tests/unit/test_execution_adversaries.py::test_provider_velocity_is_partitioned_at_ist_midnight[False]`
- `tests/unit/test_execution_adversaries.py::test_provider_velocity_is_partitioned_at_ist_midnight[True]`
- `tests/unit/test_execution_adversaries.py::test_signed_callback_first_payment_is_capped_and_remainder_held`
- `tests/unit/test_execution_adversaries.py::test_tampered_cooling_deadline_cannot_override_signed_callback_window`
- `tests/unit/test_execution_adversaries.py::test_unsigned_callback_row_never_authorizes_execution`
- `tests/unit/test_execution_adversaries.py::test_uploaded_memo_claiming_phone_confirmation_cannot_create_callback`
- `tests/unit/test_execution_adversaries.py::test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused`
- `tests/unit/test_fx_execution.py::test_quote_expiry_requires_new_quote_and_new_human_approval[-1-GBP]`
- `tests/unit/test_fx_execution.py::test_quote_expiry_requires_new_quote_and_new_human_approval[60-GBP]`
- `tests/unit/test_operators_signing.py::test_duplicate_roster_email_is_not_a_second_human`
- `tests/unit/test_operators_signing.py::test_two_enabled_approvers_cannot_begin_t2_signoff`
- `tests/unit/test_worker_process_crash.py::test_kill_after_durable_claim_before_money_post_recovers_lookup_only`

## Scenario node IDs (one line per requested scenario)

- replayed approval or WebAuthn assertion: `tests/unit/test_operators_signing.py::test_real_passkey_two_person_approval_and_reverification`
- cooling-off bypass: `tests/unit/test_execution_adversaries.py::test_tampered_cooling_deadline_cannot_override_signed_callback_window`
- clock skew: `tests/unit/test_execution_adversaries.py::test_provider_clock_skew_refuses_before_any_create`
- kill between claim and POST: `tests/unit/test_worker_process_crash.py::test_kill_after_durable_claim_before_money_post_recovers_lookup_only`
- timeout plus retry with the same idempotency key: `tests/unit/test_execution_adversaries.py::test_timeout_recovery_and_retry_keep_the_original_idempotency_key`
- duplicate webhook: `tests/unit/test_execution_adversaries.py::test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused`
- out-of-order webhook: `tests/unit/test_execution_adversaries.py::test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused`
- forged webhook signature: `tests/unit/test_execution_adversaries.py::test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused`
- stale FX quote: `tests/unit/test_fx_execution.py::test_quote_expiry_requires_new_quote_and_new_human_approval[-1-GBP]`
- concurrent workers racing: `tests/unit/test_worker_process_crash.py::test_two_actual_worker_processes_cannot_double_execute`
- policy change between approval and execution: `tests/unit/test_execution_adversaries.py::test_control_change_after_claim_prevents_the_money_post[signed_policy]`
- halt mid-execution: `tests/unit/test_execution_adversaries.py::test_control_change_after_claim_prevents_the_money_post[halt]`
- cancel racing execute: `tests/unit/test_execution_adversaries.py::test_cancel_racing_executor_has_one_transactional_winner[before_claim]`, `tests/unit/test_execution_adversaries.py::test_cancel_racing_executor_has_one_transactional_winner[after_claim]`
- compliance failure tripping halt: `tests/unit/test_execution_adversaries.py::test_compliance_failure_trips_halt_and_holds_the_destination`

The webhook node asserts duplicate handling, contradictory out-of-order hints,
and signature forgery in the same real HTTP flow. It is run once, not counted as
three independent tests. The cancel scenario runs both explicit interleavings.

## Exact selected-scenario output

Command: `uv run pytest` followed by the unique node IDs above, then `-q --timeout=180 --tb=short`. No other test nodes were selected.

```text
.............                                                            [100%]
13 passed in 91.48s (0:01:31)
```

## Mutation sensitivity

Initial role-check mutation (remove the role check only in `queue_action`) survived
the pre-existing unsigned-packet test: `1 passed in 5.70s`, exit 0. Signature
validation rejected the unsigned packet independently. The code was restored
byte-for-byte, and `test_ops_cannot_queue_a_fully_approved_packet` now isolates
the role boundary using valid human signatures. A new timeout test also asserts
that every keyed lookup and POST retains the signed request ID on recovery/retry.

The repeatable opt-in runner is `uv run python -m tests.support.run_mutation_checks --run`.
It refuses a dirty tree, applies one valid Python mutation at a time, captures
pytest/JUnit call-phase failures, restores original bytes in finally, compares
SHA-256 and verifies empty `git status --porcelain` after each mutation.
A syntax/collection/setup error is not accepted as a killed mutation. Results
will be appended after the experiment; the runner itself does not claim success.

## Actual mutation results

Every mutation returned pytest exit 1 with a JUnit test-call failure and no setup/collection error. Every file was restored byte-for-byte, with identical SHA-256 before/after and empty git status after each revert.

| Mutation | Tests that failed |
|---|---|
| cooling_deadline | `tests/unit/test_execution_adversaries.py::test_tampered_cooling_deadline_cannot_override_signed_callback_window` |
| approval_consumption | `tests/unit/test_real_executor.py::test_approved_payment_executes_once_and_uses_real_boundaries` |
| idempotency_recovery_key | `tests/unit/test_execution_adversaries.py::test_timeout_recovery_and_retry_keep_the_original_idempotency_key` |
| webhook_signature | `tests/unit/test_execution_adversaries.py::test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused` |
| halt_before_post | `tests/unit/test_execution_adversaries.py::test_control_change_after_claim_prevents_the_money_post[halt]` |
| approver_role | `tests/unit/test_execution_adversaries.py::test_ops_cannot_queue_a_fully_approved_packet` |

Mutations were: bypass the effective cooling deadline; omit durable approval consumption/state update; use a new UUID for the timeout recovery lookup instead of the persisted idempotency request ID; bypass HMAC comparison; omit the executor halt guard; omit only the money-request approver-role check. The idempotency experiment targets the actual lookup-only retry after an uncertain payout; it does not claim that unsafe money POST retries are supported.

The original role-test mutation survived (exit 0), as recorded above. After adding the approved-packet test, the same mutation was killed (exit 1). No production relaxation remains. The restored positive controls passed before mutation and the full restored-tree rerun follows.

Per-round runner output:

```text
cooling_deadline -> test_tampered_cooling_deadline_cannot_override_signed_callback_window
restored bytes; git status --porcelain empty
approval_consumption -> test_approved_payment_executes_once_and_uses_real_boundaries
restored bytes; git status --porcelain empty
idempotency_recovery_key -> test_timeout_recovery_and_retry_keep_the_original_idempotency_key
restored bytes; git status --porcelain empty
webhook_signature -> test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused
restored bytes; git status --porcelain empty
halt_before_post -> test_control_change_after_claim_prevents_the_money_post[halt]
restored bytes; git status --porcelain empty
approver_role -> test_ops_cannot_queue_a_fully_approved_packet
restored bytes; git status --porcelain empty
```

### cooling_deadline exact pytest output

```text
F                                                                        [100%]
================================== FAILURES ===================================
____ test_tampered_cooling_deadline_cannot_override_signed_callback_window ____
tests\unit\test_execution_adversaries.py:163: in test_tampered_cooling_deadline_cannot_override_signed_callback_window
    with pytest.raises(packets.PaymentBlockedError, match="cooling off"):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE PaymentBlockedError
=========================== short test summary info ===========================
FAILED tests/unit/test_execution_adversaries.py::test_tampered_cooling_deadline_cannot_override_signed_callback_window
1 failed in 8.16s
```

### approval_consumption exact pytest output

```text
F                                                                        [100%]
================================== FAILURES ===================================
________ test_approved_payment_executes_once_and_uses_real_boundaries _________
tests\unit\test_real_executor.py:378: in test_approved_payment_executes_once_and_uses_real_boundaries
    assert (
E   assert 0 == 1
=========================== short test summary info ===========================
FAILED tests/unit/test_real_executor.py::test_approved_payment_executes_once_and_uses_real_boundaries
1 failed in 8.64s
```

### idempotency_recovery_key pytest output (trailing spaces stripped)

```text
F                                                                        [100%]
================================== FAILURES ===================================
______ test_timeout_recovery_and_retry_keep_the_original_idempotency_key ______
tests\unit\test_execution_adversaries.py:431: in test_timeout_recovery_and_retry_keep_the_original_idempotency_key
    assert executor.execute(packet) == "SUBMITTED"
E   AssertionError: assert 'AMBIGUOUS' == 'SUBMITTED'
E
E     - SUBMITTED
E     + AMBIGUOUS
=========================== short test summary info ===========================
FAILED tests/unit/test_execution_adversaries.py::test_timeout_recovery_and_retry_keep_the_original_idempotency_key
1 failed in 18.15s
```

### webhook_signature exact pytest output

```text
F                                                                        [100%]
================================== FAILURES ===================================
___ test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused ___
tests\unit\test_execution_adversaries.py:411: in test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused
    assert client.post("/webhooks/airwallex", content=body, headers=bad).status_code == 400
E   assert 200 == 400
E    +  where 200 = <Response [200 OK]>.status_code
E    +    where <Response [200 OK]> = post('/webhooks/airwallex', content=b'{"id": "later", "name": "payout.transfer.failed", "data": {"id": "transfer-1", "status": "FAILED"}}', headers={'x-timestamp': '1794567600000', 'x-signature': '0000000000000000000000000000000000000000000000000000000000000000'})
E    +      where post = <starlette.testclient.TestClient object at 0x000002500CD2BFE0>.post
------------------------------ Captured log call ------------------------------
{"time": "2026-11-13T11:00:00+00:00", "level": "INFO", "logger": "wiretight", "event": {"event": "http.completed", "method": "POST", "route": "/webhooks/airwallex", "status": 200}}
{"time": "2026-11-13T11:00:00+00:00", "level": "INFO", "logger": "httpx2", "event": "HTTP Request: POST http://testserver/webhooks/airwallex \"HTTP/1.1 200 OK\""}
{"time": "2026-11-13T11:00:00+00:00", "level": "INFO", "logger": "wiretight", "event": {"event": "http.completed", "method": "POST", "route": "/webhooks/airwallex", "status": 200}}
{"time": "2026-11-13T11:00:00+00:00", "level": "INFO", "logger": "httpx2", "event": "HTTP Request: POST http://testserver/webhooks/airwallex \"HTTP/1.1 200 OK\""}
{"time": "2026-11-13T11:00:00+00:00", "level": "INFO", "logger": "wiretight", "event": {"event": "http.completed", "method": "POST", "route": "/webhooks/airwallex", "status": 200}}
{"time": "2026-11-13T11:00:00+00:00", "level": "INFO", "logger": "httpx2", "event": "HTTP Request: POST http://testserver/webhooks/airwallex \"HTTP/1.1 200 OK\""}
=========================== short test summary info ===========================
FAILED tests/unit/test_execution_adversaries.py::test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused
1 failed in 12.76s
```

### halt_before_post exact pytest output

```text
F                                                                        [100%]
================================== FAILURES ===================================
________ test_control_change_after_claim_prevents_the_money_post[halt] ________
tests\unit\test_execution_adversaries.py:87: in test_control_change_after_claim_prevents_the_money_post
    with pytest.raises(RuntimeError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE RuntimeError
=========================== short test summary info ===========================
FAILED tests/unit/test_execution_adversaries.py::test_control_change_after_claim_prevents_the_money_post[halt]
1 failed in 9.32s
```

### approver_role exact pytest output

```text
F                                                                        [100%]
================================== FAILURES ===================================
________________ test_ops_cannot_queue_a_fully_approved_packet ________________
tests\unit\test_execution_adversaries.py:444: in test_ops_cannot_queue_a_fully_approved_packet
    assert response.status_code == 403, response.text
E   AssertionError: {"job_id":"c3508715-9e64-4be4-92d3-e2ede22775b4","state":"PENDING"}
E   assert 202 == 403
E    +  where 202 = <Response [202 Accepted]>.status_code
------------------------------ Captured log call ------------------------------
{"time": "2026-11-13T11:00:00+00:00", "level": "INFO", "logger": "wiretight", "event": {"event": "http.completed", "method": "POST", "route": "/api/login", "status": 200}}
{"time": "2026-11-13T11:00:00+00:00", "level": "INFO", "logger": "httpx2", "event": "HTTP Request: POST http://testserver/api/login \"HTTP/1.1 200 OK\""}
{"time": "2026-11-13T11:00:00+00:00", "level": "INFO", "logger": "wiretight", "event": {"event": "http.completed", "method": "POST", "route": "/api/approvals/{packet_id}/execute", "status": 202}}
{"time": "2026-11-13T11:00:00+00:00", "level": "INFO", "logger": "httpx2", "event": "HTTP Request: POST http://testserver/api/approvals/49950f71-1e06-4f87-a36f-4da2f0ddf15e/execute \"HTTP/1.1 202 Accepted\""}
=========================== short test summary info ===========================
FAILED tests/unit/test_execution_adversaries.py::test_ops_cannot_queue_a_fully_approved_packet
1 failed in 9.29s
```

## Clean tree after mutation restoration

Actual command/output before appending this evidence:

```text
git status
On branch demo/video
nothing to commit, working tree clean
```

Final review-tree collection (includes the two new mutation-sensitive behavior tests):

```text
uv run pytest --collect-only -q
925 tests collected in 1.69s
```

The original ba02b6e comparison remains 965 versus 923. The reviewed source at
b1bac45 adds exactly two behavior nodes, making 925; restored registry assertions
add no test-node count. Original collection logs and the complete node set diff
are retained locally under output/playwright/acceptance-evidence/.

## Final restored-tree verification

```powershell
uv run pytest tests -q --timeout=180 --tb=short 2>&1 | Tee-Object -FilePath output/playwright/acceptance-evidence/final-full-pytest.txt
exit $LASTEXITCODE
```

Exit 0; exact captured output:

```text
........................................................................ [  7%]
........................................................................ [ 15%]
........................................................................ [ 23%]
........................................................................ [ 31%]
............................................s........................... [ 38%]
........................................................................ [ 46%]
........................................................................ [ 54%]
........................................................................ [ 62%]
........................................................................ [ 70%]
........................................................................ [ 77%]
........................................................................ [ 85%]
........................................................................ [ 93%]
.............................................................            [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\live\test_airwallex_read.py:19: Read-only sandbox test requires CONFIRM_LIVE=1
924 passed, 1 skipped in 743.13s (0:12:23)
```

```text
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
112 files already formatted
uv run mypy app
Success: no issues found in 53 source files
```

Confirmed live guard (also exit 0, skipped rather than faked):

```text
uv run python -c "import os, pytest; os.environ['CONFIRM_LIVE']='1'; raise SystemExit(pytest.main(['tests/live/test_airwallex_read.py','-q','-rs']))"
SKIPPED [1] tests\live\test_airwallex_read.py:21: AWX_CLIENT_ID and AWX_API_KEY are not configured
1 skipped in 0.66s
```

Final review-tree counts reconcile to `965 - 96 + 56 = 925` collected tests:
the earlier 54 additions plus two mutation-sensitive behavior tests. Passing
counts therefore reconcile to `928 - 60 + 56 = 924`, with one live skip.
No actual monetary behavior test was deleted. The metadata assertions identified
as lost were restored, and the full suite above includes them.

Final requested test diff, including the acceptance-review additions (HEAD b1bac45; subsequent documentation commit changes no tests):

```text
git diff --stat bf575fd..HEAD -- tests
 tests/acceptance/test_compliance_index.py | 351 ++++++++---------------
 tests/support/acceptance_scenarios.json   |  87 ++++++
 tests/support/money_crash_worker.py       |  18 ++
 tests/support/run_mutation_checks.py      | 173 ++++++++++++
 tests/unit/test_airwallex.py              |  21 ++
 tests/unit/test_config_separation.py      |   1 +
 tests/unit/test_execution_adversaries.py  | 451 ++++++++++++++++++++++++++++++
 tests/unit/test_fx_execution.py           |   9 +-
 tests/unit/test_operators_signing.py      |  30 ++
 tests/unit/test_real_decisions.py         |   2 +
 tests/unit/test_real_executor.py          |   5 +
 tests/unit/test_runtime_boundary.py       |   3 +
 tests/unit/test_worker_process_crash.py   |  59 ++++
 13 files changed, 974 insertions(+), 236 deletions(-)
```

Embedded mutation-log trailing spaces are normalized for a clean patch; the raw
mutation logs in output/playwright/acceptance-evidence/mutations/ are unchanged.
