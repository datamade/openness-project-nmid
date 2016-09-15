from django.contrib import admin
from django import forms

from ckeditor.widgets import CKEditorWidget

from .models import Page


class PageAdminForm(forms.ModelForm):
    text = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Page
        fields = '__all__'

class PageAdmin(admin.ModelAdmin):
    form = PageAdminForm

admin.site.register(Page, PageAdmin)
