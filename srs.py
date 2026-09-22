"""
Spaced-repetition scheduling for Vāṇi, built on FSRS.

Like ``storage.py`` this module is deliberately dependency-light: **no
Streamlit, no ``config``, no ``storage``, no ``logic``**. (``config`` imports
Streamlit, so importing it here would drag the UI framework into the scheduler
and into every test that touches it.) Scheduler tuning therefore lives in this
file, not in ``config.py``.

It owns exactly one decision: given a graded answer, when should the learner
see that item again? Persistence is ``storage.py``'s job and joining item ids
back to quiz-bank rows is ``logic.py``'s.
"""

import json
from datetime import datetime, timedelta, timezone

from fsrs import Card, Rating, Scheduler

# ---------------------------------------------------------------------------
# Tier → rating
#
# The quiz already grades on a four-point scale, so it maps onto FSRS's four
# ratings without inventing or discarding signal:
#
#   incorrect  the answer was wrong                        → Again
#   accepted   deterministic check failed, the LLM judge
#              rescued it — understood, but shakily        → Hard
#   variant    matched a non-canonical acceptable form     → Good
#   exact      matched the canonical answer                → Easy
#
# "accepted" is deliberately rated below "variant": needing an LLM to vouch for
# a phrasing is weaker evidence of recall than hitting a form the bank already
# lists.
# ---------------------------------------------------------------------------
TIER_TO_RATING = {
    "incorrect": Rating.Again,
    "accepted": Rating.Hard,
    "variant": Rating.Good,
    "exact": Rating.Easy,
}

# Scheduler tuning. learning_steps means a missed item returns within the same
# session (1 min), then 10 min, before graduating to day-scale intervals.
#
# Fuzzing is off. FSRS otherwise randomizes each interval by a few percent, to
# stop a large imported deck from resurfacing in clumps — a real problem at
# tens of thousands of cards and a non-problem across a 200-item bank. Leaving
# it on would make the same answer at the same moment produce a different due
# date on every call, which is untestable and at odds with the deterministic
# grading the rest of the quiz is built on.
DESIRED_RETENTION = 0.9
LEARNING_STEPS = (timedelta(minutes=1), timedelta(minutes=10))
RELEARNING_STEPS = (timedelta(minutes=10),)
ENABLE_FUZZING = False

_scheduler = None


def get_scheduler():
    """Return the process-wide Scheduler (cheap to build, safe to share)."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler(
            desired_retention=DESIRED_RETENTION,
            learning_steps=LEARNING_STEPS,
            relearning_steps=RELEARNING_STEPS,
            enable_fuzzing=ENABLE_FUZZING,
        )
    return _scheduler


def rating_for_tier(tier):
    """Map a quiz grading tier to an FSRS rating.

    Raises ``KeyError`` on anything else. The tiers are a closed set produced by
    ``logic.classify_answer`` plus the "accepted" promotion in the quiz UI, so a
    fifth value is a bug worth surfacing, not a case to default through.
    """
    try:
        return TIER_TO_RATING[tier]
    except KeyError:
        raise KeyError(
            f"unknown grading tier {tier!r}; expected one of "
            f"{sorted(TIER_TO_RATING)}"
        ) from None


def new_card():
    """A never-reviewed card, due immediately."""
    return Card()


def load_card(fsrs_json):
    """Rebuild a Card from stored JSON, or a fresh one when there is none."""
    if not fsrs_json:
        return Card()
    return Card.from_dict(json.loads(fsrs_json))


def review(fsrs_json, tier, now=None):
    """Grade one answer and return the fields ``storage.upsert_card`` wants.

    ``fsrs_json`` is the card's previous serialized state, or None for an item
    the learner has never been asked before. Returns a dict of
    ``fsrs_json``/``due``/``state``/``stability``/``difficulty``/``last_review``
    with timestamps as aware UTC datetimes.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    card = load_card(fsrs_json)
    rating = rating_for_tier(tier)
    card, _log = get_scheduler().review_card(card, rating, review_datetime=now)
    data = card.to_dict()
    return {
        "fsrs_json": json.dumps(data),
        "due": card.due,
        "state": int(card.state),
        "stability": card.stability,
        "difficulty": card.difficulty,
        "last_review": card.last_review,
        "rating": int(rating),
    }


def is_due(fsrs_json, now=None):
    """True if the stored card is due at or before ``now``.

    An item with no stored state has never been asked, so it is always
    available: a fresh ``Card`` stamps ``due`` with the wall clock at
    construction, which would otherwise make a brand-new item look not-yet-due
    against an injected past timestamp.
    """
    if not fsrs_json:
        return True
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return load_card(fsrs_json).due <= now
