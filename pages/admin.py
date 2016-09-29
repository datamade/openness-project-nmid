from django.contrib import admin
from django import forms

from ckeditor.widgets import CKEditorWidget

from .models import Page, Blob


class PageAdminForm(forms.ModelForm):
    text = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Page
        fields = '__all__'

class PageAdmin(admin.ModelAdmin):
    form = PageAdminForm

class BlobAdmin(admin.ModelAdmin):
    pass

admin.site.register(Page, PageAdmin)
admin.site.register(Blob, BlobAdmin)
