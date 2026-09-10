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

    auth.set_user_enabled(user.id, False)

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


def test_last_enabled_admin_cannot_be_demoted(tmp_path):
    auth = make_auth(tmp_path)
    admin = auth.create_user("admin", "a-very-secure-password", "ADMIN")

    try:
        auth.set_user_role(admin.id, "TRADER")
    except ValueError as exc:
        assert str(exc) == "Cannot remove the last enabled ADMIN."
    else:
        raise AssertionError("Expected last ADMIN protection")

    assert auth.list_users()[0].role == "ADMIN"


def test_last_enabled_admin_cannot_be_disabled(tmp_path):
    auth = make_auth(tmp_path)
    admin = auth.create_user("admin", "a-very-secure-password", "ADMIN")

    try:
        auth.set_user_enabled(admin.id, False)
    except ValueError as exc:
        assert str(exc) == "Cannot disable the last enabled ADMIN."
    else:
        raise AssertionError("Expected last ADMIN protection")

    assert auth.list_users()[0].enabled is True


def test_admin_can_manage_users_when_another_admin_exists(tmp_path):
    auth = make_auth(tmp_path)
    first = auth.create_user("admin1", "a-very-secure-password", "ADMIN")
    second = auth.create_user("admin2", "a-very-secure-password", "ADMIN")
    third = auth.create_user("admin3", "a-very-secure-password", "ADMIN")

    auth.set_user_role(first.id, "TRADER")
    auth.set_user_enabled(second.id, False)

    users = {user.username: user for user in auth.list_users()}
    assert users["admin1"].role == "TRADER"
    assert users["admin2"].enabled is False
    assert users["admin3"].role == "ADMIN"
    assert users["admin3"].enabled is True
