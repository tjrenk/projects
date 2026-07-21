from django import forms
from django.forms import modelform_factory, formset_factory
from admission.models import *
from gradebook.models import *

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
        fields = ['current_address', 'contact_mobile', 'contact_email', 'contact_preference', ]

class ParentInfoForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['mother_name', 'mother_nik', 'mother_religion', 'mother_education', 'mother_occupation', 'mother_address_same2applicant', 'mother_address', 'mother_phone', 'mother_mobile', 'mother_email',
                  'father_name', 'father_nik', 'father_religion', 'father_education', 'father_occupation', 'father_address_same2applicant', 'father_address', 'father_phone', 'father_mobile', 'father_email']
        
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


class AssignHomeroomAndClassForm(forms.Form):

    student = forms.ModelChoiceField(
        queryset=Student.objects.filter(classmember__isnull=True),
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
        label='Student'
    )

    kelas = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
        label='Homeroom Class'
    )

    course = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'custom-checkbox-list'}),
        label='Assign a Class',
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        kelas = cleaned_data.get('kelas')

        if student and kelas:
            already_assigned = ClassMember.objects.filter(
                student=student,
                kelas=kelas,
                is_active=True
            ).exists()

            if already_assigned:
                raise forms.ValidationError(
                    f"{student} is already assigned to {kelas}."
                )

        return cleaned_data
    