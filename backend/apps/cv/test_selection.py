import datetime

from django.test import SimpleTestCase

from .selection import (
    compute_bullet_budget,
    flatten_bullets_to_text,
    remove_least_relevant_bullet,
    select_and_cut_experiences,
    select_educations_to_show,
)


class _FakeEducation:
    def __init__(self, name, start_date, end_date):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date

    def __repr__(self):
        return self.name


def _edu(name, end, start=None):
    return _FakeEducation(name, start, datetime.date(*end))


def _ongoing_edu(name, start=None):
    return _FakeEducation(name, start, None)


class SelectEducationsToShowTests(SimpleTestCase):
    def test_keeps_the_three_most_recent_by_end_date(self):
        educations = [
            _edu("oldest", (2010, 1, 1)),
            _edu("newest", (2023, 1, 1)),
            _edu("middle", (2018, 1, 1)),
            _edu("older-still", (2005, 1, 1)),
        ]
        shown = select_educations_to_show(educations)
        self.assertEqual([e.name for e in shown], ["newest", "middle", "oldest"])

    def test_tie_break_prefers_shorter_duration_at_same_end_date(self):
        long_one = _edu("long", (2020, 1, 1), start=datetime.date(2015, 1, 1))
        short_one = _edu("short", (2020, 1, 1), start=datetime.date(2019, 1, 1))
        shown = select_educations_to_show([long_one, short_one])
        self.assertEqual(shown[0].name, "short")

    def test_fewer_than_max_shown_returns_all(self):
        educations = [_edu("only", (2020, 1, 1))]
        self.assertEqual(len(select_educations_to_show(educations)), 1)

    def test_ongoing_education_without_end_date_is_treated_as_most_recent(self):
        # Sprint 34: un'istruzione ancora in corso (end_date=None) vince il
        # confronto con qualsiasi data di fine passata, invece di rompere
        # l'ordinamento con un AttributeError su None.toordinal().
        ongoing = _ongoing_edu("ongoing", start=datetime.date(2023, 1, 1))
        finished = _edu("finished", (2023, 1, 1))
        shown = select_educations_to_show([finished, ongoing])
        self.assertEqual(shown[0].name, "ongoing")

    def test_ongoing_education_duration_uses_todays_date(self):
        # La durata per il tie-break di un'istruzione in corso usa la data
        # odierna come fine provvisoria, non fallisce sul confronto None.
        ongoing_long = _ongoing_edu("ongoing-long", start=datetime.date(2015, 1, 1))
        ongoing_short = _ongoing_edu("ongoing-short", start=datetime.date(2024, 1, 1))
        shown = select_educations_to_show([ongoing_long, ongoing_short])
        self.assertEqual(shown[0].name, "ongoing-short")


class ComputeBulletBudgetTests(SimpleTestCase):
    def test_budget_table(self):
        self.assertEqual(compute_bullet_budget(1), 12)
        self.assertEqual(compute_bullet_budget(2), 10)
        self.assertEqual(compute_bullet_budget(3), 9)

    def test_zero_educations_uses_one_education_budget(self):
        self.assertEqual(compute_bullet_budget(0), 12)


def _bullet(text, rank, protected=False):
    return {"text": text, "relevance_rank": rank, "protected": protected}


def _experience(company, bullets, highly_relevant=False):
    return {
        "company": company,
        "role": "Role",
        "location": "",
        "dates": "",
        "bullets": bullets,
        "highly_relevant": highly_relevant,
    }


