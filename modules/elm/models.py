"""ELM tables. People are plain user_id integers, never foreign keys."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.elm.domain import rules
from modules.elm.domain import state_machine as sm

CATEGORY_CHOICES = [(c, c) for c in rules.CATEGORIES]
DAY_KINDS = [("closed", "Closed"), ("restricted", "Restricted")]


class CalendarDay(TimeStampedModel):
    day = models.DateField(unique=True)
    kind = models.CharField(max_length=12, choices=DAY_KINDS)
    label = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "elm_calendar_day"

    def __str__(self) -> str:
        return f"{self.day} ({self.kind})"


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField()
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES)
    balance = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "category"], name="elm_balance_unique"),
            models.CheckConstraint(check=Q(balance__gte=0), name="elm_balance_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.year} {self.category}: {self.balance}"


class LeaveRequest(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=6, blank=True)
    reason = models.CharField(max_length=500)
    station_leave_details = models.CharField(max_length=300, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    days = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=40, default=sm.DRAFT)
    unit_head_recommendation = models.CharField(max_length=20, blank=True)
    is_director_applicant = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=["user_id", "-created_at"], name="elm_request_owner_idx"),
            models.Index(fields=["status", "-created_at"], name="elm_request_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(end_date__gte=models.F("start_date")), name="elm_request_dates_valid"),
        ]

    def __str__(self) -> str:
        return f"{self.category} {self.start_date}..{self.end_date} [{self.status}]"


class LeaveRequestTransition(models.Model):
    request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="transitions")
    from_status = models.CharField(max_length=40)
    to_status = models.CharField(max_length=40)
    actor_user_id = models.IntegerField(null=True)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_request_transition"

    def __str__(self) -> str:
        return f"{self.from_status} -> {self.to_status}"
