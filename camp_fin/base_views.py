from django.views.generic import ListView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse

class PaginatedList(ListView):
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        per_page = self.request.GET.get('per_page', '25')

        paginator = Paginator(context['object_list'], per_page)

        page = self.request.GET.get('page')
        try:
            context['object_list'] = paginator.page(page)
        except PageNotAnInteger:
            context['object_list'] = paginator.page(1)
        except EmptyPage:
            context['object_list'] = paginator.page(paginator.num_pages)
        
        return context

class JSONResponseMixin(object):
    
    def render_to_json_response(self, context, **response_kwargs):
        
        return JsonResponse(
            self.get_data(context),
            **response_kwargs
        )

    def get_data(self, context):
        """
        Returns an object that will be serialized as JSON by json.dumps().
        """
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return context
