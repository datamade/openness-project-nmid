"""nmid URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from camp_fin.views import (
    AboutView,
    CandidateDetail,
    CandidateList,
    CommitteeDetail,
    CommitteeList,
    ContributionDetail,
    ContributionDownloadViewSet,
    ContributionViewSet,
    DonationsView,
    DownloadView,
    ExpenditureDetail,
    ExpenditureDownloadViewSet,
    ExpenditureViewSet,
    FinancialDisclosuresView,
    IndexView,
    LoanViewSet,
    LobbyistsView,
    OrganizationDetail,
    OrganizationList,
    SearchAPIView,
    SearchView,
    TopDonorsView,
    TopEarnersView,
    TopEarnersWidgetView,
    TopExpensesView,
    TransactionViewSet,
    bulk_candidates,
    bulk_committees,
    bulk_employers,
    bulk_employments,
    flush_cache,
)

router = routers.DefaultRouter()
router.register(r"contributions", ContributionViewSet, basename="contributions")
router.register(r"expenditures", ExpenditureViewSet, basename="expenditures")
router.register(
    r"bulk/contributions", ContributionDownloadViewSet, basename="bulk-contributions"
)
router.register(
    r"bulk/expenditures", ExpenditureDownloadViewSet, basename="bulk-expenditures"
)
router.register(r"transactions", TransactionViewSet, basename="transactions")
router.register(r"top-donors", TopDonorsView, basename="top-donors")
router.register(r"top-expenses", TopExpensesView, basename="top-expenses")
router.register(r"search", SearchAPIView, basename="search")
router.register(r"loans", LoanViewSet, basename="loan")

handler404 = "camp_fin.views.four_oh_four"
handler500 = "camp_fin.views.five_hundred"

urlpatterns = [
    path(r"admin/", admin.site.urls),
    path("", IndexView.as_view(), name="index"),
    path("about/", AboutView.as_view(), name="about"),
    path(
        "financial-disclosures/",
        FinancialDisclosuresView.as_view(),
        name="financial-disclosures",
    ),
    path(
        "lobbyists/",
        LobbyistsView.as_view(),
        name="lobbyists",
    ),
    path("donations/", DonationsView.as_view(), name="donations"),
    path("search/", SearchView.as_view(), name="search"),
    path("candidates/", CandidateList.as_view(), name="candidate-list"),
    path(
        r"candidates/<slug:slug>/",
        CandidateDetail.as_view(),
        name="candidate-detail",
    ),
    path(
        "contributions/<int:pk>/",
        ContributionDetail.as_view(),
        name="contribution-detail",
    ),
    path(
        "expenditures/<int:pk>/",
        ExpenditureDetail.as_view(),
        name="expenditure-detail",
    ),
    path("committees/", CommitteeList.as_view(), name="committee-list"),
    path(
        r"committees/<slug:slug>/",
        CommitteeDetail.as_view(),
        name="committee-detail",
    ),
    path("downloads/", DownloadView.as_view(), name="downloads"),
    path("organizations/", OrganizationList.as_view(), name="organization-list"),
    path(
        r"organizations/<slug:slug>/",
        OrganizationDetail.as_view(),
        name="organization-detail",
    ),
    path("api/bulk/candidates/", bulk_candidates, name="bulk-candidates"),
    path("api/bulk/committees/", bulk_committees, name="bulk-committees"),
    path("api/bulk/employers/", bulk_employers, name="bulk-employers"),
    path("api/bulk/employments/", bulk_employments, name="bulk-employments"),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("top-earners/", TopEarnersView.as_view(), name="top-earners"),
    path(
        "widgets/top-earners/",
        TopEarnersWidgetView.as_view(),
        name="widget-top-earners",
    ),
    path("flush-cache/", flush_cache, name="flush-cache"),
]
