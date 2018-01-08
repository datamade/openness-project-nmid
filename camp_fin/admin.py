from django.contrib import admin
from django import forms

from camp_fin.models import Race, RaceGroup, Campaign


class RaceForm(forms.ModelForm):

    class Meta:
        model = Race
        fields = ['winner']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['winner'].queryset = Campaign.objects\
                                                 .filter(active_race__id=self.instance.id)


class WinnerFilter(admin.SimpleListFilter):
    '''
    Filter Races based on whether they have a Winner or not.
    '''
    title = 'whether a winner exists'
    parameter_name = 'winner'

    def lookups(self, request, model_admin):
        '''
        Filter options that the user can choose, in the form:

        (<parameter>, <human_readable_string>)
        '''
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        '''
        Restrict the queryset based on the parameter the user has chosen.
        '''

        if self.value() == 'yes':
            return queryset.filter(winner__isnull=False)

        elif self.value() == 'no':
            return queryset.filter(winner__isnull=True)


@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    relevant_fields = ('__str__', 'display_division', 'display_district',
                       'display_office', 'display_office_type', 'display_county',
                       'display_election_season', 'display_candidates', 'has_winner')

    list_display = relevant_fields
    list_filter = (WinnerFilter, 'election_season__year')
    form = RaceForm
    search_fields = ('office__description',)

    def create_display(self, obj, attr, field):
        attribute = getattr(getattr(obj, attr), field, None)

        if attribute:
            return attribute
        else:
            return '--'

    def display_division(self, obj):
        return self.create_display(obj, 'division', 'name')

    def display_district(self, obj):
        return self.create_display(obj, 'district', 'name')

    def display_office(self, obj):
        return self.create_display(obj, 'office', 'description')

    def display_office_type(self, obj):
        return self.create_display(obj, 'office_type', 'description')

    def display_county(self, obj):
        return self.create_display(obj, 'county', 'name')

    def display_election_season(self, obj):
        return self.create_display(obj, 'election_season', 'year')

    def display_candidates(self, obj):
        return obj.num_candidates

    def has_winner(self, obj):
        return obj.winner is not None

    display_division.short_description = 'Division'
    display_district.short_description = 'District'
    display_office.short_description = 'Office'
    display_office_type.short_description = 'Office Type'
    display_county.short_description = 'County'
    display_election_season.short_description = 'Season'
    display_candidates.short_description = 'Candidates'
    has_winner.short_description = 'Winner'
    has_winner.boolean = True

@admin.register(RaceGroup)
class RaceGroupAdmin(admin.ModelAdmin):
    pass
