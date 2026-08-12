from django.contrib import admin
import decimal
from django import forms

from .models import *
from simple_history.admin import SimpleHistoryAdmin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.urls import path
from django.http import HttpResponse
from django.contrib import admin
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet


class LogEntryAdmin(admin.ModelAdmin):
    # Prevent modifying logs from the panel for security
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ['action_time', 'user', 'content_type', 'object_repr', 'action_flag_description']
    list_filter = ['action_time', 'user', 'action_flag']
    search_fields = ['object_repr', 'change_message']

    def action_flag_description(self, obj):
        if obj.action_flag == ADDITION:
            return format_html('<span style="color: green;">Created</span>')
        elif obj.action_flag == CHANGE:
            return format_html('<span style="color: orange;">Updated</span>')
        elif obj.action_flag == DELETION:
            return format_html('<span style="color: red;">Deleted</span>')
        return "Unknown"

    action_flag_description.short_description = 'Action Type'


class SubjectAdmin(admin.ModelAdmin):
    list_display = ["subject_name", "is_activity", "short_name"]


class CourseMemberForm(forms.ModelForm):
    parent_course = None  # will be set dynamically per inline instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs = Student.objects.all()
        if self.parent_course:
            qs = qs.exclude(
                coursemember__course=self.parent_course,
                coursemember__is_active=True
            )
        self.fields['student'].queryset = qs

        # Preserve the current row's own selected student even though
        # they'd otherwise get excluded by the rule above
        if self.instance and self.instance.pk:
            self.fields['student'].queryset = Student.objects.filter(pk=self.instance.student_id)


class CourseMemberFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen_students = {}

        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
                continue
            if form.cleaned_data.get('DELETE'):
                continue

            student = form.cleaned_data.get('student')
            if not student:
                continue

            if student in seen_students:
                # Point the error at THIS row's student field
                form.add_error('student', f"Siswa {student} sudah ditambah sebagai member sebelumnya.")
                # Also mark the FIRST row where this student appeared
                seen_students[student].add_error('student', f"Siswa {student} sudah ditambah sebagai member di bawahnya.")
            else:
                seen_students[student] = form




class CourseMemberInLine(admin.TabularInline):
    model = CourseMember
    fields = ("student", "is_active", "na_date", "na_reason")
    extra = 1
    form = CourseMemberForm
    formset = CourseMemberFormSet

    def get_formset(self, request, obj=None, **kwargs):
        class BoundForm(CourseMemberForm):
            parent_course = obj

        kwargs['form'] = BoundForm
        return super().get_formset(request, obj, **kwargs)


class CourseForm(forms.ModelForm):
    class Meta:
        labels = {
            'level': 'Grade',
        }

class CourseAdmin(admin.ModelAdmin):
    list_display = ["short_name", "academic_year", 'is_activity', 'get_teacher_name', 'count_students', 'level']
    list_filter = ['academic_year', 'level', 'is_activity']
    inlines = [CourseMemberInLine, ]
    search_fields = ["name"]
    # ganti nama 'level' ke 'grade', dicomment out untuk sekarang, bakal diaktifin lagi kalo mau diganti
    # form = CourseForm

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Target the specific ForeignKey field you want to filter
        if db_field.name == "subject":
            # Filter choices to show only active categories
            kwargs["queryset"] = Subject.objects.all()

            # Optional: Filter based on the currently logged-in admin user
            # if not request.user.is_superuser:
            #     kwargs["queryset"] = kwargs["queryset"].filter(owner=request.user)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_teacher_name(self, obj):
        return f"{obj.teacher.first_name} {obj.teacher.last_name}"

    get_teacher_name.short_description = "Teacher"

    # ganti nama 'level' to 'grade' di tabel, dicomment out dulu, diaktifin lagi kalo mau diganti
    # def level_to_grade(self, obj):
    #     return obj.level
    #
    # level_to_grade.short_description = "Grade"

    def count_students(self, obj: Course):
        return CourseMember.objects.filter(course_id=obj.id).count()

    def get_queryset(self, request):
        # Fetch the original base queryset
        qs = super().get_queryset(request)
        # is_teacher = User.groups.get(name="Teachers")

        # If the user is a superuser, show all records
        if request.user.is_superuser:
            return qs
        # For homeroom teachers, restrict records to their own
        elif request.user.groups.filter(name="Homeroom Teachers").exists():
            return qs.filter(teacher__user=request.user)
        else:
            return qs


