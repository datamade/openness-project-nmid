import itertools
from collections import namedtuple, OrderedDict

from django.views.generic import ListView, TemplateView, DetailView
from django.http import HttpResponseNotFound
from django.db import transaction, connection

from .models import Candidate, Office
from .base_views import PaginatedList

class CandidateList(PaginatedList):
    template_name = "camp_fin/candidate-list.html"

    def get_queryset(self, **kwargs):
        cursor = connection.cursor()
        
        self.order_by = self.request.GET.get('order_by', 'closing_balance')
        self.sort_order = self.request.GET.get('sort_order', 'desc')

        cursor.execute(''' 
            SELECT * FROM (
              SELECT DISTINCT ON (candidate.id) 
                candidate.*, 
                campaign.committee_name,
                campaign.county_id,
                campaign.district_id,
                campaign.division_id,
                office.description AS office_name,
                filing.closing_balance, 
                filing.date_last_amended 
              FROM camp_fin_candidate AS candidate 
              JOIN camp_fin_filing AS filing 
                USING(entity_id)
              JOIN camp_fin_campaign AS campaign
                ON filing.campaign_id = campaign.id
              JOIN camp_fin_office AS office
                ON campaign.office_id = office.id
              ORDER BY candidate.id, filing.date_added desc
            ) AS s
            ORDER BY {0} {1}
        '''.format(self.order_by, self.sort_order))
        
        columns = [c[0] for c in cursor.description]
        candidate_tuple = namedtuple('Candidate', columns)

        return [candidate_tuple(*r) for r in cursor]
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['sort_order'] = self.sort_order
        
        context['toggle_order'] = 'desc'
        if self.sort_order.lower() == 'desc':
            context['toggle_order'] = 'asc'

        context['order_by'] = self.order_by

        return context

class CandidateDetail(ListView):
    template_name = "camp_fin/candidate-detail.html"
    
    def get_queryset(self, **kwargs):
        cursor = connection.cursor()
        
        cursor.execute(''' 
            SELECT * FROM (
              SELECT DISTINCT ON (campaign.id) 
                candidate.*, 
                campaign.committee_name,
                campaign.county_id,
                campaign.district_id,
                campaign.division_id,
                campaign.election_season_id,
                campaign.primary_election_winner_status,
                campaign.general_election_winner_status,
                office.description AS office_name 
              FROM camp_fin_candidate AS candidate 
              JOIN camp_fin_campaign AS campaign
                ON candidate.id = campaign.candidate_id
              JOIN camp_fin_office AS office
                ON campaign.office_id = office.id
              WHERE candidate.id = %s
            ) AS s
            ORDER BY election_season_id
        ''', [self.kwargs['pk']])
        
        columns = [c[0] for c in cursor.description]
        candidate_tuple = namedtuple('Candidate', columns)
        return [candidate_tuple(*r) for r in cursor]


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['candidate'] = context['object_list'][0]

        return context

class IndexView(TemplateView):
    template_name = 'index.html'
