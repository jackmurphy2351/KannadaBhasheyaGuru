"""
Accounts and sessions for Vāṇi.

Like ``storage.py`` and ``srs.py`` this module has **no Streamlit, ``config`` or
``logic`` dependencies**, so the admin CLI and the tests can use it without
dragging in the UI. ``storage`` does the persistence; this module owns every
piece of policy: hashing, username normalization, throttling and tokens.

Two secrets never reach the database: the plaintext password (only its scrypt
hash is stored) and the raw session token (only its SHA-256 is stored), so a
leaked database can neither log anyone in nor be replayed as a cookie.
"""

import base64
import hashlib
import hmac
import re
import secrets
import uuid
from datetime import timedelta

import storage

MIN_PASSWORD_LENGTH = 12
SESSION_DAYS = 30

# How long a self-service signup has to click the confirmation link.
SIGNUP_TOKEN_HOURS = 24

# Throttle: this many failures for one username inside the window locks it
# until the oldest failure ages out. Keyed by username, not IP — Streamlit does
# not reliably expose the client address behind Community Cloud's proxy.
MAX_FAILURES = 5
FAILURE_WINDOW = timedelta(minutes=15)

# scrypt cost. Stored in each hash, so raising these later only affects new
# hashes; old ones still verify with the parameters they were made with.
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 64


class LockedOut(Exception):
    """Too many recent failed logins for this username."""


class PendingConfirmation(Exception):
    """The password was correct, but this account is awaiting email confirmation."""


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def _b64(raw):
    return base64.b64encode(raw).decode("ascii")


def hash_password(password):
    """Return ``scrypt$n$r$p$salt$key`` for ``password``."""
    salt = secrets.token_bytes(_SALT_BYTES)
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N,
                         r=_SCRYPT_R, p=_SCRYPT_P, dklen=_KEY_BYTES)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(key)}"


def verify_password(password, stored):
    """True if ``password`` matches ``stored``. Malformed hashes never match."""
    try:
        scheme, n, r, p, salt, key = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(key)
        actual = hashlib.scrypt(password.encode("utf-8"),
                                salt=base64.b64decode(salt), n=int(n),
                                r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError, AttributeError):
        return False
    return hmac.compare_digest(actual, expected)


# Verified against when the username is unknown, so a miss costs the same
# scrypt work as a hit and response time doesn't reveal which usernames exist.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def normalize_username(username):
    """Usernames are case-insensitive and ignore surrounding whitespace."""
    return (username or "").strip().casefold()


def validate_password(password):
    """Raise ``ValueError`` if ``password`` does not meet the policy."""
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


