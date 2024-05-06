import sys

from django import forms
from django.apps import apps
from django.contrib import admin
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.management import call_command

from camp_fin.decorators import boolean, short_description
from camp_fin.models import Campaign, Race, RaceGroup, Story, Candidate


def get_generic_fields():
    """Return a list of all GenericForeignKeys in all models."""
    generic_fields = []
    for model in apps.get_models():
        for field_name, field in model.__dict__.items():
            if isinstance(field, GenericForeignKey):
                generic_fields.append(field)
    return generic_fields


def merge_candidates(primary_object, alias_objects):
    """
    Merge several model instances into one, the `primary_object`.
    Use this function to merge model objects and migrate all of the related
    fields from the alias objects the primary object.
    """
    generic_fields = get_generic_fields()

    # get related fields
    related_fields = list(filter(
        lambda x: x.is_relation is True,
        primary_object._meta.get_fields()))

    many_to_many_fields = list(filter(
        lambda x: x.many_to_many is True, related_fields))

    related_fields = list(filter(
        lambda x: x.many_to_many is False, related_fields))

    # Loop through all alias objects and migrate their references to the
    # primary object
    deleted_objects = []
    deleted_objects_count = 0
    for alias_object in alias_objects:
        # Migrate all foreign key references from alias object to primary
        # object.
        for many_to_many_field in many_to_many_fields:
            alias_varname = many_to_many_field.name
            related_objects = getattr(alias_object, f"{alias_varname}_set")
            for obj in related_objects.all():
                try:
                    # Handle regular M2M relationships.
                    getattr(alias_object, alias_varname).remove(obj)
                    getattr(primary_object, alias_varname).add(obj)
                except AttributeError:
                    # Handle M2M relationships with a 'through' model.
                    # This does not delete the 'through model.
                    # TODO: Allow the user to delete a duplicate 'through' model.
                    through_model = getattr(alias_object, alias_varname).through
                    kwargs = {
                        many_to_many_field.m2m_reverse_field_name(): obj,
                        many_to_many_field.m2m_field_name(): alias_object,
                    }
                    through_model_instances = through_model.objects.filter(**kwargs)
                    for instance in through_model_instances:
                        # Re-attach the through model to the primary_object
                        setattr(
                            instance,
                            many_to_many_field.m2m_field_name(),
                            primary_object)
                        instance.save()
                        # TODO: Here, try to delete duplicate instances that are
                        # disallowed by a unique_together constraint

        for related_field in related_fields:
            if related_field.one_to_many:
                alias_varname = related_field.get_accessor_name()
                related_objects = getattr(alias_object, alias_varname)
                for obj in related_objects.all():
                    field_name = related_field.field.name
                    setattr(obj, field_name, primary_object)
                    obj.save()
            elif related_field.one_to_one or related_field.many_to_one:
                alias_varname = related_field.name
                related_object = getattr(alias_object, alias_varname)
                primary_related_object = getattr(primary_object, alias_varname)
                if primary_related_object is None:
                    setattr(primary_object, alias_varname, related_object)
                    primary_object.save()
                elif related_field.one_to_one:
                    sys.stdout.write("Deleted {} with id {}\n".format(
                        related_object, related_object.id))
                    related_object.delete()

        for field in generic_fields:
            filter_kwargs = {}
            filter_kwargs[field.fk_field] = alias_object._get_pk_val()
            filter_kwargs[field.ct_field] = field.get_content_type(alias_object)
            related_objects = field.model.objects.filter(**filter_kwargs)
            for generic_related_object in related_objects:
                setattr(generic_related_object, field.name, primary_object)
                generic_related_object.save()

        if alias_object.id:
            deleted_objects += [alias_object]
            sys.stdout.write("Deleted {} with id {}\n".format(
                alias_object, alias_object.id))
            alias_object.delete()
            deleted_objects_count += 1

    return primary_object, deleted_objects, deleted_objects_count

@admin.register(Candidate)
class MergeCandidateAdmin(admin.ModelAdmin):

    fields = ("full_name",)
    readonly_fields = ("full_name",)

    """
    TODO:
    - Add multiselect field to pick one/more candidates to merge
    - Add (override?) method to run merge_candidates on primary and 
    selected subsidiary candidates
    """

    


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


