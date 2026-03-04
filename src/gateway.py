from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

from lora_sim.sx1272 import AirChannel

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS packets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    rssi INTEGER,
    snr REAL,
    payload_hex TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_packets_device_ts ON packets(device_id, ts);
"""

@dataclass
class GatewayDB:
    path: str = "gateway.sqlite3"

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(DB_SCHEMA)
            conn.commit()

    def upsert_device(self, device_id: str, ts: str) -> None:
        with self.connect() as conn:
            row = conn.execute("SELECT device_id FROM devices WHERE device_id=?", (device_id,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO devices(device_id, first_seen, last_seen) VALUES(?,?,?)",
                    (device_id, ts, ts),
                )
            else:
                conn.execute(
                    "UPDATE devices SET last_seen=? WHERE device_id=?",
                    (ts, device_id),
                )
            conn.commit()

    def insert_packet(self, device_id: str, ts: str, payload_hex: str, rssi: Optional[int]=None, snr: Optional[float]=None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO packets(device_id, ts, rssi, snr, payload_hex) VALUES(?,?,?,?,?)",
                (device_id, ts, rssi, snr, payload_hex),
            )
            conn.commit()

    def list_devices(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
            return [dict(r) for r in rows]

    def list_packets(self, limit: int = 200) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM packets ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]


class Gateway:
    """
    AirChannel에서 payload를 수신해 DB에 저장합니다.

    payload 포맷(데모):
    - 앞 6바이트: ASCII device_id (예: DEV001)
    - 나머지: 센서 데이터(랜덤 바이트)
    """
    def __init__(self, air: AirChannel, db: GatewayDB) -> None:
        self.air = air
        self.db = db

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def process_once(self) -> bool:
        payload = self.air.poll()
        if payload is None:
            return False

        if len(payload) < 6:
            device_id = "UNKNOWN"
        else:
            device_id = payload[:6].decode("ascii", errors="replace")

        ts = self.now_iso()
        self.db.upsert_device(device_id, ts)
        self.db.insert_packet(device_id, ts, payload.hex())
        return True
