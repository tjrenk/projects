from django.contrib import admin

# Register your models here.
from admission.models import *
from django import forms


class AcademicYearAdmin(admin.ModelAdmin):
    pass
    #list_display = ["year", "begin_date", "end_date"]

class LearningPeriodAdmin(admin.ModelAdmin):
    list_display = ["academic_year", "period_name", "date_start", "date_end"]
    list_filter = ["academic_year", "period_name"]


class RegistrationAdmin(admin.ModelAdmin):
    list_display = ["form_no", "first_name", "last_name", "date_of_birth", "gender"]
    list_filter = ["form_no", "first_name", "last_name"]
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Change individual field labels here
        form.base_fields['nisn'].label = "NISN"
        form.base_fields['mother_name'].label = "Mother's Name"
        form.base_fields['mother_nik'].label = "Mother's NIK"
        form.base_fields['mother_religion'].label = "Mother's Religion"
        form.base_fields['mother_occupation'].label = "Mother's Occupation"
        form.base_fields['mother_address'].label = "Mother's Address"
        form.base_fields['mother_education'].label = "Mother's Last Education"
        form.base_fields['mother_phone'].label = "Mother's Phone Number"
        form.base_fields['mother_mobile'].label = "Mother's Mobile Phone Number"
        form.base_fields['mother_email'].label = "Mother's Email Address"
        form.base_fields['mother_address_same2applicant'].label = "Is the mother's address same as the applicant?"
        form.base_fields['father_name'].label = "Father's Name"
        form.base_fields['father_nik'].label = "Father's NIK"
        form.base_fields['father_religion'].label = "Father's Religion"
        form.base_fields['father_occupation'].label = "Father's Occupation"
        form.base_fields['father_address'].label = "Father's Address"
        form.base_fields['father_education'].label = "Father's Last Education"
        form.base_fields['father_phone'].label = "Father's Phone Number"
        form.base_fields['father_mobile'].label = "Father's Mobile Phone Number"
        form.base_fields['father_email'].label = "Father's Email Address"
        form.base_fields['contact_mobile'].label = "Mobile Phone Number"
        form.base_fields['contact_email'].label = "Email Address"
        form.base_fields['contact_preference'].label = "Prefer to be contacted by:"
        form.base_fields['father_address_same2applicant'].label = "Is the father's address same as the applicant?"
        return form


class StudentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # taroh logic dibawah
        self.fields['registration_data'].queryset = Registration.objects.filter(student__isnull=True)
        if self.instance and self.instance.pk:
            self.fields['registration_data'].queryset = Registration.objects.filter(pk=self.instance.registration_data_id)

class StudentAdmin(admin.ModelAdmin):
    form = StudentForm
    list_display = [
        "id_number",
        "registration_data__first_name",
        "registration_data__last_name",
        "nisn",
        "is_active",
    ]
    list_filter = ["is_active", "registration_data__first_name", "registration_data__last_name", "nisn"]
    search_fields = ["registration_data__first_name", "registration_data__last_name"]




class TeacherAdmin(admin.ModelAdmin):
    list_display = ["fullname_wtitle", "join_date", "user__username"]
    list_filter = ["first_name", "last_name", "fullname_wtitle", "user__username"]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Change individual field labels here
        form.base_fields['fullname_wtitle'].label = "Full Name and Title"
        return form

    def fullname_wtitle_fixed(self, obj):
        return obj.fullname_wtitle
    fullname_wtitle_fixed.short_description = "Full Name and Title"

    # def get_queryset(self, request):
    #     # Fetch the original base queryset
    #     qs = super().get_queryset(request)
    #
    #     # If the user is a superuser, show all records
    #     if request.user.is_superuser:
    #         return qs
    #
    #     # For regular staff users, restrict records to their own
    #     return qs.filter(user=request.user)


class ClassMemberInline(admin.TabularInline):
    model = ClassMember
    fields = ("student", "is_active", "na_date", "na_reason")
    max_num = 1

class KelasAdmin(admin.ModelAdmin):
    list_display = ["name", "academic_year", "short_name", "teacher", "count_students"]
    list_filter = ["academic_year", "teacher"]
    search_fields = ["academic_year__class__name"]
    inlines = [ ClassMemberInline, ]
    def count_students(self, obj: Class):
        return ClassMember.objects.filter(kelas_id=obj.id).count()

    def get_queryset(self, request):
        # Fetch the original base queryset
        qs = super().get_queryset(request)

        # If the user is a superuser, show all records
        if request.user.is_superuser:
            return qs

        # For regular staff users, restrict records to their own
        return qs.filter(teacher__user=request.user)

class ClassMemberForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # taroh logic dibawah
        self.fields['student'].queryset = Student.objects.filter(classmember__isnull=True)
        if self.instance and self.instance.pk:
            self.fields['student'].queryset = Student.objects.filter(pk=self.instance.student_id)

class ClassMemberAdmin(admin.ModelAdmin):
    list_display = ["kelas", "student_name"]
    list_filter = ["student", "student__registration_data__gender", "kelas"]
    autocomplete_fields = ["student", "kelas"]

    def student_name(self, obj: ClassMember):
        return f"{obj.student}"

    def get_queryset(self, request):
        # Fetch the original base queryset
        qs = super().get_queryset(request)

        # If the user is a superuser, show all records
        if request.user.is_superuser:
            return qs

        # For regular staff users, restrict records to their own
        return qs.filter(kelas__teacher__user=request.user)
    
class ReligionAdmin(admin.ModelAdmin):
    list_display = ["religion_name"]

class GradeLevelAdmin(admin.ModelAdmin):
    list_display = ["school_level", "grade_name", "short_name"]

class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "is_active", "created_at", "updated_at"]
    list_filter = ["title", "author", "is_active", "created_at", "updated_at"]


    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        # Sets the default author field to the logged-in user
        initial['author'] = request.user.id
        return initial



admin.site.register(Registration, RegistrationAdmin)
admin.site.register(AcademicYear, AcademicYearAdmin)
admin.site.register(LearningPeriod, LearningPeriodAdmin)
admin.site.register(Teacher, TeacherAdmin)
admin.site.register(Class, KelasAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(ClassMember, ClassMemberAdmin)
admin.site.register(SchoolData)
admin.site.register(SchoolLevel)
admin.site.register(HeadMaster)
admin.site.register(Religion, ReligionAdmin)
admin.site.register(GradeLevel, GradeLevelAdmin)
admin.site.register(Announcement, AnnouncementAdmin)