from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.security.auth_service import AuthService


def make_auth(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)
    return AuthService(database)


def test_create_and_authenticate_user(tmp_path):
    auth = make_auth(tmp_path)

    user = auth.create_user("robert", "a-very-secure-password", "ADMIN")

    assert user.username == "robert"
    assert user.role == "ADMIN"
    assert auth.authenticate("robert", "a-very-secure-password") == user
    assert auth.authenticate("robert", "wrong-password") is None


def test_disabled_user_cannot_authenticate(tmp_path):
    auth = make_auth(tmp_path)
    user = auth.create_user("viewer", "a-very-secure-password", "VIEWER")

    with auth.database.connect() as connection:
        connection.execute("UPDATE users SET enabled = 0 WHERE id = ?", (user.id,))
        connection.commit()

    assert auth.authenticate("viewer", "a-very-secure-password") is None


def test_session_can_be_created_validated_and_revoked(tmp_path):
    auth = make_auth(tmp_path)
    user = auth.create_user("trader", "a-very-secure-password", "TRADER")

    token = auth.create_session(user.id)

    assert auth.get_user_by_session(token) == user
    auth.revoke_session(token)
    assert auth.get_user_by_session(token) is None


def test_password_is_not_stored_as_plaintext(tmp_path):
    auth = make_auth(tmp_path)
    password = "a-very-secure-password"
    auth.create_user("robert", password, "ADMIN")

    with auth.database.connect() as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?", ("robert",)
        ).fetchone()

    assert row["password_hash"] != password
    assert row["password_hash"].startswith("$argon2")
