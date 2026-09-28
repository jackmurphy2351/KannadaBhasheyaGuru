"""
Accounts and sessions (auth.py). SQLite via the autouse isolated_db fixture;
no network, no Streamlit.
"""
import inspect
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


# ---------------------------------------------------------------------------
# Self-service signup
# ---------------------------------------------------------------------------

GOOD_SIGNUP_PW = "Correct-Horse9"  # upper, lower, digit, special, 12+ chars


class TestValidateSignupPassword:

    def test_accepts_a_password_with_every_character_class(self):
        auth.validate_signup_password(GOOD_SIGNUP_PW)  # no raise

    @pytest.mark.parametrize("password", [
        "correct horse battery",   # no upper, no digit, no special
        "CORRECT HORSE9!",         # no lower
        "correct horse9!",         # no upper
        "Correct Horse!!!!",       # no digit
        "CorrectHorseBattery9",    # no special
        "Sh0rt!",                  # too short
    ])
    def test_rejects_missing_a_character_class_or_length(self, password):
        with pytest.raises(ValueError):
            auth.validate_signup_password(password)

    def test_validate_password_stays_lenient_for_admin_paths(self):
        # The plain passphrase-style password used everywhere else in this
        # file must keep passing the *unmodified* admin/CLI check, even
        # though it fails the stricter signup one — proves the two are
        # layered, not merged.
        auth.validate_password(PW)  # no raise
        with pytest.raises(ValueError):
            auth.validate_signup_password(PW)


class TestStartSignup:

    def test_creates_a_disabled_unconfirmed_account(self):
        kind, token, profile_id = auth.start_signup(
            " Asha@Example.com ", GOOD_SIGNUP_PW, now=NOW)
        assert kind == "new"
        assert token is not None
        user = storage.get_user(profile_id)
        assert user["username"] == "asha@example.com"
        assert user["disabled"] is True
        assert user["email_confirmed_at"] is None
        assert user["is_admin"] is False

    def test_signature_has_no_is_admin_or_profile_id_parameter(self):
        # A future "helpful" addition of either parameter must fail loudly.
        params = inspect.signature(auth.start_signup).parameters
        assert "is_admin" not in params
        assert "profile_id" not in params

    def test_rejects_bad_email_shape(self):
        with pytest.raises(ValueError):
            auth.start_signup("not-an-email", GOOD_SIGNUP_PW)
        assert storage.list_users() == []

    def test_rejects_weak_password_and_creates_no_row(self):
        with pytest.raises(ValueError):
            auth.start_signup("asha@example.com", "weak")
        assert storage.get_user_by_username("asha@example.com") is None

    def test_duplicate_email_does_not_touch_the_existing_account(self):
        existing = auth.create_user("asha@example.com", PW, is_admin=True)
        before = storage.get_user(existing["profile_id"])

        kind, token, profile_id = auth.start_signup(
            "ASHA@example.com", GOOD_SIGNUP_PW, now=NOW)

        assert kind == "duplicate"
        assert token is None
        assert profile_id == existing["profile_id"]
        assert storage.get_user(existing["profile_id"]) == before

    def test_concurrent_signup_race_degrades_to_duplicate(self, monkeypatch):
        auth.create_user("asha@example.com", PW)

        def boom(*a, **k):
            raise ValueError("username taken")

        monkeypatch.setattr(storage, "create_user", boom)
        kind, token, profile_id = auth.start_signup(
            "asha@example.com", GOOD_SIGNUP_PW)
        assert kind == "duplicate"
        assert token is None


class TestConfirmSignup:

    def _signed_up(self):
        _, token, profile_id = auth.start_signup(
            "asha@example.com", GOOD_SIGNUP_PW, now=NOW)
        return token, profile_id

    def test_confirms_and_enables_the_account(self):
        token, profile_id = self._signed_up()
        user = auth.confirm_signup(token, now=NOW)
        assert user["username"] == "asha@example.com"
        assert storage.get_user(profile_id)["disabled"] is False
        assert storage.get_user(profile_id)["email_confirmed_at"] is not None

    def test_token_is_single_use(self):
        token, _ = self._signed_up()
        assert auth.confirm_signup(token) is not None
        assert auth.confirm_signup(token) is None

    def test_expired_token_rejected(self):
        token, _ = self._signed_up()
        later = NOW + timedelta(hours=auth.SIGNUP_TOKEN_HOURS, seconds=1)
        assert auth.confirm_signup(token, now=later) is None

    @pytest.mark.parametrize("token", [None, "", "garbage"])
    def test_bad_tokens(self, token):
        assert auth.confirm_signup(token) is None

    def test_confirmed_user_can_then_sign_in_normally(self):
        token, _ = self._signed_up()
        auth.confirm_signup(token, now=NOW)
        assert auth.authenticate(
            "asha@example.com", GOOD_SIGNUP_PW, now=NOW) is not None


class TestAuthenticateUnconfirmed:

    def _signed_up(self):
        _, token, profile_id = auth.start_signup(
            "asha@example.com", GOOD_SIGNUP_PW, now=NOW)
        return token, profile_id

    def test_correct_password_raises_pending_confirmation(self):
        self._signed_up()
        with pytest.raises(auth.PendingConfirmation):
            auth.authenticate("asha@example.com", GOOD_SIGNUP_PW, now=NOW)

    def test_wrong_password_returns_none_not_pending(self):
        # The key anti-enumeration property: a bad guess against a pending
        # account looks exactly like a bad guess against anything else.
        self._signed_up()
        assert auth.authenticate("asha@example.com", "nope at all!", now=NOW) \
            is None

    def test_lockout_still_applies_to_a_pending_account(self):
        self._signed_up()
        for _ in range(auth.MAX_FAILURES):
            auth.authenticate("asha@example.com", "nope", now=NOW)
        with pytest.raises(auth.LockedOut):
            auth.authenticate("asha@example.com", GOOD_SIGNUP_PW, now=NOW)

    def test_admin_disabled_confirmed_account_still_returns_none(self, asha):
        # Distinguishes "disabled by an admin" (existing behavior) from
        # "disabled pending confirmation" (new behavior) — must not collapse.
        storage.set_user_disabled(asha["profile_id"], True)
        assert auth.authenticate("asha", PW, now=NOW) is None
