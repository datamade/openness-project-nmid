from django import forms
from django.contrib import admin
from django.core.management import call_command

from camp_fin.decorators import boolean, short_description
from camp_fin.models import Campaign, Race, RaceGroup, Story


class ClearCacheMixin(object):
    """
    Mixin that overrides the `save` and `delete` methods of Django's ModelAdmin
    class to clear the cache whenever an object is added or changed.
    """

    def save_model(self, request, obj, form, change):
        call_command("clear_cache")
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        call_command("clear_cache")
        super().delete_model(request, obj)


def create_display(obj, attr, field):
    """
    Utility function for generating display values for ForeignKey form fields
    on the Admin page.
    """
    attribute = getattr(getattr(obj, attr), field, None)

    if attribute:
        return attribute
    else:
        return "--"


class WinnerFilter(admin.SimpleListFilter):
    """
    Filter Races based on whether they have a Winner or not.
    """

    title = "whether a winner exists"
    parameter_name = "winner"

    def lookups(self, request, model_admin):
        """
        Filter options that the user can choose, in the form:

        (<parameter>, <human_readable_string>)
        """
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        """
        Restrict the queryset based on the parameter the user has chosen.
        """

        if self.value() == "yes":
            return queryset.filter(winner__isnull=False)

        elif self.value() == "no":
            return queryset.filter(winner__isnull=True)


class RaceForm(forms.ModelForm):
    class Meta:
        model = Race
        fields = ["winner"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["winner"].queryset = Campaign.objects.filter(
            active_race__id=self.instance.id
        )


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin, ClearCacheMixin):
    relevant_fields = ("title", "link")
    list_display = relevant_fields
    search_fields = ("title", "link")


class CampaignInline(admin.StackedInline, ClearCacheMixin):
    model = Campaign
    fields = ("race_status",)
    extra = 0


@admin.register(Race)
class RaceAdmin(admin.ModelAdmin, ClearCacheMixin):
    relevant_fields = (
        "__str__",
        "display_division",
        "display_district",
        "display_office",
        "display_office_type",
        "display_county",
        "display_election_season",
        "display_candidates",
        "has_winner",
    )

    list_display = relevant_fields
    list_filter = (WinnerFilter, "election_season__year")
    form = RaceForm
    search_fields = ("office__description",)
    inlines = [CampaignInline]

    @short_description("Division")
    def display_division(self, obj):
        return create_display(obj, "division", "name")

    @short_description("District")
    def display_district(self, obj):
        return create_display(obj, "district", "name")

    @short_description("Office")
    def display_office(self, obj):
        return create_display(obj, "office", "description")

    @short_description("Office Type")
    def display_office_type(self, obj):
        return create_display(obj, "office_type", "description")

    @short_description("County")
    def display_county(self, obj):
        return create_display(obj, "county", "name")

    @short_description("Season")
    def display_election_season(self, obj):
        return create_display(obj, "election_season", "year")

    @short_description("Candidates")
    def display_candidates(self, obj):
        return obj.num_candidates

    @short_description("Winner")
    @boolean
    def has_winner(self, obj):
        return obj.winner is not None


@admin.register(RaceGroup)
class RaceGroupAdmin(admin.ModelAdmin):
    pass
