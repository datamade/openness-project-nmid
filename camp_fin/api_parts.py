import csv
from io import StringIO, BytesIO
import zipfile

from rest_framework import serializers, pagination, renderers
from rest_framework_csv.renderers import CSVStreamingRenderer

from camp_fin.models import Candidate, PAC, Transaction, LoanTransaction, \
    Loan, Treasurer, Address

class CandidateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Candidate
        fields = '__all__'

class PACSerializer(serializers.ModelSerializer):

    class Meta:
        model = PAC
        fields = '__all__'

class LoanSerializer(serializers.ModelSerializer):

    class Meta:
        model = Loan
        fields = '__all__'

class LoanTransactionSerializer(serializers.ModelSerializer):
    loan = LoanSerializer(read_only=True)
    transaction_type = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = LoanTransaction
        fields = '__all__'

class EntityField(serializers.RelatedField):

    def to_representation(self, value):
        
        try:
            if value.entity.pac_set.all():
                serializer = PACSerializer(value.entity.pac_set.first())
            
            elif value.entity.candidate_set.all():
                serializer = CandidateSerializer(value.entity.candidate_set.first())
            
            else:
                return {}

            return serializer.data
        except AttributeError:
            return value


class TransactionSerializer(serializers.ModelSerializer):
    transaction_type = serializers.StringRelatedField(read_only=True)
    full_name = serializers.StringRelatedField(read_only=True)
    transaction_subject = EntityField(read_only=True)

    class Meta:
        model = Transaction
        
        fields = (
            'id',
            'amount', 
            'received_date', 
            'date_added', 
            'check_number',
            'memo',
            'description',
            'transaction_type',
            'name_prefix',
            'first_name',
            'middle_name',
            'last_name',
            'suffix',
            'company_name',
            'full_name',
            'address',
            'city',
            'state',
            'zipcode',
            'full_address',
            'country',
            'occupation',
            'expenditure_for_certified_candidate',
            'transaction_subject'
        )

class TransactionSearchSerializer(TransactionSerializer):
    pac_slug = serializers.StringRelatedField(read_only=True)
    candidate_slug = serializers.StringRelatedField(read_only=True)
    donor_occupation = serializers.CharField(read_only=True)
    full_address = serializers.CharField(read_only=True)
    address_id = serializers.CharField(read_only=True)
    
    class Meta:
        model = Transaction
        
        fields = (
            'id',
            'amount', 
            'received_date', 
            'date_added', 
            'check_number',
            'memo',
            'description',
            'transaction_type',
            'name_prefix',
            'first_name',
            'middle_name',
            'last_name',
            'suffix',
            'company_name',
            'full_name',
            'full_address',
            'address_id',
            'address',
            'city',
            'state',
            'zipcode',
            'full_address',
            'country',
            'occupation',
            'expenditure_for_certified_candidate',
            'donor_occupation',
            'transaction_subject',
            'pac_slug',
            'candidate_slug',
        )

class TreasurerSearchSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    street = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    zipcode = serializers.CharField()
    related_entity_name = serializers.CharField()
    related_entity_url = serializers.CharField()

class CandidateSearchSerializer(serializers.ModelSerializer):
    county_name = serializers.StringRelatedField(read_only=True)
    election_year = serializers.StringRelatedField(read_only=True)
    party_name = serializers.StringRelatedField(read_only=True)
    office_name = serializers.StringRelatedField(read_only=True)
    office_type = serializers.StringRelatedField(read_only=True)
    district_name = serializers.StringRelatedField(read_only=True)
    division_name = serializers.StringRelatedField(read_only=True)
    committee_name = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Candidate
        fields = (
            'id',
            'prefix',
            'first_name',
            'middle_name',
            'last_name',
            'full_name',
            'suffix',
            'business_phone',
            'home_phone',
            'date_added',
            'email',
            'date_updated',
            'deceased',
            'slug',
            'county_name',
            'election_year',
            'party_name',
            'office_name',
            'office_type',
            'district_name',
            'division_name',
            'committee_name',
        )

class PACSearchSerializer(serializers.ModelSerializer):
    address = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = PAC
        fields = (
            'id',
            'name',
            'acronym',
            'business_phone',
            'home_phone',
            'email',
            'date_added',
            'date_updated',
            'bank_name',
            'bank_phone',
            'fax_number',
            'initial_balance',
            'initial_balance_from_self',
            'initial_debt',
            'initial_debt_from_self',
            'slug',
            'address',
        )

class TopMoneySerializer(serializers.Serializer):
    name_prefix = serializers.CharField()
    first_name = serializers.CharField()
    middle_name = serializers.CharField()
    last_name = serializers.CharField()
    suffix = serializers.CharField()
    company_name = serializers.CharField()
    amount = serializers.CharField()
    year = serializers.CharField()
    rank = serializers.CharField()
    latest_date = serializers.DateTimeField()

class DataTablesPagination(pagination.LimitOffsetPagination):
    limit_query_param = 'length'
    offset_query_param = 'start'

class TransactionCSVRenderer(CSVStreamingRenderer):
    
    def render(self, data, *args, **kwargs):
        return super().render(data['results'], *args, **kwargs)

class SearchCSVRenderer(renderers.BaseRenderer):
    media_type = 'application/zip'
    format = 'csv'

    def render(self, data, media_type=None, renderer_context=None):
        table_names = [
            'candidate',
            'pac',
            'contribution',
            'expenditure',
            'treasurer',
        ]
        
        zfoutp = BytesIO()

        with zipfile.ZipFile(zfoutp, 'w') as zf:
            
            for table in table_names:
                
                if data.get(table):

                    try:
                        first_record = data[table]['objects'][0]
                    except IndexError:
                        continue

                    outp = StringIO()
                    
                    fieldnames = first_record._fields 
                    writer = csv.writer(outp)
                    
                    writer.writerow(fieldnames)
                    writer.writerows(data[table]['objects'])
                    
                    outp.seek(0)
                    zf.writestr('{}.csv'.format(table), outp.getvalue())
        
        zfoutp.seek(0)

        return zfoutp.getvalue()
