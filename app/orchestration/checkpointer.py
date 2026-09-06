"""SQLite checkpoint lifecycle for durable workflow state."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


@asynccontextmanager
async def sqlite_checkpointer(database_path: Path) -> AsyncIterator[AsyncSqliteSaver]:
    """Open, initialize, and close the SQLite saver around app lifetime."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        await saver.setup()
        yield saver
