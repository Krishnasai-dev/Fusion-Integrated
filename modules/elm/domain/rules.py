"""Leave rules as pure functions (BR-EL-001..014)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

CL, RH, SCL, EL, COL, VL = "CL", "RH", "SCL", "EL", "COL", "VL"
CATEGORIES = (CL, RH, SCL, EL, COL, VL)
FIRST_HALF, SECOND_HALF = "first", "second"

CONTINUOUS = frozenset({EL, COL, VL})            # BR-EL-011
UNIT_HEAD_FINAL = frozenset({CL, RH})            # BR-EL-016
HIGHER_SANCTION = frozenset({SCL, EL, COL, VL})  # BR-EL-017/018
NEEDS_MEDICAL_EVIDENCE = frozenset({COL})        # BR-EL-009

ANNUAL_CREDIT = {CL: Decimal(8), RH: Decimal(2), SCL: Decimal(15), COL: Decimal(20)}
STAFF_EL_CREDIT = Decimal(30)                    # BR-EL-005
FACULTY_VL_CREDIT = Decimal(60)                  # BR-EL-006
LAPSES_AT_YEAR_END = frozenset({CL, RH, SCL})    # BR-EL-002/003/004


class RuleViolation(Exception):
    def __init__(self, rule: str, message: str):
        super().__init__(f"{rule}: {message}")
        self.rule, self.message = rule, message


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    half: str = ""


def eligible_categories(is_faculty: bool) -> frozenset[str]:
    base = {CL, RH, SCL, COL, EL}
    return frozenset(base | {VL}) if is_faculty else frozenset(base - {VL})


def check_category(category: str, is_faculty: bool) -> None:
    if category not in eligible_categories(is_faculty):
        raise RuleViolation("BR-EL-001", f"{category} is not available to this employee.")


def annual_credit(category: str, is_faculty: bool) -> Decimal:
    if category == EL:
        return Decimal(0) if is_faculty else STAFF_EL_CREDIT
    if category == VL:
        return FACULTY_VL_CREDIT if is_faculty else Decimal(0)
    return ANNUAL_CREDIT[category]


def chargeable_days(category: str, period: Period, closed: frozenset[date],
                    restricted: frozenset[date] = frozenset()) -> Decimal:
    if period.end < period.start:
        raise RuleViolation("BR-EL-001", "End date is before start date.")
    if period.half:
        if category != CL or period.start != period.end:
            raise RuleViolation("BR-EL-010", "Half-day applies to a single CL day only.")
        return Decimal("0.5")
    span = (period.end - period.start).days + 1
    if category in CONTINUOUS:
        return Decimal(span)  # weekends and closed holidays inside count
    days = (period.start + timedelta(n) for n in range(span))
    working = [d for d in days if d.weekday() < 5 and d not in closed]
    if category == RH:
        if span != 1 or period.start not in restricted:
            raise RuleViolation("BR-EL-003", "RH must be one published Restricted Holiday.")
        return Decimal(1)
    return Decimal(len(working))


def check_balance(balance: Decimal, days: Decimal) -> None:
    if days <= 0:
        raise RuleViolation("BR-EL-012", "Request covers no chargeable day.")
    if days > balance:
        raise RuleViolation("BR-EL-001", f"Needs {days} day(s), balance is {balance}.")


def overlaps(a: Period, b: Period) -> bool:
    if a.end < b.start or b.end < a.start:
        return False
    same_day = a.start == a.end == b.start == b.end
    return not (same_day and a.half and b.half and a.half != b.half)  # BR-EL-012


def check_no_overlap(new: Period, existing: list[Period]) -> None:
    if any(overlaps(new, p) for p in existing):
        raise RuleViolation("BR-EL-012", "Overlaps an active pending or approved leave.")


def check_substitute(applicant_id: int, nominee_id: int,
                     nominee_leave: list[Period], responsibility: Period) -> None:
    if nominee_id == applicant_id:
        raise RuleViolation("BR-EL-014", "Applicant cannot be their own substitute.")
    if any(overlaps(responsibility, p) for p in nominee_leave):
        raise RuleViolation("BR-EL-014", "Nominee has leave during the responsibility period.")


def vl_to_el(unused_vl: Decimal) -> Decimal:
    return unused_vl / 2  # BR-EL-007: 2 VL : 1 EL, fractions allowed
