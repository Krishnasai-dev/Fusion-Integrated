from rest_framework import serializers

from modules.elm.domain.rules import CATEGORIES, FIRST_HALF, SECOND_HALF
from modules.elm.models import LeaveBalance, LeaveRequest


class LeaveRequestReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ["id", "user_id", "category", "start_date", "end_date", "half", "reason",
                  "station_leave_details", "substitute_user_id", "days", "status",
                  "unit_head_recommendation", "created_at"]
        read_only_fields = fields


class LeaveRequestWriteSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(
        choices=[FIRST_HALF, SECOND_HALF], required=False, allow_blank=True)
    reason = serializers.CharField(max_length=500)
    station_leave_details = serializers.CharField(
        max_length=300, required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class DecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ["year", "category", "balance"]
        read_only_fields = fields


class NoBodySerializer(serializers.Serializer):
    pass
