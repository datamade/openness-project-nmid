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

from rest_framework import routers

from camp_fin.views import IndexView, CandidateList, CandidateDetail, \
    ContributionViewSet, ExpenditureViewSet, TransactionViewSet, TopDonorsView, \
    TopExpensesView, CommitteeList, CommitteeDetail, ContributionDetail, \
    ExpenditureDetail, SearchView, SearchAPIView, DonationsView, \
    LoanViewSet, TopEarnersView, TopEarnersWidgetView, bulk_contributions, \
    bulk_expenditures, AboutView

router = routers.DefaultRouter()
router.register(r'contributions', ContributionViewSet, base_name='contributions')
router.register(r'expenditures', ExpenditureViewSet, base_name='expenditures')
router.register(r'transactions', TransactionViewSet, base_name='transactions')
router.register(r'top-donors', TopDonorsView, base_name='top-donors')
router.register(r'top-expenses', TopExpensesView, base_name='top-expenses')
router.register(r'search', SearchAPIView, base_name='search')
router.register(r'loans', LoanViewSet, base_name='loan')

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^about/$', AboutView.as_view(), name='about'),
    url(r'^donations/$', DonationsView.as_view(), name='donations'),
    url(r'^search/$', SearchView.as_view(), name='search'),
    url(r'^candidates/$', CandidateList.as_view(), name='candidate-list'),
    url(r'^candidates/(?P<slug>[\w-]+)/$', CandidateDetail.as_view(), name='candidate-detail'),
    url(r'^contributions/(?P<pk>[0-9]+)/$', ContributionDetail.as_view(), name='contribution-detail'),
    url(r'^expenditures/(?P<pk>[0-9]+)/$', ExpenditureDetail.as_view(), name='expenditure-detail'),
    url(r'^committees/$', CommitteeList.as_view(), name='committee-list'),
    url(r'^committees/(?P<slug>[\w-]+)/$', CommitteeDetail.as_view(), name='committee-detail'),
    url(r'^api/bulk/contributions/$', bulk_contributions, name='bulk-contributions'),
    url(r'^api/bulk/expenditures/$', bulk_expenditures, name='bulk-expenditures'),
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
    url(r'^top-earners/$', TopEarnersView.as_view(), name='top-earners'),
    url(r'^widgets/top-earners/$', TopEarnersWidgetView.as_view(), name='widget-top-earners'),
]
