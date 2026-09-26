"""
Accounts and sessions (auth.py). SQLite via the autouse isolated_db fixture;
no network, no Streamlit.
"""
import sqlite3
from datetime import timedelta

import pytest

import auth
import storage

NOW = storage.utcnow()
PW = "correct horse battery"


@pytest.fixture
def asha():
    return auth.create_user("Asha", PW)


class TestPasswords:

    def test_round_trip(self):
        stored = auth.hash_password(PW)
        assert auth.verify_password(PW, stored)
        assert not auth.verify_password(PW + "x", stored)

    def test_hashes_are_salted(self):
        assert auth.hash_password(PW) != auth.hash_password(PW)

    @pytest.mark.parametrize("stored", ["", "garbage", "bcrypt$1$2$3$a$b",
                                        "scrypt$x$8$1$AA==$AA==", None])
    def test_malformed_hash_never_matches(self, stored):
        assert not auth.verify_password(PW, stored)

    def test_plaintext_not_stored(self, asha):
        with sqlite3.connect(storage.DB_FILE) as conn:
            dump = "\n".join(conn.iterdump())
        assert PW not in dump

    def test_short_password_rejected(self):
        with pytest.raises(ValueError):
            auth.create_user("ravi", "short")


class TestCreateUser:

    def test_username_normalized(self, asha):
        assert asha["username"] == "asha"
        assert "password_hash" not in asha

    def test_empty_username_rejected(self):
        with pytest.raises(ValueError):
            auth.create_user("   ", PW)

    def test_case_variant_is_a_duplicate(self, asha):
        with pytest.raises(ValueError):
            auth.create_user(" ASHA ", PW)

    def test_fresh_profile_ids_are_distinct(self, asha):
        ravi = auth.create_user("ravi", PW)
        assert asha["profile_id"] != ravi["profile_id"]
        assert storage.DEFAULT_PROFILE not in (asha["profile_id"],
                                               ravi["profile_id"])


class TestAuthenticate:

    def test_success(self, asha):
        user = auth.authenticate("  ASHA", PW, now=NOW)
        assert user == asha
        assert storage.get_user(asha["profile_id"])["last_login_at"] == \
            storage.to_iso(NOW)

    def test_wrong_password(self, asha):
        assert auth.authenticate("asha", "wrong password!", now=NOW) is None

    def test_unknown_user(self):
        assert auth.authenticate("nobody", PW, now=NOW) is None

    def test_disabled_user(self, asha):
        storage.set_user_disabled(asha["profile_id"], True)
        assert auth.authenticate("asha", PW, now=NOW) is None

    def test_lockout_after_max_failures(self, asha):
        for _ in range(auth.MAX_FAILURES):
            assert auth.authenticate("asha", "nope", now=NOW) is None
        # Even the right password is refused while locked.
        with pytest.raises(auth.LockedOut):
            auth.authenticate("asha", PW, now=NOW)

    def test_lockout_expires(self, asha):
        for _ in range(auth.MAX_FAILURES):
            auth.authenticate("asha", "nope", now=NOW)
        later = NOW + auth.FAILURE_WINDOW + timedelta(seconds=1)
        assert auth.authenticate("asha", PW, now=later) == asha

    def test_success_resets_failure_count(self, asha):
        for _ in range(auth.MAX_FAILURES - 1):
            auth.authenticate("asha", "nope", now=NOW)
        auth.authenticate("asha", PW, now=NOW)
        for _ in range(auth.MAX_FAILURES - 1):
            auth.authenticate("asha", "nope", now=NOW)
        assert auth.authenticate("asha", PW, now=NOW) == asha

    def test_unknown_usernames_are_throttled_too(self):
        for _ in range(auth.MAX_FAILURES):
            auth.authenticate("ghost", "nope", now=NOW)
        with pytest.raises(auth.LockedOut):
            auth.authenticate("ghost", "nope", now=NOW)


class TestSessions:

    def test_resume(self, asha):
        token = auth.issue_session(asha["profile_id"], now=NOW)
        assert auth.resume_session(token, now=NOW) == asha

    def test_raw_token_not_stored(self, asha):
        token = auth.issue_session(asha["profile_id"])
        with sqlite3.connect(storage.DB_FILE) as conn:
            dump = "\n".join(conn.iterdump())
        assert token not in dump

    @pytest.mark.parametrize("token", [None, "", "not-a-real-token"])
    def test_bad_tokens(self, asha, token):
        assert auth.resume_session(token) is None

    def test_expired(self, asha):
        token = auth.issue_session(asha["profile_id"], days=1, now=NOW)
        assert auth.resume_session(token, now=NOW + timedelta(days=1)) is None

    def test_revoked(self, asha):
        token = auth.issue_session(asha["profile_id"])
        auth.revoke_session(token)
        assert auth.resume_session(token) is None

    def test_disabled_user_cookie_rejected(self, asha):
        token = auth.issue_session(asha["profile_id"])
        storage.set_user_disabled(asha["profile_id"], True)
        assert auth.resume_session(token) is None


class TestPasswordChanges:

    NEW = "a much better passphrase"

    def test_change_requires_current_password(self, asha):
        assert not auth.change_password(asha["profile_id"], "wrong", self.NEW)
        assert auth.authenticate("asha", PW) == asha

    def test_change_revokes_other_sessions_but_keeps_own(self, asha):
        mine = auth.issue_session(asha["profile_id"])
        theirs = auth.issue_session(asha["profile_id"])
        assert auth.change_password(asha["profile_id"], PW, self.NEW,
                                    keep_token=mine)
        assert auth.resume_session(mine) == asha
        assert auth.resume_session(theirs) is None
        assert auth.authenticate("asha", self.NEW) == asha
        assert auth.authenticate("asha", PW) is None

    def test_change_enforces_policy(self, asha):
        with pytest.raises(ValueError):
            auth.change_password(asha["profile_id"], PW, "short")

    def test_admin_reset_revokes_all_sessions(self, asha):
        token = auth.issue_session(asha["profile_id"])
        auth.set_password(asha["profile_id"], self.NEW)
        assert auth.resume_session(token) is None
        assert auth.authenticate("asha", self.NEW) == asha
