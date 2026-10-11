"""HTTP layer: parse, delegate, serialise. Scope comes from selectors."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.models import LeaveBalance, LeaveRequest
from modules.elm.selectors import requests as sel
from modules.elm.services import requests as svc

MODULE = HasModuleGrant("elm")
P_APPLY = "elm.leave_request.apply"
P_RESPOND = "elm.leave_request.respond"
P_PROCESS = "elm.leave_request.process"
P_VIEW_ALL = "elm.leave_request.view"
P_REVIEW = "elm.leave_request.review"
P_SANCTION = "elm.leave_request.sanction"


class LeaveRequestListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(P_APPLY, P_VIEW_ALL)]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return sel.visible_requests(self.request.principal).order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.LeaveRequestWriteSerializer
        return s.LeaveRequestReadSerializer

    @extend_schema(request=s.LeaveRequestWriteSerializer, responses=s.LeaveRequestReadSerializer)
    def create(self, request, *args, **kwargs):
        body = s.LeaveRequestWriteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        req = svc.submit(principal=request.principal, data=body.validated_data)
        return Response(s.LeaveRequestReadSerializer(req).data, status=status.HTTP_201_CREATED)


class LeaveRequestDetailView(generics.RetrieveAPIView):
    permission_classes = [MODULE, HasPermission(P_APPLY, P_VIEW_ALL)]
    serializer_class = s.LeaveRequestReadSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return sel.visible_requests(self.request.principal)


class _ActionView(generics.GenericAPIView):
    body_serializer = None

    def get_serializer_class(self):
        return self.body_serializer or s.NoBodySerializer

    def act(self, request, pk, data):
        raise NotImplementedError

    @extend_schema(responses=s.LeaveRequestReadSerializer)
    def post(self, request, pk):
        data = {}
        if self.body_serializer:
            body = self.body_serializer(data=request.data)
            body.is_valid(raise_exception=True)
            data = body.validated_data
        return Response(s.LeaveRequestReadSerializer(self.act(request, pk, data)).data)


class WithdrawView(_ActionView):
    permission_classes = [MODULE, HasPermission(P_APPLY)]

    def act(self, request, pk, data):
        return svc.withdraw(principal=request.principal, request_id=pk)


class SubstituteResponseView(_ActionView):
    permission_classes = [MODULE, HasPermission(P_RESPOND)]
    body_serializer = s.SubstituteResponseSerializer

    def act(self, request, pk, data):
        return svc.respond_substitute(
            principal=request.principal, request_id=pk, accept=data["accept"])


class UnitHeadReviewView(_ActionView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]
    body_serializer = s.DecisionSerializer

    def act(self, request, pk, data):
        return svc.unit_head_review(
            principal=request.principal, request_id=pk, approve=data["approve"])


class EstablishmentForwardView(_ActionView):
    permission_classes = [MODULE, HasPermission(P_PROCESS)]

    def act(self, request, pk, data):
        return svc.establishment_forward(principal=request.principal, request_id=pk)


class FinalDecisionView(_ActionView):
    permission_classes = [MODULE, HasPermission(P_SANCTION)]
    body_serializer = s.DecisionSerializer

    def act(self, request, pk, data):
        return svc.final_decision(
            principal=request.principal, request_id=pk, approve=data["approve"])


class TaskQueueView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW, P_SANCTION)]
    serializer_class = s.LeaveRequestReadSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return sel.task_queue(self.request.principal).order_by("created_at")


class MyBalancesView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(P_APPLY)]
    serializer_class = s.LeaveBalanceSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveBalance.objects.none()
        mine = LeaveBalance.objects.filter(user_id=self.request.principal.user_id)
        return mine.order_by("-year", "category")
