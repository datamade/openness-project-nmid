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
from django.urls import include, re_path
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
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^$", IndexView.as_view(), name="index"),
    re_path(r"^about/$", AboutView.as_view(), name="about"),
    re_path(
        r"^financial-disclosures/$",
        FinancialDisclosuresView.as_view(),
        name="financial-disclosures",
    ),
    re_path(
        r"^lobbyists/$",
        LobbyistsView.as_view(),
        name="lobbyists",
    ),
    re_path(r"^donations/$", DonationsView.as_view(), name="donations"),
    re_path(r"^search/$", SearchView.as_view(), name="search"),
    re_path(r"^candidates/$", CandidateList.as_view(), name="candidate-list"),
    re_path(
        r"^candidates/(?P<slug>[\w-]+)/$",
        CandidateDetail.as_view(),
        name="candidate-detail",
    ),
    re_path(
        r"^contributions/(?P<pk>[0-9]+)/$",
        ContributionDetail.as_view(),
        name="contribution-detail",
    ),
    re_path(
        r"^expenditures/(?P<pk>[0-9]+)/$",
        ExpenditureDetail.as_view(),
        name="expenditure-detail",
    ),
    re_path(r"^committees/$", CommitteeList.as_view(), name="committee-list"),
    re_path(
        r"^committees/(?P<slug>[\w-]+)/$",
        CommitteeDetail.as_view(),
        name="committee-detail",
    ),
    re_path(r"^downloads/$", DownloadView.as_view(), name="downloads"),
    re_path(r"^organizations/$", OrganizationList.as_view(), name="organization-list"),
    re_path(
        r"^organizations/(?P<slug>[\w-]+)/$",
        OrganizationDetail.as_view(),
        name="organization-detail",
    ),
    re_path(r"^api/bulk/candidates/$", bulk_candidates, name="bulk-candidates"),
    re_path(r"^api/bulk/committees/$", bulk_committees, name="bulk-committees"),
    re_path(r"^api/bulk/employers/$", bulk_employers, name="bulk-employers"),
    re_path(r"^api/bulk/employments/$", bulk_employments, name="bulk-employments"),
    re_path(r"^api/", include(router.urls)),
    re_path(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    re_path(r"^ckeditor/", include("ckeditor_uploader.urls")),
    re_path(r"^top-earners/$", TopEarnersView.as_view(), name="top-earners"),
    re_path(
        r"^widgets/top-earners/$",
        TopEarnersWidgetView.as_view(),
        name="widget-top-earners",
    ),
    re_path(r"^flush-cache/$", flush_cache, name="flush-cache"),
]
