import itertools
from collections import namedtuple, OrderedDict

from django.views.generic import ListView, TemplateView, DetailView
from django.http import HttpResponseNotFound
from .models import Candidate, Office
from django.db import transaction, connection

class CandidateList(ListView):
    model = Candidate
    template_name = "camp_fin/candidate-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['candidate_count'] = len(context['object_list'])
        return context

class CandidateDetail(DetailView):
    model = Candidate
    template_name = "camp_fin/candidate-detail.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filings'] = context['candidate'].entity.filing_set.order_by('-filing_period__filing_date')

        return context

class OfficeDetail(TemplateView):
    template_name = 'camp_fin/office-detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # TODO: If we end up going this way, we need to figure out how to 404
        # properly
        
        office_id = kwargs['slug'].rsplit('-', 1)[1]

        cursor = connection.cursor()

        cursor.execute(''' 
            SELECT 
              campaign.election_season_id,
              office.description AS office_name, 
              office_type.description, 
              campaign.district_id, 
              campaign.county_id, 
              campaign.division_id,
              candidate.*
            FROM camp_fin_office AS office 
            LEFT JOIN camp_fin_officetype AS office_type 
              ON office.office_type_id = office_type.id 
            LEFT JOIN camp_fin_campaign AS campaign 
              ON office.id = campaign.office_id
            JOIN camp_fin_candidate AS candidate
              ON campaign.candidate_id = candidate.id
            WHERE office.id = %s
            ORDER BY campaign.election_season_id DESC
        ''', [office_id])
        
        columns = [col[0] for col in cursor.description]
        result_tuple = namedtuple('Office', columns)
        
        elections = OrderedDict()

        for season_id, rows in itertools.groupby(cursor, key=lambda x: x[0]):
            distinct_rows = {result_tuple(*r) for r in rows}
            elections[season_id] = sorted(list(distinct_rows), key=lambda x: x[1])
            context['office'] = elections[season_id][0].office_name

        context['elections'] = elections

        return context

class IndexView(TemplateView):
    template_name = 'index.html'
