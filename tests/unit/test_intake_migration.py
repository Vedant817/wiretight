"""A legacy bank-change conflict must block migration without losing evidence."""

import sqlite3
from pathlib import Path

import pytest

from app.core import db


def test_legacy_conflicting_bank_changes_refuse_atomic_upgrade(tmp_path):
    path = tmp_path / "legacy.sqlite"
    raw = sqlite3.connect(path)
    core = Path(db.__file__).parent
    for name in ("schema.sql", "migration_002.sql", "migration_003.sql", "migration_004.sql"):
        raw.executescript((core / name).read_text(encoding="utf-8"))
    raw.executescript("""
        PRAGMA user_version=4;
        INSERT INTO user(id,name,role,email,created_at)
        VALUES('operator','Fixture','ops','fixture@example.test','2026-01-01T00:00:00+00:00');
        INSERT INTO vendor(id,legal_name_norm,display_name,category,created_at)
        VALUES('vendor','FIXTURE','Fixture','manufacturing','2026-01-01T00:00:00+00:00');
    """)
    for identifier in ("first", "second"):
        raw.execute(
            "INSERT INTO payee_change_request(id,vendor_id,source_kind,received_at,intake_user_id,"
            "requester_set,proposed_details_ref,proposed_masked,proposed_fingerprint,status) "
            "VALUES(?,'vendor','manual','2026-01-01T00:00:00+00:00','operator','[]',"
            "'details','masked','fingerprint','PENDING_CALLBACK')",
            (identifier,),
        )
    raw.commit()
    raw.close()
    with pytest.raises(sqlite3.IntegrityError):
        db.connect(path)
    raw = sqlite3.connect(path)
    assert raw.execute("PRAGMA user_version").fetchone()[0] == 4
    assert raw.execute("SELECT COUNT(*) FROM payee_change_request").fetchone()[0] == 2
    assert (
        raw.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='evidence_file'").fetchone()[0]
        == 0
    )
    raw.execute("UPDATE payee_change_request SET status='REJECTED' WHERE id='second'")
    raw.commit()
    raw.close()
    conn = db.connect(path)
    try:
        assert db.user_version(conn) == db.SCHEMA_VERSION
        assert conn.execute("SELECT COUNT(*) FROM payee_change_request").fetchone()[0] == 2
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE payee_change_request SET status='RECEIVED' WHERE id='second'")
    finally:
        conn.close()
