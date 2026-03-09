from django.contrib import admin

# Register your models here.
from .models import (Registration, AcademicYear, LearningPeriod,
                     SchoolData, SchoolLevel, HeadMaster,
                     Teacher, Student, Class, ClassMember, Religion, GradeLevel)


class AcademicYearAdmin(admin.ModelAdmin):
    pass
    #list_display = ["year", "begin_date", "end_date"]

class LearningPeriodAdmin(admin.ModelAdmin):
    list_display = ["academic_year", "period_name", "date_start", "date_end"]

class RegistrationAdmin(admin.ModelAdmin):
    list_display = ["form_no", "first_name", "last_name", "date_of_birth", "gender"]

class StudentAdmin(admin.ModelAdmin):
    list_display = [
        "id_number",
        "registration_data__first_name",
        "registration_data__last_name",
        "nisn",
        "is_active",
    ]
    list_filter = ["is_active",]
    search_fields = ["registration_data__first_name"]

class TeacherAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "join_date", "user__username"]


class ClassMemberInline(admin.TabularInline):
    model = ClassMember
    fields = ("is_active", "na_date", "na_reason")
    max_num = 0

class KelasAdmin(admin.ModelAdmin):
    list_display = ["academic_year", "short_name", "teacher", "count_students"]
    search_fields = ["academic_year__class__name"]
    inlines = [ ClassMemberInline, ]
    def count_students(self, obj: Class):
        return ClassMember.objects.filter(kelas_id=obj.id).count()

class ClassMemberAdmin(admin.ModelAdmin):
    list_display = ["kelas", "student_name"]
    list_filter = ["student__registration_data__gender",]
    autocomplete_fields = ["student", "kelas"]

    def student_name(self, obj: ClassMember):
        return f"{obj.student}"
    
class ReligionAdmin(admin.ModelAdmin):
    list_display = ["religion_name"]

class GradeLevelAdmin(admin.ModelAdmin):
    list_display = ["school_level", "grade_name", "short_name"]




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