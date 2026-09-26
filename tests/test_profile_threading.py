"""
Multi-user guards.

storage.py keeps ``profile_id="local"`` defaults (so its own tests stay terse),
which means a UI or logic call that forgets ``profile_id`` would not fail — it
would silently read or write the "local" profile's progress. These tests make
that omission fail loudly instead.
"""
import ast
import os
from datetime import timedelta

import pytest

import logic
import storage

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# storage functions that are not per-profile: time helpers and account/session
# tables, which are keyed by username/token rather than by profile.
_PROFILE_FREE = {
    "utcnow", "to_iso", "from_iso", "get_schema_version",
    "create_user", "get_user", "get_user_by_username", "list_users",
    "set_password_hash", "set_user_disabled", "touch_last_login",
    "create_session", "get_session", "touch_session", "delete_session",
    "delete_sessions_for", "purge_expired_sessions",
    "record_login_failure", "count_recent_login_failures",
    "clear_login_failures",
}


def _storage_calls(filename):
    with open(os.path.join(_ROOT, filename), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "storage"):
            yield node


@pytest.mark.parametrize("filename", ["main.py", "logic.py"])
def test_every_per_profile_storage_call_passes_profile_id(filename):
    missing = [
        f"{filename}:{call.lineno} storage.{call.func.attr}"
        for call in _storage_calls(filename)
        if call.func.attr not in _PROFILE_FREE
        and not any(kw.arg == "profile_id" for kw in call.keywords)
    ]
    assert not missing, "storage calls without profile_id:\n" + "\n".join(missing)


def test_guard_actually_sees_calls():
    # If the walker silently matched nothing, the test above would pass vacuously.
    assert len(list(_storage_calls("main.py"))) >= 5
    assert len(list(_storage_calls("logic.py"))) >= 5


@pytest.mark.parametrize("fn,args", [
    (logic.get_quiz_topics, ()),
    (logic.record_quiz_answer, ({"id": "neg_001", "topic": "Negation"}, "exact")),
    (logic.build_review_quiz, ()),
    (logic.get_review_summary, ()),
])
def test_logic_srs_entry_points_require_profile(fn, args):
    with pytest.raises(TypeError):
        fn(*args)


def test_two_learners_do_not_share_progress():
    now = storage.utcnow()
    item = {"id": "neg_001", "topic": "Negation"}
    logic.record_quiz_answer(item, "incorrect", now=now, profile_id="asha")
    storage.record_attempt("Negation", 3, 10, profile_id="asha", at=now)
    storage.set_mastered("Adverbs", profile_id="asha")

    later = now + timedelta(days=1)
    assert [i["id"] for i in logic.build_review_quiz(now=later,
                                                     profile_id="asha")] \
        == ["neg_001"]
    assert logic.build_review_quiz(now=later, profile_id="ravi") == []
    assert logic.get_review_summary(now=later, profile_id="ravi")["tracked"] == 0
    assert storage.get_topic_stats(profile_id="ravi") == {}
    assert not storage.is_mastered("Adverbs", profile_id="ravi")
    # And nothing leaked into the pre-login profile either.
    assert logic.get_review_summary(
        now=later, profile_id=storage.DEFAULT_PROFILE)["tracked"] == 0


class TestLoginWiring:
    """Source guards on main.py (there is no Streamlit test harness here)."""

    @staticmethod
    def _src():
        with open(os.path.join(_ROOT, "main.py"), encoding="utf-8") as f:
            return f.read()

    def test_login_gate_runs_before_any_mode_renders(self):
        src = self._src()
        body = src[src.index("def main():"):]
        gate = body.index("user = require_login(lang_mode)")
        assert gate < body.index('if mode == "Home":')
        assert gate < body.index("logic.load_knowledge_base()")

    def test_login_form_stops_the_script(self):
        src = self._src()
        body = src[src.index("def require_login("):
                   src.index("def render_account_sidebar(")]
        assert body.rstrip().endswith("st.stop()")

    def test_sign_out_revokes_and_clears_state(self):
        src = self._src()
        body = src[src.index("def sign_out("):src.index("def require_login(")]
        assert "auth.revoke_session(" in body
        assert "del st.session_state[key]" in body
        assert "_queue_cookie(None)" in body

    def test_email_lesson_is_admin_only(self):
        src = self._src()
        assert 'del nav_options["Send Email Lesson"]' in src
        assert 'elif mode == "Send Email Lesson" and user["is_admin"]:' in src
