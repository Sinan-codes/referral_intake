"""SQLite persistence for `Referral`.

One flat table. `patient_name` is the only nested model on `Referral`, so it's
stored as three plain columns rather than reaching for a JSON column or an
ORM -- there's nothing else nested to justify that. Enums and dates round-trip
through their string values (`Urgency`, `ReferralStatus`, etc. are already
`str` enums; ISO 8601 covers `date`/`datetime`), so no separate serializer
is needed beyond what's here.

`possible_duplicate` is not a column: it's a computed property on `Referral`
derived from `duplicate_group_id`, so storing it would just be a second,
driftable copy of the same fact.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from app.models.referral import PatientName, Referral, ReferralSource, ReferralStatus, Urgency

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "db.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS referrals (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    received_at TEXT NOT NULL,
    patient_raw_full_name TEXT NOT NULL,
    patient_first_name TEXT,
    patient_last_name TEXT,
    date_of_birth TEXT,
    referring_provider TEXT,
    reason TEXT,
    urgency TEXT NOT NULL,
    status TEXT NOT NULL,
    duplicate_group_id TEXT
);
"""


def get_connection(path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    # `check_same_thread=False`: this connection is opened once in the
    # lifespan and reused for the app's lifetime, but FastAPI runs sync route
    # handlers in a worker thread pool -- a different thread than the one
    # that opened it. Fine at this app's concurrency level; sqlite3 itself
    # serializes access to a single connection internally.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(_SCHEMA)
    conn.commit()


def upsert_referral(conn: sqlite3.Connection, referral: Referral) -> None:
    upsert_referrals(conn, [referral])


def upsert_referrals(conn: sqlite3.Connection, referrals: list[Referral]) -> None:
    conn.executemany(
        """
        INSERT INTO referrals (
            id, source, source_record_id, received_at,
            patient_raw_full_name, patient_first_name, patient_last_name,
            date_of_birth, referring_provider, reason, urgency, status,
            duplicate_group_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            source = excluded.source,
            source_record_id = excluded.source_record_id,
            received_at = excluded.received_at,
            patient_raw_full_name = excluded.patient_raw_full_name,
            patient_first_name = excluded.patient_first_name,
            patient_last_name = excluded.patient_last_name,
            date_of_birth = excluded.date_of_birth,
            referring_provider = excluded.referring_provider,
            reason = excluded.reason,
            urgency = excluded.urgency,
            status = excluded.status,
            duplicate_group_id = excluded.duplicate_group_id
        """,
        [_to_row(referral) for referral in referrals],
    )
    conn.commit()


def get_referral(conn: sqlite3.Connection, referral_id: str) -> Referral | None:
    row = conn.execute("SELECT * FROM referrals WHERE id = ?", (referral_id,)).fetchone()
    return _from_row(row) if row is not None else None


def list_referrals(
    conn: sqlite3.Connection,
    *,
    status: ReferralStatus | None = None,
    source: ReferralSource | None = None,
    urgency: Urgency | None = None,
    q: str | None = None,
    sort: str = "-received_at",
    limit: int | None = None,
    offset: int = 0,
) -> list[Referral]:
    where, params = _build_where(status=status, source=source, urgency=urgency, q=q)
    direction = "DESC" if sort.startswith("-") else "ASC"
    sql = f"SELECT * FROM referrals{where} ORDER BY received_at {direction}"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params = [*params, limit, offset]
    rows = conn.execute(sql, params).fetchall()
    return [_from_row(row) for row in rows]


def count_referrals(
    conn: sqlite3.Connection,
    *,
    status: ReferralStatus | None = None,
    source: ReferralSource | None = None,
    urgency: Urgency | None = None,
    q: str | None = None,
) -> int:
    where, params = _build_where(status=status, source=source, urgency=urgency, q=q)
    row = conn.execute(f"SELECT COUNT(*) AS count FROM referrals{where}", params).fetchone()
    return row["count"]


def list_referrals_in_duplicate_group(
    conn: sqlite3.Connection, duplicate_group_id: str, *, exclude_id: str | None = None
) -> list[Referral]:
    """The other referrals sharing a duplicate group -- used to populate a
    detail response's `duplicate_group`, so the referral being viewed is
    excluded from its own list of possible matches."""

    if exclude_id is None:
        rows = conn.execute(
            "SELECT * FROM referrals WHERE duplicate_group_id = ?", (duplicate_group_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM referrals WHERE duplicate_group_id = ? AND id != ?",
            (duplicate_group_id, exclude_id),
        ).fetchall()
    return [_from_row(row) for row in rows]


def update_referral_status(conn: sqlite3.Connection, referral_id: str, status: ReferralStatus) -> None:
    conn.execute(
        "UPDATE referrals SET status = ? WHERE id = ?", (status.value, referral_id)
    )
    conn.commit()


def _build_where(
    *,
    status: ReferralStatus | None,
    source: ReferralSource | None,
    urgency: Urgency | None,
    q: str | None,
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if status is not None:
        clauses.append("status = ?")
        params.append(status.value)
    if source is not None:
        clauses.append("source = ?")
        params.append(source.value)
    if urgency is not None:
        clauses.append("urgency = ?")
        params.append(urgency.value)
    if q:
        # SQLite's default LIKE only case-folds ASCII, so an accented name
        # (e.g. "Rentería") won't match a differently-cased accented query
        # -- a known limitation, not a bug, given no full-text extension is
        # wired up here.
        clauses.append("patient_raw_full_name LIKE ?")
        params.append(f"%{q}%")
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def _to_row(referral: Referral) -> tuple:
    return (
        referral.id,
        referral.source.value,
        referral.source_record_id,
        referral.received_at.isoformat(),
        referral.patient_name.raw_full_name,
        referral.patient_name.first_name,
        referral.patient_name.last_name,
        referral.date_of_birth.isoformat() if referral.date_of_birth else None,
        referral.referring_provider,
        referral.reason,
        referral.urgency.value,
        referral.status.value,
        referral.duplicate_group_id,
    )


def _from_row(row: sqlite3.Row) -> Referral:
    return Referral(
        id=row["id"],
        source=ReferralSource(row["source"]),
        source_record_id=row["source_record_id"],
        received_at=datetime.fromisoformat(row["received_at"]),
        patient_name=PatientName(
            raw_full_name=row["patient_raw_full_name"],
            first_name=row["patient_first_name"],
            last_name=row["patient_last_name"],
        ),
        date_of_birth=date.fromisoformat(row["date_of_birth"]) if row["date_of_birth"] else None,
        referring_provider=row["referring_provider"],
        reason=row["reason"],
        urgency=Urgency(row["urgency"]),
        status=ReferralStatus(row["status"]),
        duplicate_group_id=row["duplicate_group_id"],
    )
