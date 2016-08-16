from django.views.generic import ListView, TemplateView, DetailView
from .models import Candidate

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

class IndexView(TemplateView):
    template_name = 'index.html'
