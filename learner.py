"""
Learning tracks: the onboarding answers (level, motivation, script literacy)
and everything that tailors the app to them.

No Streamlit, ``config``, ``storage`` or ``logic`` imports (the same rule as
``srs.py`` and ``auth.py``): ``config`` imports Streamlit, and this module must
stay unit-testable without the UI. Persona and grammar-goal names are plain
strings here; ``config`` owns the texts they refer to.

``prompt_block()`` is the ONLY place prompt text is tailored to a learner.
Every LLM caller that should adapt receives its output as ``learner_block`` —
except ``logic.judge_equivalence``: whether an answer is correct must never
depend on who wrote it.

Deliberately no free-text "learning goals" field. A stored string injected
into every prompt, indefinitely, is a permanent injection surface; fixed
choices keep every prompt variant enumerable and testable.
"""

from dataclasses import dataclass

# --- LEVELS -----------------------------------------------------------------
# Ordered easiest-first; the order is the level ranking. Labels and
# descriptions are the product owner's wording. "cefr" is where the learner is;
# "target_cefr" is what generated material aims at — one step above, so input
# is just beyond current ability.
LEVELS = {
    "total_beginner": {
        "label": "Total beginner",
        "description": "I need to learn basic greetings and necessary phrases.",
        "cefr": "Pre-A1",
        "target_cefr": "A1",
        "guidance": (
            "Use only very short sentences (3-6 words) built from the most "
            "common everyday words: greetings, self-introductions, family, "
            "home, where the learner lives, food, numbers. One idea per "
            "sentence. Repeat key phrases. In conversation, ask one simple "
            "yes/no or who/what/where question per turn. Report at most ONE "
            "error per turn - the most important one - and explain it in one "
            "plain English sentence. Written material (articles, prompts) "
            "must be at most 4-6 short lines, ideally a simple two-person "
            "dialogue. Comprehension questions must be answerable in 2-4 "
            "words."
        ),
        "grammar_goals": ("none", "greetings"),
    },
    "beginner": {
        "label": "Beginner",
        "description": ("I have mastered greetings and basic phrases, but I "
                        "don't understand the grammar."),
        "cefr": "A1",
        "target_cefr": "A2",
        "guidance": (
            "Use short, simple sentences (up to about 8 words) in the present "
            "and simple past tense, with everyday vocabulary. Avoid relative "
            "participles, conditionals, compound verbs and reported speech. "
            "When explaining grammar, use plain English and one short example. "
            "Report at most two errors per turn. Written material: one short "
            "paragraph of 4-6 simple sentences."
        ),
        "grammar_goals": ("none", "greetings", "simple_tenses"),
    },
    "intermediate": {
        "label": "Intermediate",
        "description": ("I can carry a simple conversation using short "
                        "sentences, and I want to deepen my grasp of the "
                        "grammar to discuss more complex topics."),
        "cefr": "A2-B1",
        "target_cefr": "B1",
        "guidance": (
            "Use short-to-medium, uncomplicated sentences joined with common "
            "conjunctions, across all basic tenses, dative constructions and "
            "modals. Introduce occasional new vocabulary in a context that "
            "makes its meaning clear. Written material: one or two short "
            "paragraphs."
        ),
        "grammar_goals": ("none", "simple_tenses", "compound_verbs",
                          "relative_participles", "conditionals"),
    },
    "advanced": {
        "label": "Advanced",
        "description": ("I make mistakes, but I can carry on a conversation on "
                        "just about any topic and want to maximise my fluency."),
        "cefr": "B1+-B2",
        "target_cefr": "B2-C1",
        "guidance": (
            "Striving for B2+ conversational fluency. Do not use simplistic "
            "\"tourist\" language. Use complex structures naturally - relative "
            "participles, conditionals, compound verbs, reported speech, "
            "idioms - and discuss abstract topics. Written material may be "
            "several paragraphs of natural prose."
        ),
        "grammar_goals": ("none", "compound_verbs", "relative_participles",
                          "conditionals"),
    },
}
LEVEL_ORDER = tuple(LEVELS)

