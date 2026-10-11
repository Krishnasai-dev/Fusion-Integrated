"""Leave request states and legal moves (WF-EL-01, WF-EL-02)."""
from __future__ import annotations

from dataclasses import dataclass

from modules.elm.domain.rules import UNIT_HEAD_FINAL

DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
AWAITING_DIRECTOR = "awaiting_director_self_sanction"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_FINAL = "awaiting_final_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

TERMINAL = frozenset({APPROVED, REJECTED, WITHDRAWN})
PENDING = frozenset({AWAITING_SUBSTITUTE, AWAITING_DIRECTOR, AWAITING_UNIT_HEAD,
                     AWAITING_ESTABLISHMENT, AWAITING_FINAL})
ACTIVE = PENDING | {APPROVED}

EMPLOYEE, SUBSTITUTE, UNIT_HEAD, ESTABLISHMENT, AUTHORITY = (
    "employee", "substitute", "unit_head", "establishment", "authority")


class InvalidTransition(Exception):
    pass


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    actor: str


TRANSITIONS = (
    Transition(AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, SUBSTITUTE),
    Transition(AWAITING_SUBSTITUTE, AWAITING_DIRECTOR, SUBSTITUTE),
    Transition(AWAITING_UNIT_HEAD, APPROVED, UNIT_HEAD),
    Transition(AWAITING_UNIT_HEAD, REJECTED, UNIT_HEAD),
    Transition(AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, UNIT_HEAD),
    Transition(AWAITING_UNIT_HEAD, AWAITING_FINAL, UNIT_HEAD),
    Transition(AWAITING_ESTABLISHMENT, AWAITING_FINAL, ESTABLISHMENT),
    Transition(AWAITING_FINAL, APPROVED, AUTHORITY),
    Transition(AWAITING_FINAL, REJECTED, AUTHORITY),
    Transition(AWAITING_DIRECTOR, APPROVED, AUTHORITY),
    Transition(AWAITING_DIRECTOR, REJECTED, AUTHORITY),
    *(Transition(s, WITHDRAWN, EMPLOYEE) for s in sorted(PENDING)),
)


def initial_state(substitute_required: bool, is_director: bool) -> str:
    if substitute_required:
        return AWAITING_SUBSTITUTE
    return AWAITING_DIRECTOR if is_director else AWAITING_UNIT_HEAD


def after_substitute_accepts(is_director: bool) -> str:
    return AWAITING_DIRECTOR if is_director else AWAITING_UNIT_HEAD


def after_unit_head(category: str, approve: bool, establishment_configured: bool) -> str:
    if category in UNIT_HEAD_FINAL:
        return APPROVED if approve else REJECTED  # BR-EL-016
    return AWAITING_ESTABLISHMENT if establishment_configured else AWAITING_FINAL


def validate(frm: str, to: str, actor: str) -> None:
    if not any(t.frm == frm and t.to == to and t.actor == actor for t in TRANSITIONS):
        raise InvalidTransition(f"{actor} cannot move a request from {frm} to {to}.")
