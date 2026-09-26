"""
Account administration for Vāṇi (invite-only: there is no sign-up page).

    python scripts/manage_users.py create asha
    python scripts/manage_users.py create jack --admin --profile-id local
    python scripts/manage_users.py list
    python scripts/manage_users.py reset-password asha
    python scripts/manage_users.py disable asha     # also signs them out
    python scripts/manage_users.py enable asha
    python scripts/manage_users.py revoke-sessions asha

Passwords are read with getpass, never from argv, so they don't land in shell
history or the process list.

Targets local SQLite (data/vani.db) unless ``VANI_DATABASE_URL`` is set, in
which case it administers that Postgres — e.g. the hosted database:

    VANI_DATABASE_URL=postgresql://... python scripts/manage_users.py list

``--profile-id local`` makes the new account adopt the progress stored under
the pre-login ``"local"`` profile — use it once, for your own account.
"""

import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth      # noqa: E402
import storage   # noqa: E402


def _prompt_password():
    first = getpass.getpass("New password: ")
    if first != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")
    try:
        auth.validate_password(first)
    except ValueError as e:
        sys.exit(str(e))
    return first


def _require_user(username):
    user = storage.get_user_by_username(auth.normalize_username(username))
    if user is None:
        sys.exit(f"No such user: {username}")
    return user


def cmd_create(args):
    name = auth.normalize_username(args.username)
    if storage.get_user_by_username(name) is not None:
        sys.exit(f"User {name!r} already exists.")
    if args.profile_id and storage.get_user(args.profile_id) is not None:
        sys.exit(f"Profile {args.profile_id!r} already belongs to an account.")
    try:
        user = auth.create_user(name, _prompt_password(), is_admin=args.admin,
                                profile_id=args.profile_id)
    except ValueError as e:
        sys.exit(str(e))
    role = "admin" if user["is_admin"] else "learner"
    print(f"Created {role} {user['username']!r} (profile {user['profile_id']}).")


def cmd_list(args):
    users = storage.list_users()
    if not users:
        print("No users.")
        return
    for u in users:
        flags = [f for f, on in (("admin", u["is_admin"]),
                                 ("DISABLED", u["disabled"])) if on]
        last = (u["last_login_at"] or "never")[:16]
        print(f"{u['username']:<20} {u['profile_id']:<34} "
              f"last login {last:<16} {' '.join(flags)}")


def cmd_reset_password(args):
    user = _require_user(args.username)
    auth.set_password(user["profile_id"], _prompt_password())
    print(f"Password reset for {user['username']!r}; all their sessions revoked.")


def cmd_disable(args):
    user = _require_user(args.username)
    storage.set_user_disabled(user["profile_id"], True)
    storage.delete_sessions_for(user["profile_id"])
    print(f"Disabled {user['username']!r} and revoked their sessions.")


def cmd_enable(args):
    user = _require_user(args.username)
    storage.set_user_disabled(user["profile_id"], False)
    print(f"Enabled {user['username']!r}.")


def cmd_revoke_sessions(args):
    user = _require_user(args.username)
    storage.delete_sessions_for(user["profile_id"])
    print(f"Revoked all sessions for {user['username']!r}.")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create", help="create an account")
    p.add_argument("username")
    p.add_argument("--admin", action="store_true",
                   help="may send email lessons")
    p.add_argument("--profile-id",
                   help="adopt existing progress under this profile id "
                        f"(e.g. {storage.DEFAULT_PROFILE!r})")
    p.set_defaults(func=cmd_create)

    sub.add_parser("list", help="list accounts").set_defaults(func=cmd_list)

    for name, func, help_text in (
            ("reset-password", cmd_reset_password, "set a new password"),
            ("disable", cmd_disable, "block sign-in and revoke sessions"),
            ("enable", cmd_enable, "re-allow sign-in"),
            ("revoke-sessions", cmd_revoke_sessions, "sign out everywhere")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("username")
        p.set_defaults(func=func)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    # A dedicated variable, not DATABASE_URL, so having the app's .env loaded
    # in your shell never silently points admin commands at production.
    storage.configure(os.environ.get("VANI_DATABASE_URL"))
    args.func(args)


if __name__ == "__main__":
    main()