# --- MOTIVATIONS ------------------------------------------------------------
MOTIVATIONS = {
    "work": {
        "label": "Work",
        "guidance": (
            "The learner is learning Kannada for work. Favour workplace "
            "topics: their job, colleagues, meetings, commuting, office small "
            "talk and professional courtesy. In conversation, ask what they "
            "do for work and about their workday."
        ),
        "personas": ("The New Colleague", "The Auto Driver",
                     "The Train Conductor", "The Doctor"),
        "writing_topics": ("Work (Kelasa)", "Travel & Commute (Prayana)",
                           "Health (Arogya)"),
    },
    "heritage": {
        "label": "Heritage",
        "guidance": (
            "The learner is learning Kannada to connect with their heritage. "
            "Favour family history, their family's home town, festivals, food "
            "traditions, temples and customs, and speaking respectfully with "
            "elders (plural-respect ನೀವು / ಅವರು forms)."
        ),
        "personas": ("The Family Elder", "The Purohit", "The Nosy Neighbor"),
        "writing_topics": ("Family (Kutumba)", "Food & Dining (Oota)",
                           "Philosophy/Life (Jeevana)"),
    },
    "friends_family": {
        "label": "Friends and family",
        "guidance": (
            "The learner is learning Kannada to talk with Kannada-speaking "
            "friends and family. Favour family members, home, where they "
            "live, meals together, visiting relatives and making plans with "
            "friends. In conversation, ask about their family and where they "
            "live."
        ),
        "personas": ("The Family Elder", "The Nosy Neighbor",
                     "The Neighbour Kid", "The Shopkeeper"),
        "writing_topics": ("Family (Kutumba)", "Food & Dining (Oota)",
                           "Hobbies (Havyasagalu)"),
    },
    "fun": {
        "label": "Just for fun",
        "guidance": (
            "The learner is learning Kannada just for fun. Favour hobbies, "
            "films and music, food, travel around Karnataka and sport, and "
            "keep the tone light and playful."
        ),
        "personas": ("The Neighbour Kid", "The Auto Driver",
                     "The Shopkeeper", "The House Cleaner"),
        "writing_topics": ("Hobbies (Havyasagalu)", "Food & Dining (Oota)",
                           "Travel & Commute (Prayana)"),
    },
}

# Written as instructions to *write Kannada in script*: the app transliterates
# deterministically for a Roman reader (logic.toggle_script), which is far more
# consistent than the model's own ad-hoc romanization.
_SCRIPT_GUIDANCE = {
    True: "The learner reads and writes Kannada script fluently.",
    False: (
        "The learner CANNOT read Kannada script. Always write Kannada in "
        "Kannada script anyway - the app converts it to Roman letters for "
        "this learner automatically - and never write Kannada in Roman "
        "letters yourself. The learner will often TYPE Kannada in Roman "
        "letters (e.g. 'naanu chennagiddini'); treat that as Kannada, not "
        "English, and never report it as an error merely for being "
        "Romanized."
    ),
}

SCRIPT_DISPLAY = "Kannada (Script)"
ROMAN_DISPLAY = "Kannada (Roman - Natural)"


@dataclass(frozen=True)
class LearnerProfile:
    level: str
    motivation: str
    reads_script: bool
    updated_at: str = ""

    @classmethod
    def from_row(cls, row):
        """Build from a storage row, or None for no row / unknown keys.

        Unknown keys (a level renamed after it was saved) mean the learner
        simply answers the form again — better than crashing every page.
        """
        if not row or row.get("level") not in LEVELS \
                or row.get("motivation") not in MOTIVATIONS:
            return None
        return cls(row["level"], row["motivation"],
                   bool(row["reads_script"]), row.get("updated_at") or "")


