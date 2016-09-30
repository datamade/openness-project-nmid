from django.contrib import admin
from django import forms
from django.db import models

from ckeditor.widgets import CKEditorWidget

from .models import Page, Blob

class PageAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('text', 'blobs')
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('title', 'path', 'template'),
        }),
    )
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget},
    }

class BlobAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget},
    }

admin.site.register(Page, PageAdmin)
admin.site.register(Blob, BlobAdmin)
