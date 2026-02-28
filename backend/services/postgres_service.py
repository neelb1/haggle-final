"""
Postgres Call Log Service (Render Postgres)
- Durable audit log for completed calls
- Stores transcript, outcome, savings, modulate analysis
- In-memory task store remains the real-time source of truth
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import config

logger = logging.getLogger(__name__)

# Connection pool (lazy-init)
_pool = None

DATABASE_URL = os.getenv("DATABASE_URL", "")


async def connect():
    """Initialize asyncpg connection pool."""
    global _pool
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set — Postgres call logging disabled")
        return
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
        await _create_tables()
        logger.info("Postgres connected — call logging enabled")
    except ImportError:
        logger.warning("asyncpg not installed — run: pip install asyncpg")
    except Exception as e:
        logger.error("Postgres connection failed: %s", e)


async def disconnect():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def _create_tables():
    if not _pool:
        return
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS call_logs (
                id SERIAL PRIMARY KEY,
                call_id TEXT UNIQUE,
                task_id TEXT,
                company TEXT,
                action TEXT,
                outcome TEXT,
                savings REAL DEFAULT 0,
                confirmation TEXT,
                transcript TEXT,
                modulate_analysis JSONB,
                duration_seconds REAL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bill_scans (
                id SERIAL PRIMARY KEY,
                provider TEXT,
                total_amount TEXT,
                price_change TEXT,
                line_items JSONB,
                fees JSONB,
                hidden_fees JSONB,
                task_created TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        logger.info("Postgres tables ensured")


def available() -> bool:
    return _pool is not None


async def insert_call_log(
    call_id: str,
    task_id: str = "",
    company: str = "",
    action: str = "",
    outcome: str = "",
    savings: float = 0,
    confirmation: str = "",
    transcript: str = "",
    modulate_analysis: dict = None,
    duration_seconds: float = 0,
):
    if not _pool:
        return
    try:
        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO call_logs (call_id, task_id, company, action, outcome, savings, confirmation, transcript, modulate_analysis, duration_seconds)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10)
                ON CONFLICT (call_id) DO UPDATE SET
                    outcome = EXCLUDED.outcome,
                    savings = EXCLUDED.savings,
                    confirmation = EXCLUDED.confirmation,
                    transcript = EXCLUDED.transcript,
                    modulate_analysis = EXCLUDED.modulate_analysis,
                    duration_seconds = EXCLUDED.duration_seconds
                """,
                call_id, task_id, company, action, outcome, savings,
                confirmation, transcript,
                __import__("json").dumps(modulate_analysis) if modulate_analysis else None,
                duration_seconds,
            )
    except Exception as e:
        logger.error("Postgres insert_call_log failed: %s", e)


async def insert_bill_scan(result: dict, task_id: str = ""):
    if not _pool:
        return
    try:
        import json
        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO bill_scans (provider, total_amount, price_change, line_items, fees, hidden_fees, task_created)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7)
                """,
                result.get("provider_name", ""),
                result.get("total_amount", ""),
                result.get("price_change", ""),
                json.dumps(result.get("line_items", [])),
                json.dumps(result.get("fees", [])),
                json.dumps(result.get("hidden_fees", [])),
                task_id,
            )
    except Exception as e:
        logger.error("Postgres insert_bill_scan failed: %s", e)


async def get_call_history(limit: int = 10) -> list[dict]:
    if not _pool:
        return []
    try:
        async with _pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT call_id, company, action, outcome, savings, confirmation, duration_seconds, created_at "
                "FROM call_logs ORDER BY created_at DESC LIMIT $1",
                limit,
            )
            return [
                {
                    "call_id": r["call_id"],
                    "company": r["company"],
                    "action": r["action"],
                    "outcome": r["outcome"],
                    "savings": r["savings"],
                    "confirmation": r["confirmation"],
                    "duration": r["duration_seconds"],
                    "date": r["created_at"].isoformat() if r["created_at"] else "",
                }
                for r in rows
            ]
    except Exception as e:
        logger.error("Postgres get_call_history failed: %s", e)
        return []
