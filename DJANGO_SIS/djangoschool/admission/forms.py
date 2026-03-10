from django import forms
from django.forms import modelform_factory, formset_factory
from .models import Registration, AbstractPerson

class PersonalInfoForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['form_no', 'first_name', 'middle_name', 'last_name', 'gender', 'nisn', 'prev_school', 'prev_nis', 'date_of_birth', 'place_of_birth', 'birth_order', 'religion', 'church_name']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        }

class ContactInfoForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['current_address', 'current_district', 'current_region', 'current_city', 'current_province', 'contact_whatsapp', 'contact_mobile', 'contact_email', 'contact_preference', ]

class ParentInfoForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['mother_name', 'mother_nik', 'mother_religion', 'mother_education', 'mother_occupation', 'mother_address_same2applicant', 'mother_address', 'mother_district', 'mother_region', 'mother_city', 'mother_province', 'mother_phone', 'mother_mobile', 'mother_whatsapp', 'mother_email',
                  'father_name', 'father_nik', 'father_religion', 'father_education', 'father_occupation', 'father_address_same2applicant', 'father_address', 'father_district', 'father_region', 'father_city', 'father_province', 'father_phone', 'father_mobile', 'father_whatsapp', 'father_email']
        
        def clean(self):
            cleaned_data = super().clean()
            mother_same = cleaned_data.get('mother_address_same2applicant')
            father_same = cleaned_data.get('father_address_same2applicant')
            registration_instance = self.instance
            if mother_same:
                cleaned_data['mother_address'] = registration_instance.current_address
                cleaned_data['mother_district'] = registration_instance.current_district
                cleaned_data['mother_region'] = registration_instance.current_region
                cleaned_data['mother_city'] = registration_instance.current_city
                cleaned_data['mother_province'] = registration_instance.current_province

            if father_same:
                cleaned_data['father_address'] = registration_instance.current_address
                cleaned_data['father_district'] = registration_instance.current_district
                cleaned_data['father_region'] = registration_instance.current_region
                cleaned_data['father_city'] = registration_instance.current_city
                cleaned_data['father_province'] = registration_instance.current_province
            
            return cleaned_data
        
    