class CourseMemberAdmin(admin.ModelAdmin):
    list_display = ["get_course_name", "student", "is_active"]
    # autocomplete_fields = ["student", "course"]
    form = CourseMemberForm

    def get_course_name(self, obj: CourseMember) -> str:
        return f"{obj.course.short_name}"

    get_course_name.short_description = "Course"

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if request.GET.get('model_name') == 'classmember':
            queryset = queryset.filter(coursemember__isnull=True)
            # print("Filtered count:", queryset.count())
        return queryset, use_distinct

    def student_name(self, obj: CourseMember):
        return f"{obj.student}"


class PassingGradeAdmin(admin.ModelAdmin):
    list_display = ["academic_year", "subject", "level", "passing_grade"]


class AssignmentTypeAdmin(admin.ModelAdmin):
    list_display = ["short_name", "name"]


class WeightingForm(forms.ModelForm):
    class Meta:
        model = Weighting
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        acayear = None
        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.filter(
                academic_year_id=acayear, period_name__icontains='semester'
            )
        else:
            self.fields['period'].queryset = LearningPeriod.objects.filter(
                period_name__icontains='semester'
            )  # show all instead of none, so add view isn't empty


class WeightingAdmin(admin.ModelAdmin):
    list_display = ["academic_year", "period", "mid_sem", "subject", "assignment", "format_percentage"]
    list_filter = ["academic_year", "period", "subject", "is_mid"]
    form = WeightingForm

    def format_percentage(self, obj: Weighting) -> decimal:
        return obj.weight * 100

    format_percentage.short_description = "Weight %"

    # def filter_period(self, request, obj=None, **kwargs):
    #     qs = super().get_queryset(request)
    #     if obj and obj.academic_year:  # If the object exists and has a value
    #         # Filter the 'related_item' field based on the 'category' field
    #         qs.base_fields['academic_year'].queryset = LearningPeriod.objects.filter(
    #             academic_year=obj.academic_year
    #         )
    #     return qs

    @admin.display(description="Mid Semester?")
    def mid_sem(self, obj):
        if obj.is_mid == True:
            return "Yes"
        else:
            return "No"


class GradeEntryAdmin(admin.ModelAdmin):
    list_display = ("academic_year", "course", "period", "subject", "teacher")

    def delete_queryset(self, request, queryset):
        pass


class RubricIndicatorAdmin(admin.TabularInline):
    model = RubricIndicator


class RubricAdmin(admin.ModelAdmin):
    list_display = ("type", "description", "index")
    list_filter = ["type"]
    inlines = [RubricIndicatorAdmin]


class ReportcardGradeAdmin(admin.TabularInline):
    model = ReportcardGrade


class StudentReportcardAdmin(admin.ModelAdmin):
    list_display = ("academic_year", "period", "is_mid", "level", "student")
    list_filter = ["academic_year", "period", "is_mid", "student"]
    inlines = [ReportcardGradeAdmin]


class StudentReportcardHistory(SimpleHistoryAdmin):
    list_display = ("academic_year", "period", "is_mid", "level", "student")
    history_list_display = ["academic_year", "is_mid", "student"]
    inlines = [ReportcardGradeAdmin]


class ReportcardGradeAdmin(admin.ModelAdmin):
    list_display = ("reportcard", "subject", "grade", "comments")
    history_list_display = ["reportcard", "subject"]
    max_num = 0


class ReportCardGradeHistory(SimpleHistoryAdmin):
    list_display = ("reportcard", "subject")
    history_list_display = ["reportcard", "subject"]


class GradeLevelAdmin(admin.ModelAdmin):
    list_display = ("grade_name", "school_level", "short_name")
    list_filter = ["school_level"]


class StudentBehaviorAdmin(admin.ModelAdmin):
    list_display = ("student", "behavior", "rubric", "score")
    list_filter = ["student", "behavior", "rubric", "score"]


class StudentReportExtraAdmin(admin.ModelAdmin):
    list_display = ("reportcard", "extra_type", "extra_description", "extra_score", "extra_notes")
    list_filter = ["reportcard", "extra_type", "extra_description", "extra_score", "extra_notes"]


class ReportcardRubricTemplateAdmin(admin.ModelAdmin):
    list_display = ("academic_year", "rubric", "lookup_grade", "text")
    list_filter = ["academic_year", "rubric", "lookup_grade", "text"]


class StudentBehaviourReportAdmin(admin.ModelAdmin):
    list_display = ("score", "rubric", "student", "description", "grade")
    list_filter = ["score", "rubric", "student", "description", "grade"]


