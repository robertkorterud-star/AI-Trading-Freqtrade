"""
ATLAS Database Connection

SQLite connection management for ATLAS.
"""

import sqlite3
from pathlib import Path


class Database:
    """Manages the ATLAS SQLite database."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self):
        """Return a SQLite connection."""

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = sqlite3.connect(
            self.path
        )

        connection.row_factory = sqlite3.Row

        return connection
