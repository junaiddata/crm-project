import os
from rest_framework import serializers
from .models import Lead


class LeadSerializer(serializers.ModelSerializer):
    mobileNo        = serializers.CharField(source='mobile_no', allow_blank=True, required=False)
    emailId         = serializers.CharField(source='email_id', allow_blank=True, required=False)
    salesPerson     = serializers.CharField(source='sales_person', allow_blank=True, required=False)
    quotation       = serializers.CharField(allow_blank=True, required=False)
    quotationDate   = serializers.DateField(source='quotation_date', allow_null=True, required=False)
    followUp1Date   = serializers.DateField(source='follow_up1_date', allow_null=True, required=False)
    followUp1Notes  = serializers.CharField(source='follow_up1_notes', allow_blank=True, required=False)
    followUp2Date   = serializers.DateField(source='follow_up2_date', allow_null=True, required=False)
    followUp2Notes  = serializers.CharField(source='follow_up2_notes', allow_blank=True, required=False)
    leadStatus      = serializers.CharField(source='lead_status', allow_blank=True, required=False)
    quotationFile   = serializers.SerializerMethodField()
    source          = serializers.CharField(read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'date', 'mobileNo', 'emailId', 'name', 'platform', 'items',
            'salesPerson', 'quotation', 'quotationFile', 'quotationDate',
            'followUp1Date', 'followUp1Notes', 'followUp2Date', 'followUp2Notes',
            'leadStatus', 'source',
        ]

    def get_quotationFile(self, obj):
        if not obj.quotation_file:
            return None
        request = self.context.get('request')
        url = (
            request.build_absolute_uri(obj.quotation_file.url)
            if request else obj.quotation_file.url
        )
        return {'name': os.path.basename(obj.quotation_file.name), 'data': url}