class SelectAndCutExperiencesTests(SimpleTestCase):
    def test_all_experiences_shown_when_at_or_under_cap(self):
        experiences = [_experience(f"c{i}", [_bullet("b", 0)]) for i in range(5)]
        result = select_and_cut_experiences(experiences, budget=100)
        self.assertEqual(len(result), 5)

    def test_more_than_cap_keeps_only_most_recent_five(self):
        experiences = [_experience(f"c{i}", [_bullet("b", 0)]) for i in range(7)]
        result = select_and_cut_experiences(experiences, budget=100)
        self.assertEqual([e["company"] for e in result], [f"c{i}" for i in range(5)])

    def test_single_swap_brings_in_most_relevant_excluded_experience(self):
        experiences = [_experience(f"c{i}", [_bullet("b", 0)]) for i in range(5)]
        experiences.append(_experience("relevant-excluded", [_bullet("b", 0)], highly_relevant=True))
        experiences.append(_experience("irrelevant-excluded", [_bullet("b", 0)]))

        result = select_and_cut_experiences(experiences, budget=100)

        companies = [e["company"] for e in result]
        self.assertIn("relevant-excluded", companies)
        self.assertNotIn("irrelevant-excluded", companies)
        self.assertNotIn("c4", companies)  # la meno recente delle 5 è sostituita
        self.assertEqual(len(result), 5)

    def test_swap_tie_break_prefers_more_recent_among_highly_relevant(self):
        # L'array arriva già in ordine cronologico inverso: indice più basso
        # = esperienza più recente. "newer-relevant" va quindi inserita
        # prima di "older-relevant" per rappresentare "più recente".
        experiences = [_experience(f"c{i}", [_bullet("b", 0)]) for i in range(5)]
        experiences.append(_experience("newer-relevant", [_bullet("b", 0)], highly_relevant=True))
        experiences.append(_experience("older-relevant", [_bullet("b", 0)], highly_relevant=True))

        result = select_and_cut_experiences(experiences, budget=100)

        companies = [e["company"] for e in result]
        self.assertIn("newer-relevant", companies)
        self.assertNotIn("older-relevant", companies)

    def test_no_swap_when_no_excluded_experience_is_highly_relevant(self):
        experiences = [_experience(f"c{i}", [_bullet("b", 0)]) for i in range(6)]
        result = select_and_cut_experiences(experiences, budget=100)
        self.assertEqual([e["company"] for e in result], [f"c{i}" for i in range(5)])

    def test_bullets_cut_to_global_budget_keeping_most_relevant(self):
        experiences = [
            _experience("a", [_bullet("a1", 0), _bullet("a2", 3)]),
            _experience("b", [_bullet("b1", 1), _bullet("b2", 2)]),
        ]
        result = select_and_cut_experiences(experiences, budget=2)

        all_kept = [b["text"] for exp in result for b in exp["bullets"]]
        self.assertEqual(set(all_kept), {"a1", "b1"})

    def test_experience_without_bullets_after_cut_becomes_single_line(self):
        experiences = [
            _experience("a", [_bullet("a1", 0)]),
            _experience("b", [_bullet("b1", 1)]),
        ]
        result = select_and_cut_experiences(experiences, budget=1)

        by_company = {e["company"]: [b["text"] for b in e["bullets"]] for e in result}
        self.assertEqual(by_company["a"], ["a1"])
        self.assertEqual(by_company["b"], [])

    def test_highly_relevant_old_experience_gets_minimum_guaranteed_bullets(self):
        experiences = [
            _experience("newer", [_bullet(f"n{i}", 0) for i in range(5)]),
            _experience("older-relevant", [_bullet("o1", 10), _bullet("o2", 11)], highly_relevant=True),
        ]
        result = select_and_cut_experiences(experiences, budget=5)

        by_company = {e["company"]: {b["text"] for b in e["bullets"]} for e in result}
        self.assertEqual(by_company["older-relevant"], {"o1", "o2"})

    def test_protected_bullet_survives_budget_cut_even_with_low_relevance(self):
        # Docs/03 §5.6: priorità massima di inclusione — sempre tenuto, a
        # prescindere dal rank, anche con budget insufficiente per il resto.
        experiences = [
            _experience("a", [_bullet("a1", 0), _bullet("enriched", 99, protected=True)]),
        ]
        result = select_and_cut_experiences(experiences, budget=1)

        kept = [b["text"] for exp in result for b in exp["bullets"]]
        self.assertIn("enriched", kept)

    def test_experience_with_protected_bullet_is_never_excluded_by_cap(self):
        # 6 esperienze, cap a 5: la più vecchia porta un bullet protetto e
        # non marcato "altamente rilevante" — deve comunque restare.
        experiences = [_experience(f"c{i}", [_bullet("b", 0)]) for i in range(5)]
        experiences.append(
            _experience("has-enrichment", [_bullet("enriched", 0, protected=True)])
        )

        result = select_and_cut_experiences(experiences, budget=100)

        companies = [e["company"] for e in result]
        self.assertIn("has-enrichment", companies)
        self.assertEqual(len(result), 5)


class RemoveLeastRelevantBulletTests(SimpleTestCase):
    def test_removes_the_globally_least_relevant_bullet(self):
        experiences = [
            _experience("a", [_bullet("a1", 0), _bullet("a2", 5)]),
            _experience("b", [_bullet("b1", 2)]),
        ]
        removed = remove_least_relevant_bullet(experiences)

        self.assertTrue(removed)
        remaining = [b["text"] for exp in experiences for b in exp["bullets"]]
        self.assertEqual(set(remaining), {"a1", "b1"})

    def test_returns_false_when_no_bullets_left(self):
        experiences = [_experience("a", [])]
        self.assertFalse(remove_least_relevant_bullet(experiences))

    def test_mutates_experiences_in_place(self):
        experiences = [_experience("a", [_bullet("a1", 0), _bullet("a2", 1)])]
        remove_least_relevant_bullet(experiences)
        self.assertEqual(len(experiences[0]["bullets"]), 1)
        self.assertEqual(experiences[0]["bullets"][0]["text"], "a1")

    def test_protected_bullet_is_never_removed(self):
        experiences = [_experience("a", [_bullet("enriched", 0, protected=True)])]
        removed = remove_least_relevant_bullet(experiences)

        self.assertFalse(removed)
        self.assertEqual(len(experiences[0]["bullets"]), 1)

    def test_removes_least_relevant_non_protected_bullet_even_with_lower_rank(self):
        experiences = [
            _experience(
                "a",
                [_bullet("enriched", 0, protected=True), _bullet("normal", 1)],
            )
        ]
        removed = remove_least_relevant_bullet(experiences)

        self.assertTrue(removed)
        remaining = [b["text"] for b in experiences[0]["bullets"]]
        self.assertEqual(remaining, ["enriched"])


class FlattenBulletsToTextTests(SimpleTestCase):
    def test_flattens_dict_bullets_to_plain_strings(self):
        experiences = [_experience("a", [_bullet("a1", 0), _bullet("a2", 1)])]
        result = flatten_bullets_to_text(experiences)
        self.assertEqual(result[0]["bullets"], ["a1", "a2"])