class CapaianPemelajaranLulusanAdmin(admin.ModelAdmin):
    list_display = ("text",)
    list_filter = ["text", ]


class AssignmentHeadAdmin(admin.ModelAdmin):
    list_display = ("date", "topic", "max_score", "assignment", "course")
    list_filter = ["date", "topic", "max_score", "assignment", "course"]


class AssignmentDetailAdmin(admin.ModelAdmin):
    list_display = ("is_active", "na_date", "na_reason", "student", "score")
    list_filter = ["is_active", "na_date", "na_reason", "student"]


class CPMPForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['cpl_root'].choices = CapaianPemelajaranLulusan.objects.all().values_list('id', 'text')


# class LockData(forms.ModelForm):
#     list_display = ("lock_start", "lock_end")


class CapaianPemelajaranMataPelajaranAdmin(admin.ModelAdmin):
    list_display = ("academic_year", "level", "subject", "get_cpl_str", "text")
    list_filter = ["academic_year", "level", "subject"]
    form = CPMPForm

    def get_cpl_str(self, obj: CapaianPemelajaranMataPelajaran) -> str:
        return f"{obj.cpl_root.text}"

    get_cpl_str.short_description = "Capaian Pembelajaran Lulusan"


class PDRPTAdminForm(forms.ModelForm):
    class Meta:
        label = {
            'care1': 'test'
        }


class PDRPTAdmin(admin.ModelAdmin):
    list_display = ("reporcard",)
    list_filter = ["reporcard", ]
    form = PDRPTAdminForm


# class LockDataEntryAdmin(admin.ModelAdmin):
#     list_display = ["lock_start", "lock_end"]
#
#     def has_add_permission(self, request):
#         return not LockDataEntry.objects.exists()
#
#     def has_delete_permission(self, request, obj=None):
#         return False
#
#     def changelist_view(self, request, extra_context=None):
#         obj, created = LockDataEntry.objects.get_or_create(
#             pk=1,
#             defaults={'lock_start': None, 'lock_end': None}
#         )
#         return redirect(f'/admin/gradebook/lockdataentry/{obj.pk}/change/')


@staff_member_required
def admin_statistics_view(request):
    return render(request, "admin/statistics.html", {
        "title": "Statistics"
    })


class CustomAdminSite(admin.AdminSite):
    def get_app_list(self, request, _=None):
        app_list = super().get_app_list(request)
        app_list += [
            {
                "name": "My Custom App",
                "app_label": "my_custom_app",
                "models": [
                    {
                        "name": "Statistics",
                        "object_name": "statistics",
                        "admin_url": "/admin/statistics",
                        "view_only": True,
                    }
                ],
            }
        ]
        return app_list

    def get_urls(self):
        urls = super().get_urls()
        urls += [
            path("statistics/", admin_statistics_view, name="admin-statistics"),
        ]
        return urls


# Register your models here.
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Course, CourseAdmin)
# admin.site.register(CourseMember, CourseMemberAdmin)
admin.site.register(AssignmentType, AssignmentTypeAdmin)
admin.site.register(Weighting, WeightingAdmin)
admin.site.register(PassingGrade, PassingGradeAdmin)
admin.site.register(GradeEntry, GradeEntryAdmin)
admin.site.register(Rubric, RubricAdmin)
admin.site.register(StudentReportcard, StudentReportcardAdmin)
admin.site.register(StudentReportExtra, StudentReportExtraAdmin)
# admin.site.register(RubricIndicator)
# admin.site.register(StudentReportcard, StudentReportcardHistory)
admin.site.register(ReportcardGrade, ReportCardGradeHistory)
# admin.site.register(GradeLevel, GradeLevelAdmin)
admin.site.register(ReportcardRubricTemplate, ReportcardRubricTemplateAdmin)
admin.site.register(StudentBehaviourReport, StudentBehaviourReportAdmin)
# admin.site.register(CapaianPemelajaranLulusan, CapaianPemelajaranLulusanAdmin)
admin.site.register(CapaianPemelajaranMataPelajaran, CapaianPemelajaranMataPelajaranAdmin)
admin.site.register(ReportcardPersonalDev, PDRPTAdmin)
admin.site.register(AssignmentHead, AssignmentHeadAdmin)
admin.site.register(AssignmentDetail, AssignmentDetailAdmin)
# admin.site.register(LockDataEntry, LockDataEntryAdmin)