from django.shortcuts import render
from django.views.generic import DetailView

from .models import Page

class PagesView(DetailView):
    
    model = Page

    def get_object(self):
        path = self.request.path
        if not path.endswith('/'):
            path = path + '/'
        return self.model.objects.get(path=path)

    def get_template_names(self):
        return [self.object.template]
