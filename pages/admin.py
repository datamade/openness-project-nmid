from django.contrib import admin
from django import forms
from django.db import models

from ckeditor.widgets import CKEditorWidget

from .models import Page, Blob


class PageAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("text",)}),
        (
            "Advanced options",
            {
                "classes": ("collapse",),
                "fields": ("title", "path", "template"),
            },
        ),
    )


admin.site.register(Page, PageAdmin)
