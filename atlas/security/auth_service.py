"""Server-side authentication and role management for ATLAS."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import sqlite3

from pwdlib import PasswordHash

from atlas.database.connection import Database


PASSWORD_HASHER = PasswordHash.recommended()
SESSION_TTL = timedelta(hours=12)
VALID_ROLES = {"ADMIN", "TRADER", "VIEWER"}


@dataclass(frozen=True, slots=True)
class User:
    id: int
    username: str
    role: str
    enabled: bool


class AuthService:
    """Authenticate users and manage revocable database-backed sessions."""

    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def hash_password(password: str) -> str:
        if not password:
            raise ValueError("Password cannot be empty.")
        return PASSWORD_HASHER.hash(password)

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_user(self, username: str, password: str, role: str = "VIEWER") -> User:
        username = username.strip()
        role = role.upper().strip()
        if not username:
            raise ValueError("Username cannot be empty.")
        if role not in VALID_ROLES:
            raise ValueError("Unsupported role.")

        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO users(username, password_hash, role, enabled, created_at)
                    VALUES (?, ?, ?, 1, ?)
                    """,
                    (username, self.hash_password(password), role, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Username already exists.") from exc
            connection.commit()
            return User(cursor.lastrowid, username, role, True)

    def list_users(self) -> list[User]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id, username, role, enabled FROM users ORDER BY username"
            ).fetchall()
        return [
            User(row["id"], row["username"], row["role"], bool(row["enabled"]))
            for row in rows
        ]

    def set_user_role(self, user_id: int, role: str) -> None:
        role = role.upper().strip()
        if role not in VALID_ROLES:
            raise ValueError("Unsupported role.")

        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT role, enabled FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                raise ValueError("User not found.")

            if row["role"] == "ADMIN" and row["enabled"] and role != "ADMIN":
                admin_count = connection.execute(
                    "SELECT COUNT(*) AS count FROM users "
                    "WHERE role = 'ADMIN' AND enabled = 1"
                ).fetchone()["count"]
                if admin_count <= 1:
                    raise ValueError("Cannot remove the last enabled ADMIN.")

            connection.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                (role, user_id),
            )
            connection.commit()

    def set_user_enabled(self, user_id: int, enabled: bool) -> None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT role, enabled FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                raise ValueError("User not found.")

            if row["role"] == "ADMIN" and row["enabled"] and not enabled:
                admin_count = connection.execute(
                    "SELECT COUNT(*) AS count FROM users "
                    "WHERE role = 'ADMIN' AND enabled = 1"
                ).fetchone()["count"]
                if admin_count <= 1:
                    raise ValueError("Cannot disable the last enabled ADMIN.")

            connection.execute(
                "UPDATE users SET enabled = ? WHERE id = ?",
                (int(enabled), user_id),
            )
            if not enabled:
                connection.execute(
                    "UPDATE sessions SET revoked_at = ? "
                    "WHERE user_id = ? AND revoked_at IS NULL",
                    (datetime.now(timezone.utc).isoformat(), user_id),
                )
            connection.commit()

    def authenticate(self, username: str, password: str) -> User | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id, username, password_hash, role, enabled FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()
            if row is None or not row["enabled"]:
                return None
            if not PASSWORD_HASHER.verify(password, row["password_hash"]):
                return None
            connection.execute(
                "UPDATE users SET last_login_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), row["id"]),
            )
            connection.commit()
            return User(row["id"], row["username"], row["role"], True)

    def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + SESSION_TTL
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions(user_id, token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, self._token_hash(token), now.isoformat(), expires.isoformat()),
            )
            connection.commit()
        return token

    def get_user_by_session(self, token: str | None) -> User | None:
        if not token:
            return None
        now = datetime.now(timezone.utc)
        token_hash = self._token_hash(token)
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT u.id, u.username, u.role, u.enabled
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ?
                  AND s.revoked_at IS NULL
                  AND s.expires_at > ?
                """,
                (token_hash, now.isoformat()),
            ).fetchone()
            if row is None or not row["enabled"]:
                return None
            connection.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?",
                (now.isoformat(), token_hash),
            )
            connection.commit()
            return User(row["id"], row["username"], row["role"], True)

    def revoke_session(self, token: str | None) -> None:
        if not token:
            return
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE sessions SET revoked_at = ? WHERE token_hash = ?",
                (datetime.now(timezone.utc).isoformat(), self._token_hash(token)),
            )
            connection.commit()