def validate_signup_password(password):
    """Stricter policy for public self-service signup.

    Layered on top of ``validate_password`` rather than replacing it: an
    admin resetting someone's password, or the CLI, still only needs length
    (existing passphrase-style passwords like "correct horse battery" keep
    working there) — this extra complexity check applies only where a
    stranger on the internet is choosing their own password unsupervised.
    """
    validate_password(password)
    password = password or ""
    missing = []
    if not re.search(r"[A-Z]", password):
        missing.append("an uppercase letter")
    if not re.search(r"[a-z]", password):
        missing.append("a lowercase letter")
    if not re.search(r"\d", password):
        missing.append("a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        missing.append("a special character")
    if missing:
        raise ValueError("Password must also contain " + ", ".join(missing) + ".")


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
def public_user(user):
    """The fields safe to keep in session state (no password hash)."""
    return {"profile_id": user["profile_id"], "username": user["username"],
            "is_admin": user["is_admin"]}


def create_user(username, password, is_admin=False, profile_id=None):
    """Create an account and return its public fields.

    ``profile_id`` defaults to a fresh opaque id. Pass an existing one (e.g.
    ``storage.DEFAULT_PROFILE``) to let the account adopt progress already
    stored under it.
    """
    name = normalize_username(username)
    if not name:
        raise ValueError("Username must not be empty.")
    validate_password(password)
    profile_id = profile_id or uuid.uuid4().hex
    storage.create_user(profile_id, name, hash_password(password),
                        is_admin=is_admin)
    return public_user(storage.get_user(profile_id))


def authenticate(username, password, now=None):
    """Return the public user on success, None on bad credentials.

    Raises ``LockedOut`` before checking the password once the username has
    ``MAX_FAILURES`` recent failures, so a locked account can't be probed.
    """
    now = now or storage.utcnow()
    name = normalize_username(username)
    if storage.count_recent_login_failures(name, now - FAILURE_WINDOW) \
            >= MAX_FAILURES:
        raise LockedOut(name)

    user = storage.get_user_by_username(name)
    ok = verify_password(password or "",
                         user["password_hash"] if user else _DUMMY_HASH)
    if not ok or user is None:
        storage.record_login_failure(name, at=now)
        return None
    if user["disabled"]:
        # A disabled account only reveals *why* once the password has
        # already matched — a wrong guess is indistinguishable from a wrong
        # guess against any other account, so this can't be used to find out
        # which emails are registered-but-unconfirmed.
        if user["email_confirmed_at"] is None:
            raise PendingConfirmation(name)
        storage.record_login_failure(name, at=now)
        return None
    storage.clear_login_failures(name)
    storage.touch_last_login(user["profile_id"], at=now)
    return public_user(user)


def set_password(profile_id, new_password):
    """Admin reset: set a new password and revoke every session."""
    validate_password(new_password)
    storage.set_password_hash(profile_id, hash_password(new_password))
    storage.delete_sessions_for(profile_id)


def change_password(profile_id, current_password, new_password,
                    keep_token=None):
    """Self-service change. Returns False if ``current_password`` is wrong.

    Every other session is revoked — changing a password is what you do when
    you think someone else has it. ``keep_token`` spares the caller's own.
    """
    user = storage.get_user(profile_id)
    if user is None or not verify_password(current_password or "",
                                           user["password_hash"]):
        return False
    validate_password(new_password)
    storage.set_password_hash(profile_id, hash_password(new_password))
    storage.delete_sessions_for(
        profile_id, keep=_token_hash(keep_token) if keep_token else None)
    return True


# ---------------------------------------------------------------------------
# Self-service signup
#
# start_signup()'s signature deliberately has no ``is_admin`` and no
# ``profile_id`` parameter — not defaulted away, absent — so it structurally
# cannot create an admin or land in an existing account's row. The only
# remaining way to grant admin stays scripts/manage_users.py, run locally.
# ---------------------------------------------------------------------------
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def start_signup(email, password, now=None):
    """Begin a public signup. Returns ``(kind, raw_token, profile_id)``.

    ``kind`` is ``"new"`` (a disabled, unconfirmed account was created; send
    the confirmation email to ``raw_token``'s link) or ``"duplicate"`` (the
    email is already registered; ``raw_token`` is None — send a notice to the
    existing address instead, and show the caller the exact same "check your
    email" outcome either way, so signup can never be used to discover which
    emails have accounts).

    Both the email shape and the password policy are checked before the
    lookup, regardless of whether the email turns out to be registered, so
    neither is an enumeration channel either.
    """
    now = now or storage.utcnow()
    name = normalize_username(email)
    if not _EMAIL_RE.match(name):
        raise ValueError("Enter a valid email address.")
    validate_signup_password(password)

    existing = storage.get_user_by_username(name)
    if existing is not None:
        return "duplicate", None, existing["profile_id"]

    profile_id = uuid.uuid4().hex
    try:
        storage.create_user(profile_id, name, hash_password(password),
                            confirmed=False, at=now)
    except ValueError:
        # Lost a race with a concurrent signup for the same email: the
        # database's UNIQUE(username) constraint is the real backstop, not
        # this function's own check-then-act read above.
        existing = storage.get_user_by_username(name)
        return "duplicate", None, existing["profile_id"]

    token = secrets.token_urlsafe(32)
    storage.create_email_confirmation(
        _token_hash(token), profile_id,
        now + timedelta(hours=SIGNUP_TOKEN_HOURS), at=now)
    return "new", token, profile_id


def confirm_signup(token, now=None):
    """Redeem a signup confirmation link. Returns the signed-in-ready public
    user, or None if the token is missing, garbage, expired or already used.

    The token is deleted before anything else, so it's single-use even if a
    later step fails. Only ``set_user_confirmed`` runs — never the password
    hash or admin flag.
    """
    if not token:
        return None
    digest = _token_hash(token)
    confirmation = storage.get_email_confirmation(digest, now=now)
    if confirmation is None:
        return None
    storage.delete_email_confirmation(digest)
    storage.set_user_confirmed(confirmation["profile_id"], at=now)
    return public_user(storage.get_user(confirmation["profile_id"]))


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session(profile_id, days=SESSION_DAYS, now=None):
    """Create a session and return the raw token (for the cookie only)."""
    now = now or storage.utcnow()
    token = secrets.token_urlsafe(32)
    storage.create_session(_token_hash(token), profile_id,
                           now + timedelta(days=days), at=now)
    return token


def resume_session(token, now=None):
    """Return the public user for a live token, else None.

    A disabled or deleted account's sessions stop working immediately, even
    though their cookies are still out there.
    """
    if not token:
        return None
    digest = _token_hash(token)
    session = storage.get_session(digest, now=now)
    if session is None:
        return None
    user = storage.get_user(session["profile_id"])
    if user is None or user["disabled"]:
        return None
    storage.touch_session(digest, at=now)
    return public_user(user)


def revoke_session(token):
    if token:
        storage.delete_session(_token_hash(token))
