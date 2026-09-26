"""
Admin CLI (scripts/manage_users.py). getpass is patched; the database is the
autouse isolated_db.
"""
import importlib.util
import os
from unittest.mock import patch

import pytest

import auth
import storage

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "scripts", "manage_users.py")
_spec = importlib.util.spec_from_file_location("manage_users", _PATH)
manage_users = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_users)

PW = "correct horse battery"


def run(*argv, password=PW, repeat=None):
    answers = [password, password if repeat is None else repeat]
    with patch.object(manage_users.getpass, "getpass", side_effect=answers):
        manage_users.main(list(argv))


def test_create_and_login():
    run("create", "Asha")
    assert auth.authenticate("asha", PW)["username"] == "asha"


def test_create_admin():
    run("create", "jack", "--admin")
    assert storage.get_user_by_username("jack")["is_admin"] is True


def test_create_adopting_local_progress():
    storage.set_mastered("Negation")
    run("create", "jack", "--profile-id", storage.DEFAULT_PROFILE)
    user = auth.authenticate("jack", PW)
    assert storage.is_mastered("Negation", profile_id=user["profile_id"])


def test_profile_cannot_be_adopted_twice():
    run("create", "jack", "--profile-id", "local")
    with pytest.raises(SystemExit):
        run("create", "asha", "--profile-id", "local")


def test_duplicate_username():
    run("create", "asha")
    with pytest.raises(SystemExit):
        run("create", "ASHA")


def test_mismatched_passwords():
    with pytest.raises(SystemExit):
        run("create", "asha", repeat="something else entirely")
    assert storage.get_user_by_username("asha") is None


def test_weak_password():
    with pytest.raises(SystemExit):
        run("create", "asha", password="short")


def test_disable_revokes_sessions_and_blocks_login():
    run("create", "asha")
    token = auth.issue_session(storage.get_user_by_username("asha")["profile_id"])
    manage_users.main(["disable", "asha"])
    assert auth.resume_session(token) is None
    assert auth.authenticate("asha", PW) is None
    manage_users.main(["enable", "asha"])
    assert auth.authenticate("asha", PW) is not None


def test_reset_password():
    run("create", "asha")
    run("reset-password", "asha", password="a brand new passphrase")
    assert auth.authenticate("asha", "a brand new passphrase") is not None


def test_unknown_user():
    with pytest.raises(SystemExit):
        manage_users.main(["disable", "nobody"])


def test_list(capsys):
    run("create", "asha", "--admin")
    manage_users.main(["list"])
    out = capsys.readouterr().out
    assert "asha" in out and "admin" in out