def validate(level, motivation, reads_script):
    """Raise ValueError unless every answer is one of the fixed choices."""
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r}")
    if motivation not in MOTIVATIONS:
        raise ValueError(f"unknown motivation {motivation!r}")
    if not isinstance(reads_script, bool):
        raise ValueError("reads_script must be a bool")


def level_rank(level):
    return LEVEL_ORDER.index(level)


def content_script(profile):
    """The display mode for Kannada content (not for UI chrome)."""
    return SCRIPT_DISPLAY if profile.reads_script else ROMAN_DISPLAY


def prompt_block(profile):
    """The '## Student Profile' section that tailors every generated text."""
    lvl = LEVELS[profile.level]
    mot = MOTIVATIONS[profile.motivation]
    return (
        "## Student Profile (The User)\n"
        f"* Level: {lvl['label']} (about CEFR {lvl['cefr']}). Pitch all "
        f"Kannada you produce at CEFR {lvl['target_cefr']}.\n"
        f"* {lvl['guidance']}\n"
        f"* Motivation: {mot['guidance']}\n"
        f"* Script: {_SCRIPT_GUIDANCE[profile.reads_script]}"
    )


def grammar_goal_keys(profile):
    return LEVELS[profile.level]["grammar_goals"]


def _preferred_first(preferred, names):
    first = [n for n in preferred if n in names]
    return first + [n for n in names if n not in first]


def order_personas(profile, names):
    """All persona names, the learner's recommended ones first."""
    return _preferred_first(MOTIVATIONS[profile.motivation]["personas"],
                            list(names))


def recommended_personas(profile):
    return set(MOTIVATIONS[profile.motivation]["personas"])


def order_writing_topics(profile, topics):
    return _preferred_first(
        MOTIVATIONS[profile.motivation]["writing_topics"], list(topics))


def visible_topics(profile, topics, show_harder=False):
    """Filter and order topic dicts (each with a ``band`` level key).

    By default a learner sees topics at or below their level, their own band
    first. ``show_harder`` reveals the rest — never for a total beginner, whose
    whole point is not being overwhelmed.
    """
    mine = level_rank(profile.level)
    reveal = show_harder and profile.level != "total_beginner"
    kept = [t for t in topics if reveal or level_rank(t["band"]) <= mine]

    def key(t):
        rank = level_rank(t["band"])
        group = 0 if rank == mine else (1 if rank < mine else 2)
        return (group, -rank if group == 1 else rank, t["name"])
    return sorted(kept, key=key)


# --- PLACEMENT --------------------------------------------------------------
# A staircase over the same four bands as LEVELS: PLACEMENT_PER_BAND items per
# band, easiest band first; the learner climbs while they get at least
# PLACEMENT_PASS right. Passing k bands suggests LEVEL_ORDER[min(k, 3)] —
# passing the total-beginner band (greetings) shows they are at least a
# Beginner, and so on. It only ever *suggests* a level.
PLACEMENT_PER_BAND = 3
PLACEMENT_PASS = 2

# Deterministic script-literacy check: a Kannada word, its meaning, and the
# choices shown. Passing every item suggests reads_script = True.
SCRIPT_CHECK = (
    {"word": "ಮನೆ", "answer": "House",
     "choices": ("Tree", "House", "Water", "Milk")},
    {"word": "ನೀರು", "answer": "Water",
     "choices": ("Milk", "Tree", "House", "Water")},
)


def band_passed(correct):
    return correct >= PLACEMENT_PASS


def placement_level(bands_passed):
    """The suggested level after passing ``bands_passed`` bands in a row."""
    return LEVEL_ORDER[min(bands_passed, len(LEVEL_ORDER) - 1)]


def script_check_passed(answers):
    """``answers`` lists the chosen meaning for each SCRIPT_CHECK item."""
    return len(answers) == len(SCRIPT_CHECK) and all(
        a == item["answer"] for a, item in zip(answers, SCRIPT_CHECK))
