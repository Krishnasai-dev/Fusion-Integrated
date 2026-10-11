"""Who sees which request, decided once (BR-EL-016/017)."""
from __future__ import annotations

from datetime import date

from django.db.models import Q, QuerySet

from modules.elm.domain import state_machine as sm
from modules.elm.domain.rules import Period
from modules.elm.models import CalendarDay, LeaveBalance, LeaveRequest

P_VIEW_ALL = "elm.leave_request.view"
P_REVIEW = "elm.leave_request.review"
P_SANCTION = "elm.leave_request.sanction"


def visible_requests(principal) -> QuerySet[LeaveRequest]:
    if principal.has_permission(P_VIEW_ALL):
        return LeaveRequest.objects.all()
    mine = Q(user_id=principal.user_id) | Q(substitute_user_id=principal.user_id)
    return LeaveRequest.objects.filter(mine)


def task_queue(principal) -> QuerySet[LeaveRequest]:
    states = []
    if principal.has_permission(P_REVIEW):
        states.append(sm.AWAITING_UNIT_HEAD)
    if principal.has_permission(P_SANCTION):
        states += [sm.AWAITING_FINAL, sm.AWAITING_DIRECTOR]
    return LeaveRequest.objects.filter(status__in=states).exclude(user_id=principal.user_id)


def active_periods(user_id: int, exclude_id: int | None = None) -> list[Period]:
    qs = LeaveRequest.objects.filter(user_id=user_id, status__in=sm.ACTIVE)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return [Period(r.start_date, r.end_date, r.half) for r in qs]


def calendar(start: date, end: date) -> tuple[frozenset[date], frozenset[date]]:
    rows = CalendarDay.objects.filter(day__range=(start, end))
    closed = frozenset(r.day for r in rows if r.kind == "closed")
    restricted = frozenset(r.day for r in rows if r.kind == "restricted")
    return closed, restricted


def balance_for(user_id: int, year: int, category: str):
    return LeaveBalance.objects.filter(user_id=user_id, year=year, category=category).first()
