from ckeditor.widgets import CKEditorWidget
from django import forms
from django.contrib import admin
from django.db import models

from .models import Blob, Page


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
