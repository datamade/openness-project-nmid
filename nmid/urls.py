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
from django.conf.urls import url, include
from django.contrib import admin
from django.conf.urls import handler404, handler500

from rest_framework import routers

from camp_fin.views import (
    IndexView,
    CandidateList,
    CandidateDetail,
    LobbyistList,
    LobbyistDetail,
    LobbyistTransactionList,
    LobbyistPortal,
    ContributionViewSet,
    ExpenditureViewSet,
    ContributionDownloadViewSet,
    ExpenditureDownloadViewSet,
    TransactionViewSet,
    TopDonorsView,
    TopExpensesView,
    CommitteeList,
    CommitteeDetail,
    ContributionDetail,
    DownloadView,
    ExpenditureDetail,
    SearchView,
    SearchAPIView,
    DonationsView,
    LoanViewSet,
    TopEarnersView,
    TopEarnersWidgetView,
    AboutView,
    flush_cache,
    bulk_candidates,
    bulk_committees,
    bulk_lobbyists,
    bulk_employers,
    bulk_employments,
    OrganizationList,
    OrganizationDetail,
    LobbyistContributionViewSet,
    LobbyistExpenditureViewSet,
)

router = routers.DefaultRouter()
router.register(r"contributions", ContributionViewSet, base_name="contributions")
router.register(r"expenditures", ExpenditureViewSet, base_name="expenditures")
router.register(
    r"bulk/contributions", ContributionDownloadViewSet, base_name="bulk-contributions"
)
router.register(
    r"bulk/expenditures", ExpenditureDownloadViewSet, base_name="bulk-expenditures"
)
router.register(r"transactions", TransactionViewSet, base_name="transactions")
router.register(r"top-donors", TopDonorsView, base_name="top-donors")
router.register(r"top-expenses", TopExpensesView, base_name="top-expenses")
router.register(r"search", SearchAPIView, base_name="search")
router.register(r"loans", LoanViewSet, base_name="loan")

handler404 = "camp_fin.views.four_oh_four"
handler500 = "camp_fin.views.five_hundred"

urlpatterns = [
    url(r"^admin/", admin.site.urls),
    url(r"^$", IndexView.as_view(), name="index"),
    url(r"^about/$", AboutView.as_view(), name="about"),
    url(r"^donations/$", DonationsView.as_view(), name="donations"),
    url(r"^search/$", SearchView.as_view(), name="search"),
    url(r"^candidates/$", CandidateList.as_view(), name="candidate-list"),
    url(
        r"^candidates/(?P<slug>[\w-]+)/$",
        CandidateDetail.as_view(),
        name="candidate-detail",
    ),
    url(
        r"^contributions/(?P<pk>[0-9]+)/$",
        ContributionDetail.as_view(),
        name="contribution-detail",
    ),
    url(
        r"^expenditures/(?P<pk>[0-9]+)/$",
        ExpenditureDetail.as_view(),
        name="expenditure-detail",
    ),
    url(r"^committees/$", CommitteeList.as_view(), name="committee-list"),
    url(
        r"^committees/(?P<slug>[\w-]+)/$",
        CommitteeDetail.as_view(),
        name="committee-detail",
    ),
    url(r"^downloads/$", DownloadView.as_view(), name="downloads"),
    url(r"^organizations/$", OrganizationList.as_view(), name="organization-list"),
    url(
        r"^organizations/(?P<slug>[\w-]+)/$",
        OrganizationDetail.as_view(),
        name="organization-detail",
    ),
    url(
        r"^transactions/$",
        LobbyistTransactionList.as_view(),
        name="lobbyist-transaction-list",
    ),
    url(r"^api/bulk/candidates/$", bulk_candidates, name="bulk-candidates"),
    url(r"^api/bulk/committees/$", bulk_committees, name="bulk-committees"),
    url(r"^api/bulk/employers/$", bulk_employers, name="bulk-employers"),
    url(r"^api/bulk/employments/$", bulk_employments, name="bulk-employments"),
    url(r"^api/", include(router.urls)),
    url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"^ckeditor/", include("ckeditor_uploader.urls")),
    url(r"^top-earners/$", TopEarnersView.as_view(), name="top-earners"),
    url(
        r"^widgets/top-earners/$",
        TopEarnersWidgetView.as_view(),
        name="widget-top-earners",
    ),
    url(r"^flush-cache/$", flush_cache, name="flush-cache"),
]
