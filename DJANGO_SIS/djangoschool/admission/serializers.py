from rest_framework import serializers
from .models import Registration

class RegSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = ['form_no', 'first_name', 'middle_name', 'last_name', 'gender', 'nisn', 'prev_school', 'prev_nis', 'date_of_birth', 'place_of_birth', 'birth_order', 'religion', 'church_name']