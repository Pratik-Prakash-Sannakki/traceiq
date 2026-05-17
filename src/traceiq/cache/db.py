import json
import aiosqlite
from dataclasses import asdict
from traceiq.models import AnalysisResult, Issue, Flag


class SQLiteCache:

    def __init__(self, db_path: str = "traceiq.db"):
        self._path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    trace_id TEXT PRIMARY KEY,
                    data     TEXT NOT NULL,
                    created  TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    role     TEXT NOT NULL,
                    content  TEXT NOT NULL,
                    created  TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_trace_id ON chat_messages (trace_id)"
            )
            await db.commit()

    async def save_analysis(self, result: AnalysisResult) -> None:
        data = {
            "trace_id": result.trace_id,
            "issues": [asdict(i) for i in result.issues],
            "root_cause": result.root_cause,
            "summary": result.summary,
            "analyzed_at": result.analyzed_at,
            "flags": [asdict(f) for f in result.flags],
        }
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO analyses (trace_id, data, created) VALUES (?, ?, ?)",
                (result.trace_id, json.dumps(data), result.analyzed_at),
            )
            await db.commit()

    async def get_analysis(self, trace_id: str) -> AnalysisResult | None:
        async with aiosqlite.connect(self._path) as db:
            async with db.execute(
                "SELECT data FROM analyses WHERE trace_id = ?", (trace_id,)
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        return AnalysisResult(
            trace_id=data["trace_id"],
            issues=[Issue(**i) for i in data.get("issues", [])],
            root_cause=data["root_cause"],
            summary=data["summary"],
            analyzed_at=data["analyzed_at"],
            flags=[Flag(**f) for f in data.get("flags", [])],
        )

    async def delete_analysis(self, trace_id: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute("DELETE FROM analyses WHERE trace_id = ?", (trace_id,))
            await db.execute("DELETE FROM chat_messages WHERE trace_id = ?", (trace_id,))
            await db.commit()

    async def save_chat_message(self, trace_id: str, role: str, content: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT INTO chat_messages (trace_id, role, content) VALUES (?, ?, ?)",
                (trace_id, role, content),
            )
            await db.commit()

    async def get_chat_history(self, trace_id: str) -> list[dict]:
        async with aiosqlite.connect(self._path) as db:
            async with db.execute(
                "SELECT role, content FROM chat_messages WHERE trace_id = ? ORDER BY id",
                (trace_id,),
            ) as cur:
                rows = await cur.fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]
