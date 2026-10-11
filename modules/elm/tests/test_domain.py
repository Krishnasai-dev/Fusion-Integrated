from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain import rules
from modules.elm.domain import state_machine as sm
from modules.elm.domain.rules import Period

NO_DAYS = frozenset()


def test_half_day_cl_is_half_a_day():
    p = Period(date(2026, 3, 2), date(2026, 3, 2), rules.FIRST_HALF)
    assert rules.chargeable_days(rules.CL, p, NO_DAYS) == Decimal("0.5")


def test_el_counts_intervening_weekend():
    p = Period(date(2026, 3, 6), date(2026, 3, 9))
    assert rules.chargeable_days(rules.EL, p, NO_DAYS) == 4


def test_cl_skips_weekend():
    p = Period(date(2026, 3, 6), date(2026, 3, 9))
    assert rules.chargeable_days(rules.CL, p, NO_DAYS) == 2


def test_rh_must_match_published_calendar():
    p = Period(date(2026, 3, 4), date(2026, 3, 4))
    with pytest.raises(rules.RuleViolation):
        rules.chargeable_days(rules.RH, p, NO_DAYS, frozenset())
    assert rules.chargeable_days(rules.RH, p, NO_DAYS, frozenset({date(2026, 3, 4)})) == 1


def test_opposite_halves_same_day_do_not_overlap():
    a = Period(date(2026, 3, 2), date(2026, 3, 2), rules.FIRST_HALF)
    b = Period(date(2026, 3, 2), date(2026, 3, 2), rules.SECOND_HALF)
    assert not rules.overlaps(a, b)
    assert rules.overlaps(a, a)


def test_substitute_cannot_be_applicant():
    p = Period(date(2026, 3, 2), date(2026, 3, 3))
    with pytest.raises(rules.RuleViolation):
        rules.check_substitute(1, 1, [], p)


def test_vl_converts_two_to_one_with_fractions():
    assert rules.vl_to_el(Decimal("5")) == Decimal("2.5")


def test_faculty_only_gets_vl():
    assert rules.VL in rules.eligible_categories(True)
    assert rules.VL not in rules.eligible_categories(False)


def test_unit_head_final_only_for_cl_and_rh():
    assert sm.after_unit_head(rules.CL, True, True) == sm.APPROVED
    assert sm.after_unit_head(rules.EL, True, True) == sm.AWAITING_ESTABLISHMENT
    assert sm.after_unit_head(rules.VL, False, False) == sm.AWAITING_FINAL


def test_director_skips_unit_head():
    assert sm.initial_state(False, True) == sm.AWAITING_DIRECTOR
    assert sm.initial_state(True, False) == sm.AWAITING_SUBSTITUTE


def test_terminal_states_have_no_exit():
    assert not [t for t in sm.TRANSITIONS if t.frm in sm.TERMINAL]
