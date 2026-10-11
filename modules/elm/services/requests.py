"""All writes to a leave request (WF-EL-01, WF-EL-02)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.elm.domain import rules
from modules.elm.domain import state_machine as sm
from modules.elm.domain.rules import Period
from modules.elm.models import LeaveBalance, LeaveRequest, LeaveRequestTransition
from modules.elm.selectors import requests as sel

P_FACULTY = "elm.vacation_leave.apply"
P_DIRECTOR = "elm.leave_request.self_sanction"
ESTABLISHMENT_CONFIGURED = True  # BR-EL-019: replaced by published hierarchy config


def _record(req: LeaveRequest, to: str, actor_id: int | None, note: str = "") -> None:
    LeaveRequestTransition.objects.create(
        request=req, from_status=req.status, to_status=to, actor_user_id=actor_id, note=note)
    req.status = to


@transaction.atomic
def submit(*, principal, data: dict) -> LeaveRequest:
    is_faculty = principal.has_permission(P_FACULTY)
    is_director = principal.has_permission(P_DIRECTOR)
    period = Period(data["start_date"], data["end_date"], data.get("half", ""))
    substitute = data.get("substitute_user_id")
    try:
        rules.check_category(data["category"], is_faculty)
        closed, restricted = sel.calendar(period.start, period.end)
        days = rules.chargeable_days(data["category"], period, closed, restricted)
        row = sel.balance_for(principal.user_id, period.start.year, data["category"])
        rules.check_balance(row.balance if row else Decimal(0), days)
        rules.check_no_overlap(period, sel.active_periods(principal.user_id))
        if substitute:
            rules.check_substitute(
                principal.user_id, substitute, sel.active_periods(substitute), period)
    except rules.RuleViolation as exc:
        raise BadRequestError(str(exc)) from exc
    req = LeaveRequest.objects.create(
        user_id=principal.user_id, category=data["category"], start_date=period.start,
        end_date=period.end, half=period.half, reason=data["reason"],
        station_leave_details=data.get("station_leave_details", ""),
        substitute_user_id=substitute, days=days, is_director_applicant=is_director)
    _record(req, sm.initial_state(bool(substitute), is_director), principal.user_id, "submitted")
    req.save(update_fields=["status", "updated_at"])
    return req


def _get(request_id: int, scope) -> LeaveRequest:
    req = scope.select_for_update().filter(pk=request_id).first()
    if req is None:
        raise NotFoundError("Leave request not found.")
    return req


def _move(req: LeaveRequest, to: str, actor: str, actor_id: int, note: str = "") -> LeaveRequest:
    try:
        sm.validate(req.status, to, actor)
    except sm.InvalidTransition as exc:
        raise ConflictError(str(exc)) from exc
    _record(req, to, actor_id, note)
    req.save(update_fields=["status", "unit_head_recommendation", "updated_at"])
    return req


def _decline(req: LeaveRequest, principal) -> LeaveRequest:
    LeaveRequestTransition.objects.create(
        request=req, from_status=req.status, to_status=req.status,
        actor_user_id=principal.user_id, note="substitute declined")
    req.substitute_user_id = None
    req.save(update_fields=["substitute_user_id", "updated_at"])
    return req


@transaction.atomic
def respond_substitute(*, principal, request_id: int, accept: bool) -> LeaveRequest:
    req = _get(request_id, sel.visible_requests(principal))
    if req.substitute_user_id != principal.user_id:
        raise PermissionDeniedError("Only the nominated substitute may respond.")
    if not accept:
        return _decline(req, principal)
    to = sm.after_substitute_accepts(req.is_director_applicant)
    return _move(req, to, sm.SUBSTITUTE, principal.user_id, "substitute accepted")


@transaction.atomic
def unit_head_review(*, principal, request_id: int, approve: bool) -> LeaveRequest:
    req = _get(request_id, sel.task_queue(principal))
    to = sm.after_unit_head(req.category, approve, ESTABLISHMENT_CONFIGURED)
    if req.category in rules.HIGHER_SANCTION:
        req.unit_head_recommendation = "recommended" if approve else "not_recommended"
    _move(req, to, sm.UNIT_HEAD, principal.user_id)
    if to == sm.APPROVED:
        _debit(req)
    return req


@transaction.atomic
def establishment_forward(*, principal, request_id: int) -> LeaveRequest:
    scope = LeaveRequest.objects.filter(status=sm.AWAITING_ESTABLISHMENT)
    req = _get(request_id, scope)
    return _move(req, sm.AWAITING_FINAL, sm.ESTABLISHMENT, principal.user_id)


@transaction.atomic
def final_decision(*, principal, request_id: int, approve: bool) -> LeaveRequest:
    req = _get(request_id, sel.task_queue(principal))
    _move(req, sm.APPROVED if approve else sm.REJECTED, sm.AUTHORITY, principal.user_id)
    if approve:
        _debit(req)
    return req


@transaction.atomic
def withdraw(*, principal, request_id: int) -> LeaveRequest:
    req = _get(request_id, LeaveRequest.objects.filter(user_id=principal.user_id))
    return _move(req, sm.WITHDRAWN, sm.EMPLOYEE, principal.user_id, "withdrawn")


def _debit(req: LeaveRequest) -> None:
    row = LeaveBalance.objects.select_for_update().get(
        user_id=req.user_id, year=req.start_date.year, category=req.category)
    row.balance -= req.days
    row.save(update_fields=["balance", "updated_at"])
