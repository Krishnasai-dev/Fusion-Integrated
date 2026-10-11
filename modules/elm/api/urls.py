from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("requests", v.LeaveRequestListCreateView.as_view(), name="elm-requests"),
    path("requests/<int:pk>", v.LeaveRequestDetailView.as_view(), name="elm-request"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(),
         name="elm-request-withdraw"),
    path("requests/<int:pk>/substitute", v.SubstituteResponseView.as_view(),
         name="elm-request-substitute"),
    path("requests/<int:pk>/unit-head-review", v.UnitHeadReviewView.as_view(),
         name="elm-request-unit-head"),
    path("requests/<int:pk>/forward", v.EstablishmentForwardView.as_view(),
         name="elm-request-forward"),
    path("requests/<int:pk>/decision", v.FinalDecisionView.as_view(),
         name="elm-request-decision"),
    path("tasks", v.TaskQueueView.as_view(), name="elm-tasks"),
    path("balances", v.MyBalancesView.as_view(), name="elm-balances"),
]
