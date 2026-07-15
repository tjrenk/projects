from django.db.models import Q
from django.shortcuts import get_object_or_404
from django import forms
from datetime import datetime
from slick_reporting.forms import BaseReportForm
from django.forms import modelform_factory, formset_factory, modelformset_factory, BaseFormSet
# from .models import GradeEntry, AssignmentHead, AssignmentDetail, StudentAttendance, ReportcardGrade, StudentReportcard, Subject, Course, LearningPeriod, AcademicYear, AssignmentType
# from admission.models import Class, ClassMember, GradeLevel, Teacher, AbstractClass, Student, SchoolLevel
from gradebook.models import *
from admission.models import *
import re
from django.utils.safestring import mark_safe

# Define grade choices
FINAL_GRADE_CHOICES = [
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),
    ('D', 'D'),
    ('E', 'E'),
]


# biar jadi text, bukan field yang gabisa diapa2in
class PlainTextWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        # Render the value as a simple span or string
        # You can add style/classes here if needed
        return mark_safe(f'<span class="form-control-plaintext">{value or ""}</span>')



# Form Step 1
class GradeEntryForm(forms.ModelForm):
    cpmp_target = forms.ModelMultipleChoiceField(
        queryset=CapaianPemelajaranMataPelajaran.objects.all(),
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'custom-checkbox-list'}),
        label="Tujuan Pembelajaran"
    )

    class Meta:
        model = GradeEntry
        fields = ["level", "academic_year", "period", "teacher", "subject", "course", "assignment_type"]
        labels = {
            'course': "Sub-level",
        }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        data = self.data
        initial = self.initial

        is_admin = user and (user.is_staff or user.is_superuser)

        # Default Logic for Logged-in Teacher
        if user and not self.is_bound and not is_admin:
            teacher_obj = Teacher.objects.filter(user=user).first()
            if teacher_obj:
                self.initial['teacher'] = teacher_obj.id
                
                # Filter and potentially default Subject
                teacher_subjects = Subject.objects.filter(course__teacher=teacher_obj).distinct()
                if teacher_subjects.count() == 1:
                    self.initial['subject'] = teacher_subjects.first().id

            # Default to the most recent Academic Year and Period
            # curr_ay = AcademicYear.objects.order_by('-id').first()
            # if curr_ay:
            #     self.initial['academic_year'] = curr_ay.id
            # curr_period = LearningPeriod.objects.filter(Q(academic_year=curr_ay) & Q(period_name__icontains='semester')).order_by('-id').first()
            curr_period = LearningPeriod.objects.filter(
                Q(period_name__icontains='semester')).order_by('-id').first()
            if curr_period:
                self.initial['period'] = curr_period.id
        
        acayear = data.get('0-academic_year') or initial.get('academic_year')
        level = data.get('0-level') or initial.get('level')
        period = data.get('0-period') or initial.get('period')
        teacher = data.get('0-teacher') or initial.get('teacher')
        subject = data.get('0-subject') or initial.get('subject')
        course = data.get('0-course') or initial.get('course')
        assignment_type = data.get('0-assignment_type') or initial.get('assignment_type')
        cpmp_target = data.get('0-cpmp_target') or initial.get('cpmp_target')

        # 2. Logic: Period depends on Academic Year


        # niatnya mau set semuanya jadi kosong sebagai default value (value buat field yg ga ketouch)
        # self.fields['period'].queryset = LearningPeriod.objects.none()
        # self.fields['level'].queryset = GradeLevel.objects.none()
        # self.fields['teacher'].queryset = Teacher.objects.none()
        # self.fields['cpmp_target'].queryset = CapaianPemelajaranLulusan.objects.none()
        # self.fields['course'].queryset = Course.objects.none()
        # self.fields['assignment_type'].queryset = AssignmentType.objects.none()

        self.fields['cpmp_target'].label_from_instance = lambda obj: obj.text
        # buat validasi
        if acayear:
            self.fields['cpmp_target'].queryset = CapaianPemelajaranMataPelajaran.objects.filter(
                academic_year_id=acayear, subject_id=subject
            )
            self.fields['period'].queryset = LearningPeriod.objects.filter(academic_year_id=acayear, period_name__icontains='semester')
            self.fields['level'].queryset = GradeLevel.objects.all()
            if is_admin:
                self.fields['period'].queryset = LearningPeriod.objects.all()
                self.fields['level'].queryset = GradeLevel.objects.all()
                self.fields['cpmp_target'].queryset = CapaianPemelajaranMataPelajaran.objects.all()
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()
            self.fields['level'].queryset = GradeLevel.objects.none()
            self.fields['cpmp_target'].queryset = CapaianPemelajaranMataPelajaran.objects.none()



        # 3. Logic: Teacher depends on Period
        # if period:
        #     self.fields['teacher'].queryset = Teacher.objects.filter(user=user).all()
        #     if user.is_staff:
        #         self.fields['teacher'].queryset = Teacher.objects.all()
        # else:
        #     self.fields['teacher'].queryset = Teacher.objects.none()
        if period:
            self.fields['teacher'].queryset = Teacher.objects.all()
        else:
            self.fields['teacher'].queryset = Teacher.objects.none()

        # 4. Logic: Subject depends on Teacher
        if teacher:
            # Using your existing filtering logic
            self.fields['subject'].queryset = Subject.objects.filter(course__teacher__id=teacher).distinct()
            if is_admin:
                self.fields['subject'].queryset = Subject.objects.all()
        else:
            self.fields['subject'].queryset = Subject.objects.none()

        if subject:
            # Using your existing filtering logic
            self.fields['course'].queryset = Course.objects.filter(teacher_id=teacher, academic_year_id=acayear, subject_id=subject)
            if is_admin:
                self.fields['course'].queryset = Course.objects.all()
        else:
            self.fields['course'].queryset = Course.objects.none()

        # if level:
        #     self.fields['course'].queryset = Course.objects.filter(teacher_id=teacher).distinct()
        # else:
        #     self.fields['course'].queryset = Course.objects.none()

        if course:
            self.fields['assignment_type'].label_from_instance = lambda obj: obj.name
            self.fields['assignment_type'].queryset = AssignmentType.objects.all()

        else:
            self.fields['assignment_type'].queryset = AssignmentType.objects.none()

        # --- HTMX Attributes ---
        # Update Academic Year to trigger Period update
        self.fields['academic_year'].widget.attrs.update({
            'id': 'acayear-select-ge',  # Vital for the listener
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-ge/',
            'hx-trigger': 'change',
            'hx-target': '#period-select-ge', # Updates Period normally
            'hx-swap': 'innerHTML',
        })

        # --- 2. PERIOD (Standard Chain) ---
        self.fields['period'].widget.attrs.update({
            'id': 'period-select-ge',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-teachers-ge/',
            'hx-trigger': 'change',
            'hx-target': '#teacher-select-ge',
            'hx-swap': 'innerHTML',
            'hx-include': '#period-select-ge' # Use ID selector for safety
        })

        self.fields['subject'].widget.attrs.update({
            'id': 'subject-select-ge',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-courses-ge/',
            'hx-trigger': 'change',
            'hx-target': '#course-select-ge',
            'hx-swap': 'innerHTML',
            'hx-include': '#acayear-select-ge, #subject-select-ge'
        })

        # --- 3. LEVEL (The Listener) ---
        # "I will update myself whenever Academic Year changes"
        self.fields['level'].widget.attrs.update({
            'id': 'level-select-ge',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-levels-ge/', # Separate View
            'hx-trigger': 'change from:#acayear-select-ge', # LISTEN to the Year field
            'hx-include': '#acayear-select-ge', # Send the Year data
            'hx-target': '#level-select-ge', # Update myself
            'hx-swap': 'innerHTML',
        })


        # --- 4. COURSE (Triggers Assignment Type) ---
        self.fields['course'].widget.attrs.update({
            'id': 'course-select-ge',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-assignment-types-ge/', # Separate View
            'hx-trigger': 'change',
            'hx-target': '#assignment-type-select-ge',
            'hx-swap': 'innerHTML',
            'hx-include': '#acayear-select-ge, #subject-select-ge'
            # hx-include is not strictly needed if we just need the course ID 
            # (htmx sends the trigger element's value by default)
        })

        self.fields['teacher'].widget.attrs.update({
            'id': 'teacher-select-ge',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-subjects-ge/',
            'hx-trigger': 'change',
            'hx-target': '#subject-select-ge',
            'hx-swap': 'innerHTML',
        })


        # --- 5. ASSIGNMENT TYPE ---
        self.fields['assignment_type'].widget.attrs.update({
            'id': 'assignment-type-select-ge',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-cpmp-ge/',
            'hx-trigger': 'change',
            'hx-target': '#cpmp-select-ge',
            'hx-swap': 'innerHTML',
            'hx-include': '#acayear-select-ge, #course-select-ge, #subject-select-ge',  # send both
        })

        self.fields['cpmp_target'].widget.attrs.update({
            'id': 'cpmp-select-ge',
            'class': 'custom-select mb-4',
            'hx-include': '#acayear-select-ge, #assignment-type-select-ge'
        })
        
        # Ensure Teacher/Subject IDs match your previous setup
        self.fields['teacher'].widget.attrs['id'] = 'teacher-select-ge'
        self.fields['subject'].widget.attrs['id'] = 'subject-select-ge'

        # old code
        # self.fields['academic_year'].widget.attrs.update({
        #     'class': 'custom-select mb-4',
        #     'hx-get': '/gradebook/get-period-ge/',
        #     'hx-trigger': 'change',
        #     'hx-target': '#period-select-ge', # Make sure this matches the ID below
        #     'hx-swap': 'innerHTML',
        # })

        # # Update Period to trigger Teacher update
        # self.fields['period'].widget.attrs.update({
        #     'id': 'period-select-ge', # Set ID for target
        #     'class': 'custom-select mb-4',
        #     'hx-get': '/gradebook/get-teachers-ge/',
        #     'hx-trigger': 'change',
        #     'hx-target': '#teacher-select-ge',
        #     'hx-swap': 'innerHTML',
        # })

        # # Set ID for Teacher field so it can be targeted
        # self.fields['teacher'].widget.attrs.update({
        #     'id': 'teacher-select-ge',
        #     'class': 'custom-select mb-4',
        #     'hx-get': '/gradebook/get-subjects-ge/',
        #     'hx-trigger': 'change',
        #     'hx-target': '#subject-select-ge',
        #     'hx-swap': 'innerHTML',
        # })

        # self.fields['subject'].widget.attrs.update({
        #     'id': 'subject-select-ge',
        #     'class': 'custom-select mb-4',
        #     'hx-get': '/gradebook/get-courses-ge/',
        #     'hx-trigger': 'change',
        #     'hx-target': '#course-select-ge',
        #     'hx-swap': 'innerHTML',
        # })

        # self.fields['course'].widget.attrs.update({
        #     'id': 'course-select-ge',
        #     'class': 'custom-select mb-4',
        #     'hx-get': '/gradebook/get_assignment_types/',
        #     'hx-trigger': 'change',
        #     'hx-target': '#assignment-type-select-ge',
        #     'hx-swap': 'innerHTML',
        # })

        # self.fields['course'].widget.attrs['id'] = 'course-select-ge'
        # self.fields['level'].widget.attrs['id'] = 'level-select-ge'
        



# class ReportCardComment(forms.ModelForm):
#     class Meta:
#         model = ReportcardGrade
#         fields = ["teacher_notes"]

# class TeacherForm(forms.ModelForm):
#     class Meta:
#         model = Teacher
#         fields = ['user']

# Absensi
# class AttendanceForm(forms.ModelForm):

#     def __init__(self, *args, **kwargs):
#         user = kwargs.pop('user', None)
#         super().__init__(*args, **kwargs)
    
#     current_teacher = ClassMember.student
#     # filtered_students = Teacher.objects.filter(current_teacher)
#     kelas_obj = Teacher.objects.filter(user_id=1)
#     # kelas_teacher = kelas_obj.alast.is_home_room
#     student = forms.ModelChoiceField(
#         queryset=kelas_obj,
#         required=False,  # Make it optional (so you can search by project only)
#     )



#     # jgn lupa yg diatas
#     class Meta:
#         model = StudentAttendance
#         fields = ["attendance_date", "student", "attendance_type", "notes"]
#         widgets = {
#             'attendance_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
#         }


class AttendanceForm(forms.ModelForm):


    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.all().select_related('registration_data')
        
        if user and hasattr(user, 'teacher'):
                # get current Teacher.user
            current_teacher = Teacher.objects.get(user=user)
                
                # filter Class table by current Teacher.user
                # (You only need the classes relevant to filtering students)
            teacher_classes = Class.objects.filter(teacher=current_teacher)
                
                # If the teacher has classes, filter the students
            if teacher_classes.exists():
                student_ids = ClassMember.objects.filter(
                    kelas__in=teacher_classes, 
                    is_active=True
                ).values_list('student_id', flat=True)
                    
                self.fields['student'].queryset = Student.objects.filter(id__in=student_ids)
        
        # ganti queryset
        # self.fields['student'].queryset = Student.objects.filter(id__in=student_ids)
        # if teacher_classes:
        #     self.fields['student'].queryset = Student.objects.filter(id__in=student_ids)
        # else:
        #     self.fields['student'].queryset = Student.objects.all()


            



    class Meta:
        model = StudentAttendance
        fields = ["attendance_date", "student", "attendance_type", "notes"]
        widgets = {
            'attendance_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control cally bg-base-100 border border-base-300 rounded-box'})
        }
        # labels = {
        #     'attendance_date': 'Tanggal Absensi',
        #     'student': 'Nama Murid',
        #     'attendance_type': 'Tipe Absensi',
        #     'notes': 'Catatan',
        # }

# Form Step 2
class AssignmentHeadForm(forms.ModelForm):
    class Meta:
        model = AssignmentHead
        fields = ['date', 'topic', 'max_score'] 
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'topic': forms.TextInput()
        }

        # labels = {
        #     'date': 'Tanggal',
        #     'topic': 'Topik',
        #     'max_score': 'Nilai Maksimal'
        # }



# Form Step 3 (Detail per Siswa)
class AssignmentDetailItemForm(forms.ModelForm):
    student_name = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'border-none outline-none focus:ring-0'})
    )

    student_nisn = forms.CharField(
        required=False,
        # widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
        widget=PlainTextWidget
    )

    class Meta:
        model = AssignmentDetail
        # YOU MUST INCLUDE 'student' HERE
        fields = ['student', 'score', 'is_active', 'na_reason', 'na_date']
        widgets = {
            'student': forms.HiddenInput(),
            'na_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
        }

    def __init__(self, *args, **kwargs):
        student_obj = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)


        # 1. SETUP STUDENT NAME (Keep your existing logic)
        student_obj = None
        if self.instance and hasattr(self.instance, 'student'):
            student_obj = self.instance.student
        elif self.initial.get('student'):
            from admission.models import Student
            try:
                student_obj = Student.objects.get(pk=self.initial['student'])
            except Student.DoesNotExist:
                pass
        
        if student_obj:
            self.fields['student_name'].initial = str(student_obj)
            
        # 2. DETERMINE IS_ACTIVE STATUS (The Fix)
        # Default to True (active) unless we find otherwise
        if self.is_bound:
            # CASE A: User clicked Save/Next. Look at POST data.
            # We construct the HTML name of the checkbox: "{prefix}-is_active"
            checkbox_name = f"{self.prefix}-is_active"
            
            # In HTML, an unchecked box sends NO data. A checked box sends data.
            # So, if the key exists in self.data, it is True. If missing, it is False.
            self.current_is_active = checkbox_name in self.data
        else:
            # CASE B: First page load. Look at Database/Initial.
            if self.instance and self.instance.pk:
                self.current_is_active = self.instance.is_active
            else:
                self.current_is_active = self.initial.get('is_active', True)
    


        # 3. Calculate the Name
        if student_obj:
            # Access the related Registration table
            # We use getattr in case the relationship is missing (prevents crash)
            reg_data = getattr(student_obj, 'registration_data', None)
            
            if reg_data:
                first = reg_data.first_name or ""
                middle = reg_data.middle_name or ""
                last = reg_data.last_name or ""
                
                # Logic: If middle name exists, add it with spaces
                full_name = f"{first} {middle} {last}".strip()
                
                # Assign to the readonly field
                self.fields['student_name'].initial = full_name
            self.fields['student_nisn'].initial = student_obj.nisn

    def clean(self):
        cleaned_data = super().clean()
        is_active = cleaned_data.get('is_active')
        na_reason = cleaned_data.get('na_reason')

            # Logic: If inactive (False) AND reason is empty, raise error
        if is_active is False and not na_reason:
            self.add_error('na_reason', "Reason is required when item is inactive.")

        if is_active:
            cleaned_data['na_reason'] = ""


        return cleaned_data
        

        

# Membuat FormSet Factory
class AssignmentDetailFormSet(BaseFormSet):

    class Meta:
        widgets={
            'score': forms.NumberInput(attrs={'class': 'form-control'}),
            'na_reason': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    def __init__(self, *args, max_score=None, is_active=True, form_kwargs_list=None, **kwargs):
        form_kwargs_list = kwargs.pop('form_kwargs_list', [])
        super().__init__(*args, **kwargs)
        self.max_score = max_score
        self.is_active = is_active
        if form_kwargs_list:
            self.form_kwargs_list = form_kwargs_list


        # THIS ONE BELOW IS OLD, UNCOMMENTED INCASE NEW ONE WORKS EVEN WORSE
        #
        #
        # for i, form_kwargs in enumerate(form_kwargs_list):
        #     if i < len(self.forms):
        #         self.forms[i].form_index = form_kwargs.get('form_index', i)
        #         # Add HTMX attributes
        #         self.forms[i].fields['na_reason'].widget.attrs.update({
        #             'hx-get': '/gradebook/toggle-na-reason/',
        #             'hx-target': f'#na_reason_td_{self.forms[i].form_index}',
        #             'hx-swap': 'innerHTML',
        #             'hx-include': f'[name="form-{self.forms[i].form_index}-na_reason"], [name="form-{self.forms[i].form_index}-is_active"]',
        #             'hx-trigger': 'change',
        #             'id': f'na_reason_input_{self.forms[i].form_index}',
        #             'class': 'form-control textarea textarea-bordered w-full min-w-24 focus:outline-0 transition-all focus:outline-offset-0'
        #         })
        #         self.forms[i].fields['is_active'].widget.attrs.update({
        #             'hx-get': '/gradebook/toggle-na-reason/',
        #             'hx-target': f'#na_reason_td_{self.forms[i].form_index}',
        #             'hx-swap': 'innerHTML',
        #             'hx-include': f'[name="form-{self.forms[i].form_index}-na_reason"], [name="form-{self.forms[i].form_index}-is_active"]',
        #             'hx-trigger': 'change',
        #             'id': f'is_active_{self.forms[i].form_index}'
        #         })

        for i, form_kwargs in enumerate(form_kwargs_list):
            if i < len(self.forms):
                idx = i

                self.forms[i].fields['is_active'].widget.attrs.update({
                    'hx-get': '/gradebook/toggle-na-reason/',
                    'hx-target': 'closest tr',  # Target the whole row
                    'hx-swap': 'outerHTML',  # Replace the whole row
                    'hx-trigger': 'change',
                    # 'closest tr' includes all inputs inside that row automatically
                    'hx-include': 'closest tr',
                })

    
    def clean(self):
        super().clean()
        if self.max_score is not None:
            for form in self.forms:
                if form.cleaned_data and form.cleaned_data.get('score') is not None:
                    if form.cleaned_data['score'] > self.max_score:
                        form.add_error('score', f"Score cannot exceed {self.max_score}.")

        if self.is_active is not True:
            for form in self.forms:
                if form.cleaned_data is not None:
                    form.cleaned_data['na_reason'] = ""

AssignmentDetailFormSet = formset_factory(AssignmentDetailItemForm, formset=AssignmentDetailFormSet, extra=0)


class StudentReportcardForm(forms.ModelForm):
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
        # label='Tahun Ajaran'
    )

    period = forms.ModelChoiceField(
        queryset=LearningPeriod.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'period-select'})
        # label='Periode Pembelajaran / Semester'
    )

    is_mid = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'level-select'})
        # label='Level Pembelajaran'
    )

    kelas = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'level-select'}),
        label='Class'
    )

    class Meta:
        model = StudentReportcard
        fields = ["academic_year", "period", "is_mid", "level"]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select select2'}), # Assuming you use select2
        }
        # labels = {
        #     'academic_year': 'Tahun Ajaran',
        #     'period': 'Periode Pembelajaran / Semester',
        #     'is_mid': 'Tengah Semester',
        #     'level': 'Level Pembelajaran'
        # }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # BIAR NGGAK ERROR PAS MAU LANJUT KE STEP BERIKUTNYA
        data = self.data
        initial = self.initial

        is_staff = user and (user.is_staff or user.is_superuser)

        acayear = data.get('0-academic_year') or initial.get('academic_year')
        level = data.get('0-level') or initial.get('level')
        period = data.get('0-period') or initial.get('period')

        if not is_staff and user:
            # homeroom teacher — lock to their class, hide the field
            kelas = Class.objects.filter(teacher__user=user).first()
            if kelas:
                self.fields['kelas'].initial = kelas.id
                self.fields['kelas'].widget = forms.HiddenInput()
                self.fields['kelas'].required = False

        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.filter(academic_year=acayear)
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()

        if period:
            self.fields['level'].queryset = GradeLevel.objects.all()
        else:
            self.fields['level'].queryset = GradeLevel.objects.none()
            
        self.fields['academic_year'].widget.attrs.update({
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-reportcard/',
            'hx-trigger': 'change',
            'hx-target': '#period-select',
            'hx-swap': 'innerHTML',
            'hx-include': '[name="1-period"]'
            })
        
        # self.fields['period'].widget.attrs.update({
        #         'class': 'custom-select mb-4',
        #         'id': 'period-select'
        #         })
        self.fields['period'].widget.attrs.update({
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-level-reportcard/',
            'hx-trigger': 'change',
            'hx-target': '#level-select',
            'hx-swap': 'innerHTML',
            'hx-include': '[name="1-level"]'
            })
        
        self.fields['level'].widget.attrs['id'] = 'level-select'

class CourseByTeacher(forms.ModelForm):
    # subject = forms.ModelChoiceField(
    #     queryset=Subject.objects.all(),
    #     required=True
    # )
    
    # course = forms.ModelChoiceField(
    #     queryset=Course.objects.filter(subject=subject),
    #     required=False
    # )
    
    class Meta:
        model = GradeEntry
        fields = ["subject", "course"]
        labels = {
            'course': 'Sub-level'
        }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        teacher_obj = None
        if user:
            teacher_obj = Teacher.objects.filter(user=user).first()

        data = self.data
        initial = self.initial
        
        # Get currently selected/initial subject ID
        # Using '1-' prefix for Wizard step 1
        subject_id = data.get('1-subject') or initial.get('subject')

        # Ambil data dari initial dictionary yang dikirim Wizard
        initial_score = self.initial.get('final_score')
        initial_grade = self.initial.get('final_grade')

        if initial_score is not None:
            # Set nilai ke widget secara langsung
            self.fields['final_score'].widget.attrs['value'] = initial_score

        if initial_grade:
            self.fields['final_grade'].initial = initial_grade

        if teacher_obj:
            # 1. Filter Subjects: Only subjects taught by this teacher
            subj_qs = Subject.objects.filter(course__teacher=teacher_obj).distinct()
            self.fields['subject'].queryset = subj_qs

            # Default Subject: If only 1 subject exists and no data is bound yet
            if not self.is_bound and subj_qs.count() == 1:
                self.initial['subject'] = subj_qs.first().id
                subject_id = self.initial['subject']

            # 2. Filter Courses: Only courses taught by this teacher for the chosen subject
            if subject_id:
                course_qs = Course.objects.filter(teacher=teacher_obj, subject_id=subject_id)
                self.fields['course'].queryset = course_qs
                
                # Default Course: If only 1 course exists for this subject
                if not self.is_bound and course_qs.count() == 1:
                    self.initial['course'] = course_qs.first().id
            else:
                self.fields['course'].queryset = Course.objects.none()
        else:
            # Fallback for admins or if no teacher profile is linked
            if subject_id:
                self.fields['course'].queryset = Course.objects.filter(subject_id=subject_id).distinct()
            else:
                self.fields['course'].queryset = Course.objects.none()

        self.fields['course'].required = False
        
        self.fields['subject'].widget.attrs.update({
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-courses/',
            'hx-trigger': 'change',
            'hx-target': '#course-select',
            'hx-swap': 'innerHTML',
            'hx-include': '[name="1-course"]'
        })
        self.fields['course'].widget.attrs.update({
            'class': 'custom-select mb-4',
            'id': 'course-select'
        })

    def clean(self):
        cleaned_data = super().clean()
        subject = cleaned_data.get('subject')
        course = cleaned_data.get('course')

        # Proteksi: Pastikan course yang dipilih memang milik subject tersebut
        if course and subject and course.subject != subject:
            raise forms.ValidationError("Invalid Course for the selected Subject.")
        return cleaned_data


class ReportCardGradeForm(forms.Form):  # plain Form, not ModelForm
    student_id = forms.IntegerField(widget=forms.HiddenInput())
    student_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True})
    )
    ht_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

ReportCardGradeFormset = formset_factory(ReportCardGradeForm, extra=0)


# class RequestLogForm(BaseReportForm, forms.Form):
#     subject_name = forms.CharField(
#         required=False,
#         widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext fw-bold'})
#     )
#
#     student_name = forms.CharField(
#         required=False,
#         widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext fw-bold'})
#     )
#
#
#     # This must be required=False, as you haven't entered a score yet
#     final_score = forms.DecimalField(required=False, max_digits=5, decimal_places=2, initial=0)
#
#     # This must be required=False, as you haven't entered a grade yet
#     final_grade = forms.ChoiceField(choices=FINAL_GRADE_CHOICES, required=False)
#
#     # Hidden field for the Subject ID: MUST NOT BE required=True
#     subject = forms.ModelChoiceField(queryset=Subject.objects.all(), required=False)
#
#     teacher_notes = forms.CharField(
#         widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Notes...'}),
#         required=False
#     )
#
#     def __init__(self, *args, subject_queryset=None, **kwargs):
#         object().__init__(*args, **kwargs)
#
#         # Apply a filtered queryset when provided (passed via formset form_kwargs)
#         if subject_queryset:
#             self.fields['subject'].queryset = subject_queryset
#         else:
#             self.fields['subject'].queryset = Subject.objects.all()
#
#         # UI tweaks
#         # Keep the subject value submitted: use readonly/display field for name
#         self.fields['subject'].widget.attrs.pop('disabled', None)
#         self.fields['subject'].widget.attrs['readonly'] = True
#         self.fields['subject'].widget.attrs['class'] = 'form-control bg-light'
#
#         self.fields['final_score'].widget.attrs.pop('disabled', None)
#         self.fields['final_score'].widget.attrs['readonly'] = True
#         self.fields['final_score'].widget.attrs['class'] = 'form-control bg-light'
#
#         self.fields['final_grade'].disabled = True
#         self.fields['final_grade'].widget.attrs['readonly'] = True
#         # self.fields['final_grade'].widget.attrs['class'] = 'form-control bg-light'
#
#         # Populate subject_name for display if initial data exists
#         if self.initial.get('subject'):
#             try:
#                 subj = Subject.objects.get(pk=self.initial['subject'])
#                 self.fields['subject_name'].initial = subj.subject_name
#             except Subject.DoesNotExist:
#                 pass
#
#         # Populate student_name for display if initial data exists
#         if self.initial.get('student_name'):
#             self.fields['student_name'].initial = self.initial['student_name']
#
#     class Meta:
#         model = ReportcardGrade
#         fields = ['student_name', 'subject', 'final_score', 'final_grade', 'teacher_notes']
#         widgets = {
#             'student_name': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
#             'subject': forms.HiddenInput(),
#             'final_score': forms.NumberInput(attrs={'class': 'form-control'}),
#             'final_grade': forms.Select(attrs={'class': 'form-select'}),
#             'teacher_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
#         }
#         exclude = ('reportcard',)


# Formset for ReportCardGradeForm
ReportCardGradeFormset = formset_factory(ReportCardGradeForm, extra=0)


class RequestLogForm(BaseReportForm, forms.Form):

    start_date = forms.DateField(
        required=False,
        label="Start Date",
        widget=forms.DateInput(attrs={"type": "hidden"}),
        initial=datetime.now
    )
    end_date = forms.DateField(required=False, label="End Date", widget=forms.DateInput({"type": "hidden"}), initial=datetime.now)

    academic_year = forms.ModelChoiceField(
        queryset = AcademicYear.objects.all(),
        required=False,
        widget=forms.RadioSelect(attrs={
            'class': 'form-control'
        })
    )

    period = forms.ModelChoiceField(
        queryset = LearningPeriod.objects.all(),
        required=False,
        widget=forms.RadioSelect(attrs={
            'class': 'form-control'
        })
    )

    is_mid = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_date"].initial = datetime.date
        self.fields["end_date"].initial = datetime.date

        data = self.data
        initial = self.initial

        # no wizard prefix — this is a plain GET form
        acayear = data.get('academic_year') or initial.get('academic_year')

        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.filter(
                academic_year_id=acayear,
                period_name__icontains='semester'
            )
        else:
            # show all semesters as fallback so period is never empty
            self.fields['period'].queryset = LearningPeriod.objects.filter(
                academic_year_id=acayear,
                period_name__icontains='semester'
            )


        # self.fields["start_date"].widget.is_hidden = True
        # self.fields['period'].queryset = LearningPeriod.objects.all()


        self.fields['academic_year'].widget.attrs.update({
            'id': 'acayear-select-ledger',  # Vital for the listener
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get_period_ledger/',
            'hx-trigger': 'change',
            'hx-target': '#period-select-ledger', # Updates Period normally
            'hx-swap': 'innerHTML',
        })

        self.fields['period'].widget.attrs.update({
            'id': 'period-select-ledger',
            'class': 'form-check-input mb-2',
        })


    def get_filters(self):
        academic_year = self.cleaned_data.get("academic_year")
        period = self.cleaned_data.get("period")
        is_mid = self.cleaned_data.get("is_mid")
        # return the filters to be used in the report
        # Note: the use of Q filters and kwargs filters
        filters = {}
        q_filters = []
        if not academic_year and not period:
            filters['id'] = -1 # Impossible ID, results in empty table
            return q_filters, filters
        
        if academic_year:
            filters["reportcard__academic_year"] = academic_year
            
        if period:
            filters["reportcard__period"] = period

        # For Booleans, usually we only filter if the checkbox is checked, 
        # or you can force the filter regardless:
        if is_mid is not None:
            filters["reportcard__is_mid"] = is_mid

        return q_filters, filters

    def get_start_date(self):
        return self.cleaned_data["start_date"]

    def get_end_date(self):
        return self.cleaned_data["end_date"]
    






# ============================================================================
# RUBRIC ENTRY (Student Behavior Form)
# ============================================================================

class RubricEntryForm(forms.ModelForm):
    """Step 0: Select academic year, period, teacher, and class"""
    
    teacher = forms.ModelChoiceField(
        queryset=Teacher.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
        # label='Nama Guru'
    )

    kelas = forms.ModelChoiceField(
        queryset=Course.objects.none(),  # starts empty, populated by HTMX
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
        label='Sub-level'
    )


        
    class Meta:
        model = ReportcardBehaviour
        fields = ['academic_year', 'period', 'level']
        # labels = {
        #     'academic_year': 'Tahun Ajaran',
        #     'period': 'Periode Pembelajaran / Semester',
        #     'level': 'Level Pembelajaran'
        # }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        data = self.data
        initial = self.initial

        is_admin = user and (user.is_staff or user.is_superuser)

        # Default Logic
        if user and not self.is_bound:
            teacher_obj = Teacher.objects.filter(user=user).first()
            if teacher_obj:
                self.initial['teacher'] = teacher_obj.id
                
            # curr_ay = AcademicYear.objects.order_by('-id').first()
            # if curr_ay:
            #     self.initial['academic_year'] = curr_ay.id
            #     curr_period = LearningPeriod.objects.filter(academic_year=curr_ay, period_name__icontains='semester').order_by('-id').first()
            #     if curr_period:
            #         self.initial['period'] = curr_period.id
        
        acayear = data.get('0-academic_year') or initial.get('academic_year')
        level = data.get('0-level') or initial.get('level')
        period = data.get('0-period') or initial.get('period')
        teacher = data.get('0-teacher') or initial.get('teacher')
        kelas = data.get('0-kelas') or initial.get('kelas')
        
        # Period depends on Academic Year
        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.filter(academic_year_id=acayear, period_name__icontains='semester')
            # if is_admin and not teacher_obj:
            if is_admin:
                self.fields['period'].queryset = LearningPeriod.objects.filter(period_name__icontains='semester').all()
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()

        # print(f"user: {user}, is_staff: {user.is_staff if user else 'NO USER'}")

        # Teacher depends on Period
        if period:
            if user.is_staff==True:
                self.fields['teacher'].queryset = Teacher.objects.all()
            elif user:
                self.fields['teacher'].queryset = Teacher.objects.filter(user=user)
            else:
                self.fields['teacher'].queryset = Teacher.objects.none()
        else:
            self.fields['teacher'].queryset = Teacher.objects.none()

        # Kelas depends on Teacher (FK relationship in admission.models.Class)
        if teacher:
            self.fields['kelas'].queryset = Course.objects.filter(
                teacher_id=teacher
            ).select_related('teacher')
        elif is_admin:
            self.fields['kelas'].queryset = Course.objects.all().select_related('teacher')
        else:
            self.fields['kelas'].queryset = Course.objects.none()

        # HTMX Attributes for dynamic cascading
        self.fields['academic_year'].widget.attrs.update({
            'id': 'rubric-acayear-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-ge/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-period-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['period'].widget.attrs.update({
            'id': 'rubric-period-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-teachers-ge/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-teacher-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['level'].widget.attrs.update({
            'id': 'rubric-level-select',
            'class': 'custom-select mb-4',
        })

        self.fields['teacher'].widget.attrs.update({
            'id': 'rubric-teacher-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-courses-assignment-avg/',
            'hx-trigger': 'change',
            'hx-target': '#assignment-avg-course-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['kelas'].widget.attrs.update({
            'id': 'rubric-kelas-select',
            'class': 'custom-select mb-4',
        })


# Form Step 1: Student List (reuse AssignmentDetailItemForm structure)
class StudentListItemForm(forms.ModelForm):
    student_name = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
    )

    student_nisn = forms.CharField(
        required=False,
        # widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
        widget=PlainTextWidget
    )
    
    is_graded = forms.BooleanField(required=False, disabled=True)
    
    class Meta:
        model = AssignmentDetail
        # YOU MUST INCLUDE 'student' HERE
        fields = ['student', 'score']
        widgets = {
            'student': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        student_obj = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)

        # 1. SETUP STUDENT NAME (Keep your existing logic)
        student_obj = None
        if self.instance and hasattr(self.instance, 'student'):
            student_obj = self.instance.student
        elif self.initial.get('student'):
            from admission.models import Student
            try:
                student_obj = Student.objects.get(pk=self.initial['student'])
            except Student.DoesNotExist:
                pass
        
        if student_obj:
            self.fields['student_name'].initial = str(student_obj)

        self.fields['is_graded'].initial = self.initial.get('is_graded', False)
            
        # 2. DETERMINE IS_ACTIVE STATUS (The Fix)
        # Default to True (active) unless we find otherwise
        if self.is_bound:
            # CASE A: User clicked Save/Next. Look at POST data.
            # We construct the HTML name of the checkbox: "{prefix}-is_active"
            checkbox_name = f"{self.prefix}-is_active"
            
            # In HTML, an unchecked box sends NO data. A checked box sends data.
            # So, if the key exists in self.data, it is True. If missing, it is False.
            self.current_is_active = checkbox_name in self.data
        else:
            # CASE B: First page load. Look at Database/Initial.
            if self.instance and self.instance.pk:
                self.current_is_active = self.instance.is_active
            else:
                self.current_is_active = self.initial.get('is_active', True)
    


        # 3. Calculate the Name
        if student_obj:
            # Access the related Registration table
            # We use getattr in case the relationship is missing (prevents crash)
            reg_data = getattr(student_obj, 'registration_data', None)
            
            if reg_data:
                first = reg_data.first_name or ""
                middle = reg_data.middle_name or ""
                last = reg_data.last_name or ""
                
                # Logic: If middle name exists, add it with spaces
                full_name = f"{first} {middle} {last}".strip()
                
                # Assign to the readonly field
                self.fields['student_name'].initial = full_name
            self.fields['student_nisn'].initial = student_obj.nisn

    def clean(self):
        cleaned_data = super().clean()
        is_active = cleaned_data.get('is_active')
        na_reason = cleaned_data.get('na_reason')

            # Logic: If inactive (False) AND reason is empty, raise error
        if is_active is False and not na_reason:
            self.add_error('na_reason', "Reason is required when item is inactive.")
            
        return cleaned_data


class StudentListForm(StudentListItemForm):
    """Uses AssignmentDetail model to track student rubric scores"""


    
    def __init__(self, *args, **kwargs):
        # Pop custom wizard kwargs
        kelas = kwargs.pop('kelas', None)
        form_kwargs_list = kwargs.pop('form_kwargs_list', None)
        # Call parent init with remaining kwargs
        super().__init__(*args, **kwargs)
        # kelas is now available if needed for additional logic


# Custom FormSet Base for StudentListForm (accepts wizard kwargs)
class StudentListFormSetBase(BaseFormSet):
    """Custom formset that accepts kelas and form_kwargs_list from RubricEntryWizard"""
    
    def __init__(self, *args, kelas=None, form_kwargs_list=None, **kwargs):
        # Extract custom kwargs before parent init
        kelas = kwargs.pop('kelas', kelas)
        form_kwargs_list = kwargs.pop('form_kwargs_list', form_kwargs_list)
        super().__init__(*args, **kwargs)
        
        # Store for reference
        self.kelas = kelas
        self.form_kwargs_list = form_kwargs_list or []
        
        # Pass form_index to each form if provided
        for i, form_kwargs in enumerate(self.form_kwargs_list):
            if i < len(self.forms):
                self.forms[i].form_index = form_kwargs.get('form_index', i)


# ============================================================================
# BEHAVIOR GRADING (Student Rubric/Indicator Scoring)
# ============================================================================

# class BehaviorGradingForm(forms.ModelForm):
#     """Form for grading individual rubric indicators (1-4 scale)"""
    
#     indicator_text = forms.CharField(
#         required=False,
#         widget=forms.TextInput(attrs={
#             'readonly': 'readonly',
#             'class': 'form-control-plaintext',
#             'style': 'font-weight: bold;'
#         })
#     )
    
#     class Meta:
#         model = StudentRubrics
#         fields = ['indicator', 'score']
#         widgets = {
#             'indicator': forms.HiddenInput(),
#             'score': forms.RadioSelect(attrs={'class': 'form-check-input'}),
#         }

#     def __init__(self, *args, **kwargs):
#         indicator_obj = kwargs.pop('indicator', None)
#         super().__init__(*args, **kwargs)
        
#         # Set initial indicator text for display
#         if indicator_obj:
#             self.fields['indicator_text'].initial = indicator_obj.indicator_text
#         elif self.initial.get('indicator'):
#             try:
#                 indicator = RubricIndicator.objects.get(pk=self.initial['indicator'])
#                 self.fields['indicator_text'].initial = indicator.indicator_text
#             except RubricIndicator.DoesNotExist:
#                 pass


# class BehaviorGradingFormSet(BaseFormSet):
#     """Formset for grading multiple indicators at once"""
#     pass


# # FormSet for Behavior Grading
# BehaviorGradingFormSet = formset_factory(BehaviorGradingForm, formset=BehaviorGradingFormSet, extra=0)


# EXTRA REPORT FORM
EXTRA_GRADE_TYPE_CHOICES = [
    ("EK", "Ekstrakurikuler"),
    ("PD", "Pengembangan Diri"),
    ("P", "Prestasi"),
]
class ExtraGradeItemForm(forms.ModelForm):
    teacher = forms.ModelChoiceField(
        queryset=Teacher.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'})
    )

    kelas = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
        label='Extracurricular Class'
    )

    act_subj = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'})
    )



    class Meta:
        model = ReportcardBehaviour
        fields = ['academic_year', 'period', 'level']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)


        data = self.data
        initial = self.initial

        is_admin = user and (user.is_staff or user.is_superuser)

        if user and not self.is_bound and not is_admin:
            teacher_obj = Teacher.objects.filter(user=user).first()
            if teacher_obj:
                self.initial['teacher'] = teacher_obj.id

                # Filter and potentially default Subject
                teacher_subjects = Subject.objects.filter(course__teacher=teacher_obj).distinct()
                if teacher_subjects.count() == 1:
                    self.initial['subject'] = teacher_subjects.first().id

        acayear = data.get('0-academic_year') or initial.get('academic_year')
        level = data.get('0-level') or initial.get('level')
        period = data.get('0-period') or initial.get('period')
        teacher = data.get('0-teacher') or initial.get('teacher')
        kelas = data.get('0-kelas') or initial.get('kelas')
        act_subj = data.get('0-act_subj') or initial.get('act_subj')

        # Period depends on Academic Year
        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.filter(academic_year_id=acayear,
                                                                           period_name__icontains='semester')
            if user.is_staff:
                self.fields['period'].queryset = LearningPeriod.objects.all()
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()

        # Teacher depends on Period
        if period:
            self.fields['teacher'].queryset = Teacher.objects.all()
        else:
            self.fields['teacher'].queryset = Teacher.objects.none()

        # Kelas depends on Teacher (FK relationship in admission.models.Class)
        if teacher:
            self.fields['kelas'].queryset = Course.objects.all()
        else:
            self.fields['kelas'].queryset = Course.objects.none()

        # HTMX Attributes for dynamic cascading
        self.fields['academic_year'].widget.attrs.update({
            'id': 'rubric-acayear-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-extra/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-period-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['period'].widget.attrs.update({
            'id': 'rubric-period-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-teachers-extra/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-teacher-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['level'].widget.attrs.update({
            'id': 'rubric-level-select',
            'class': 'custom-select mb-4',
        })

        self.fields['teacher'].widget.attrs.update({
            'id': 'rubric-teacher-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-kelas-extra/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-kelas-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['kelas'].widget.attrs.update({
            'id': 'rubric-kelas-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-act-subj/',
            'hx-trigger': 'change',
            'hx-target': '#extra-type-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['act_subj'].widget.attrs.update({
            'id': 'extra-type-select',
            'class': 'custom-select mb-4',
            'hx-include': '#rubric-kelas-select',
        })

class ExtraGradeForm(forms.Form):
    student_id = forms.IntegerField(widget=forms.HiddenInput())
    student_nisn = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': True,
        })
    )
    student_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': True,
        })
    )
    extra_score = forms.IntegerField(
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control score-input'})
    )
    extra_description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    extra_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 1})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)


ExtraGradeFormSet = formset_factory(ExtraGradeForm, extra=0)


class ExtraGradeListForm(ExtraGradeItemForm):
    student_name = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
    )

    student_nisn = forms.CharField(
        required=False,
        # widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
        widget=PlainTextWidget
    )

    is_graded = forms.BooleanField(required=False, disabled=True)

    class Meta:
        model = AssignmentDetail
        # YOU MUST INCLUDE 'student' HERE
        fields = ['student', 'score']
        widgets = {
            'student': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        student_obj = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)

        # 1. SETUP STUDENT NAME (Keep your existing logic)
        student_obj = None
        if self.instance and hasattr(self.instance, 'student'):
            student_obj = self.instance.student
        elif self.initial.get('student'):
            from admission.models import Student
            try:
                student_obj = Student.objects.get(pk=self.initial['student'])
            except Student.DoesNotExist:
                pass
        
        if student_obj:
            self.fields['student_name'].initial = str(student_obj)
            
        # 2. DETERMINE IS_ACTIVE STATUS (The Fix)
        # Default to True (active) unless we find otherwise
        if self.is_bound:
            # CASE A: User clicked Save/Next. Look at POST data.
            # We construct the HTML name of the checkbox: "{prefix}-is_active"
            checkbox_name = f"{self.prefix}-is_active"
            
            # In HTML, an unchecked box sends NO data. A checked box sends data.
            # So, if the key exists in self.data, it is True. If missing, it is False.
            self.current_is_active = checkbox_name in self.data
        else:
            # CASE B: First page load. Look at Database/Initial.
            if self.instance and self.instance.pk:
                self.current_is_active = self.instance.is_active
            else:
                self.current_is_active = self.initial.get('is_active', True)
    


        # 3. Calculate the Name
        if student_obj:
            # Access the related Registration table
            # We use getattr in case the relationship is missing (prevents crash)
            reg_data = getattr(student_obj, 'registration_data', None)
            
            if reg_data:
                first = reg_data.first_name or ""
                middle = reg_data.middle_name or ""
                last = reg_data.last_name or ""
                
                # Logic: If middle name exists, add it with spaces
                full_name = f"{first} {middle} {last}".strip()
                
                # Assign to the readonly field
                self.fields['student_name'].initial = full_name
            self.fields['student_nisn'].initial = student_obj.nisn

    def clean(self):
        cleaned_data = super().clean()
        is_active = cleaned_data.get('is_active')
        na_reason = cleaned_data.get('na_reason')

            # Logic: If inactive (False) AND reason is empty, raise error
        if is_active is False and not na_reason:
            self.add_error('na_reason', "Reason is required when item is inactive.")
            
        return cleaned_data


class StudentListExtraGForm(ExtraGradeItemForm):
    """Uses AssignmentDetail model to track student rubric scores"""
    
    def __init__(self, *args, **kwargs):
        # Pop custom wizard kwargs
        kelas = kwargs.pop('kelas', None)
        form_kwargs_list = kwargs.pop('form_kwargs_list', None)
        # Call parent init with remaining kwargs
        super().__init__(*args, **kwargs)
        # kelas is now available if needed for additional logic


# Custom FormSet Base for StudentListForm (accepts wizard kwargs)
class StudentListExtraGFormSetBase(BaseFormSet):
    """Custom formset that accepts kelas and form_kwargs_list from RubricEntryWizard"""
    
    def __init__(self, *args, kelas=None, form_kwargs_list=None, **kwargs):
        # Extract custom kwargs before parent init
        kelas = kwargs.pop('kelas', kelas)
        form_kwargs_list = kwargs.pop('form_kwargs_list', form_kwargs_list)
        super().__init__(*args, **kwargs)
        
        # Store for reference
        self.kelas = kelas
        self.form_kwargs_list = form_kwargs_list or []
        
        # Pass form_index to each form if provided
        for i, form_kwargs in enumerate(self.form_kwargs_list):
            if i < len(self.forms):
                self.forms[i].form_index = form_kwargs.get('form_index', i)




class StudentsExamGradesEntry(forms.ModelForm):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'})
    )

    is_mid = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput()
    )


    class Meta:
        model = ReportcardBehaviour
        fields = ['academic_year', 'period', 'level']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        data = self.data
        initial = self.initial

        acayear = data.get('0-academic_year') or initial.get('academic_year')
        level = data.get('0-level') or initial.get('level')
        period = data.get('0-period') or initial.get('period')
        subject = data.get('0-subject') or initial.get('subject')
        is_mid = data.get('0-is_mid') or initial.get('is_mid')

        # Period depends on Academic Year
        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.filter(academic_year_id=acayear)
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()

        # Teacher depends on Period
        if period:
            self.fields['teacher'].queryset = Teacher.objects.all()
        else:
            self.fields['teacher'].queryset = Teacher.objects.none()

        # Kelas depends on Teacher (FK relationship in admission.models.Class)
        # if teacher:
        #     self.fields['kelas'].queryset = Teacher.objects.all()
        # else:
        #     self.fields['kelas'].queryset = Teacher.objects.none()

        # HTMX Attributes for dynamic cascading
        self.fields['academic_year'].widget.attrs.update({
            'id': 'rubric-acayear-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-ge/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-period-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['period'].widget.attrs.update({
            'id': 'rubric-period-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-teachers-ge/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-teacher-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['level'].widget.attrs.update({
            'id': 'rubric-level-select',
            'class': 'custom-select mb-4',
        })

        self.fields['teacher'].widget.attrs.update({
            'id': 'rubric-teacher-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-kelas-ge/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-kelas-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['kelas'].widget.attrs.update({
            'id': 'rubric-kelas-select',
            'class': 'custom-select mb-4',
        })

        self.fields['extra_type'].widget.attrs.update({
            'id': 'extra-type-select',
            'class': 'custom-select mb-4',
        })



class GradesSelectionForm(forms.ModelForm):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'})
    )

    is_mid = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = StudentReportcard
        fields = ['academic_year', 'period', 'level']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        data = self.data
        initial = self.initial

        acayear = data.get('0-academic_year') or initial.get('academic_year')
        level = data.get('0-level') or initial.get('level')
        period = data.get('0-period') or initial.get('period')
        subject = data.get('0-subject') or initial.get('subject')
        is_mid = data.get('0-is_mid') or initial.get('is_mid')

        # Period depends on Academic Year
        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.filter(academic_year_id=acayear)
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()

        # Level can be all, but perhaps filter if needed
        self.fields['level'].queryset = GradeLevel.objects.all()

        # HTMX Attributes for dynamic cascading
        self.fields['academic_year'].widget.attrs.update({
            'id': 'grades-acayear-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-grades/',
            'hx-trigger': 'change',
            'hx-target': '#grades-period-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['period'].widget.attrs.update({
            'id': 'grades-period-select',
            'class': 'custom-select mb-4',
        })

        self.fields['level'].widget.attrs.update({
            'class': 'custom-select mb-4',
        })

        self.fields['subject'].widget.attrs.update({
            'class': 'custom-select mb-4',
        })

        self.fields['is_mid'].widget.attrs.update({
            'class': 'form-check-input',
        })

EXTRA_INFO_TYPE_CHOICES = [
    ("PD", "Pengembangan Diri"),
    ("P", "Prestasi"),
]

class ExtraInfoItemForm(forms.ModelForm):
    teacher = forms.ModelChoiceField(
        queryset=Teacher.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'})
    )

    kelas = forms.ModelChoiceField(
        queryset=Class.objects.none(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
        label='Class'
    )

    extra_type = forms.ChoiceField(
        choices=EXTRA_INFO_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'})
    )

    class Meta:
        model = ReportcardBehaviour
        fields = ['academic_year', 'period', 'level']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        data = self.data
        initial = self.initial

        acayear = data.get('0-academic_year') or initial.get('academic_year')
        level = data.get('0-level') or initial.get('level')
        period = data.get('0-period') or initial.get('period')
        teacher = data.get('0-teacher') or initial.get('teacher')
        kelas = data.get('0-kelas') or initial.get('kelas')
        ext_type = data.get('0-extra_type') or initial.get('extra_type')

        # Period depends on Academic Year
        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.filter(academic_year_id=acayear)
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()
# a
        # Teacher depends on Period
        if period:
            self.fields['teacher'].queryset = Teacher.objects.all()
        else:
            self.fields['teacher'].queryset = Teacher.objects.none()

        # Kelas depends on Teacher (FK relationship in admission.models.Class)
        if teacher:
            self.fields['kelas'].queryset = Class.objects.all()
        else:
            self.fields['kelas'].queryset = Class.objects.none()

        # HTMX Attributes for dynamic cascading
        self.fields['academic_year'].widget.attrs.update({
            'id': 'rubric-acayear-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-ge/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-period-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['period'].widget.attrs.update({
            'id': 'rubric-period-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-teachers-ge/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-teacher-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['level'].widget.attrs.update({
            'id': 'rubric-level-select',
            'class': 'custom-select mb-4',
        })

        self.fields['teacher'].widget.attrs.update({
            'id': 'rubric-teacher-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-kelas-ge/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-kelas-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['kelas'].widget.attrs.update({
            'id': 'rubric-kelas-select',
            'class': 'custom-select mb-4',
        })

        self.fields['extra_type'].widget.attrs.update({
            'id': 'extra-type-select',
            'class': 'custom-select mb-4',
        })


class ExtraInfoListForm(ExtraInfoItemForm):
    student_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
    )

    student_nisn = forms.CharField(
        required=False,
        # widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
        widget=PlainTextWidget
    )

    is_graded = forms.BooleanField(required=False, disabled=True)

    class Meta:
        model = AssignmentDetail
        # YOU MUST INCLUDE 'student' HERE
        fields = ['student', 'score']
        widgets = {
            'student': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        student_obj = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)

        # 1. SETUP STUDENT NAME (Keep your existing logic)
        student_obj = None
        if self.instance and hasattr(self.instance, 'student'):
            student_obj = self.instance.student
        elif self.initial.get('student'):
            from admission.models import Student
            try:
                student_obj = Student.objects.get(pk=self.initial['student'])
            except Student.DoesNotExist:
                pass

        if student_obj:
            self.fields['student_name'].initial = str(student_obj)

        # 2. DETERMINE IS_ACTIVE STATUS (The Fix)
        # Default to True (active) unless we find otherwise
        if self.is_bound:
            # CASE A: User clicked Save/Next. Look at POST data.
            # We construct the HTML name of the checkbox: "{prefix}-is_active"
            checkbox_name = f"{self.prefix}-is_active"

            # In HTML, an unchecked box sends NO data. A checked box sends data.
            # So, if the key exists in self.data, it is True. If missing, it is False.
            self.current_is_active = checkbox_name in self.data
        else:
            # CASE B: First page load. Look at Database/Initial.
            if self.instance and self.instance.pk:
                self.current_is_active = self.instance.is_active
            else:
                self.current_is_active = self.initial.get('is_active', True)

        # 3. Calculate the Name
        if student_obj:
            # Access the related Registration table
            # We use getattr in case the relationship is missing (prevents crash)
            reg_data = getattr(student_obj, 'registration_data', None)

            if reg_data:
                first = reg_data.first_name or ""
                middle = reg_data.middle_name or ""
                last = reg_data.last_name or ""

                # Logic: If middle name exists, add it with spaces
                full_name = f"{first} {middle} {last}".strip()

                # Assign to the readonly field
                self.fields['student_name'].initial = full_name
            self.fields['student_nisn'].initial = student_obj.nisn

    def clean(self):
        cleaned_data = super().clean()
        is_active = cleaned_data.get('is_active')
        na_reason = cleaned_data.get('na_reason')

        # Logic: If inactive (False) AND reason is empty, raise error
        if is_active is False and not na_reason:
            self.add_error('na_reason', "Reason is required when item is inactive.")

        return cleaned_data




class TotalGradesForm(forms.ModelForm):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'})
    )

    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'})
    )

    period = forms.ModelChoiceField(
        queryset=LearningPeriod.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'custom-select mb-4'})
    )

    is_mid = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = ReportcardBehaviour
        fields = ['subject', 'academic_year', 'period']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)


        data = self.data
        initial = self.initial

        if user and not self.is_bound:
            teacher_obj = Teacher.objects.filter(user=user).first()
            if teacher_obj:
                self.initial['teacher'] = teacher_obj.id

                # Filter and potentially default Subject
                teacher_subjects = Subject.objects.filter(course__teacher=teacher_obj).distinct()
                if teacher_subjects.count() == 1:
                    self.initial['subject'] = teacher_subjects.first().id

            # Default to the most recent Academic Year and Period
            curr_ay = AcademicYear.objects.order_by('-id').first()
            if curr_ay:
                self.initial['academic_year'] = curr_ay.id
                curr_period = LearningPeriod.objects.filter(academic_year=curr_ay).order_by('-id').first()
                if curr_period:
                    self.initial['period'] = curr_period.id


        subject = data.get('0-subject') or initial.get('subject')
        acayear = data.get('0-academic_year') or initial.get('academic_year')
        period = data.get('0-period') or initial.get('period')
        is_mid = data.get('0-is_mid') or initial.get('is_mid')

        self.fields['subject'].queryset = Subject.objects.all()

        # Period depends on Academic Year
        if subject:
            self.fields['academic_year'].queryset = AcademicYear.objects.all()
        else:
            self.fields['academic_year'].queryset = AcademicYear.objects.all()


        # Teacher depends on Period
        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.all()
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()




        # HTMX Attributes for dynamic cascading
        self.fields['subject'].widget.attrs.update({
            'id': 'rubric-subject-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-academic_year-tgrade/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-teacher-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['academic_year'].widget.attrs.update({
            'id': 'rubric-acayear-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-tgrade/',
            'hx-trigger': 'change',
            'hx-target': '#rubric-period-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['period'].widget.attrs.update({
            'id': 'rubric-period-select',
            'class': 'custom-select mb-4',
        })

        self.fields['is_mid'].widget.attrs.update({
            'id': 'rubric-level-select',
            'class': 'form-check-input',
        })

class TotalGradesTestList(TotalGradesForm):
    student_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
    )

    student_nisn = forms.CharField(
        required=False,
        # widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
        widget=PlainTextWidget
    )

    is_graded = forms.BooleanField(required=False, disabled=True)

    class Meta:
        model = AssignmentDetail
        # YOU MUST INCLUDE 'student' HERE
        fields = ['student', 'score']
        widgets = {
            'student': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        student_obj = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)

        # 1. SETUP STUDENT NAME (Keep your existing logic)
        student_obj = None
        if self.instance and hasattr(self.instance, 'student'):
            student_obj = self.instance.student
        elif self.initial.get('student'):
            from admission.models import Student
            try:
                student_obj = Student.objects.get(pk=self.initial['student'])
            except Student.DoesNotExist:
                pass

        if student_obj:
            self.fields['student_name'].initial = str(student_obj)

        # 2. DETERMINE IS_ACTIVE STATUS (The Fix)
        # Default to True (active) unless we find otherwise
        if self.is_bound:
            # CASE A: User clicked Save/Next. Look at POST data.
            # We construct the HTML name of the checkbox: "{prefix}-is_active"
            checkbox_name = f"{self.prefix}-is_active"

            # In HTML, an unchecked box sends NO data. A checked box sends data.
            # So, if the key exists in self.data, it is True. If missing, it is False.
            self.current_is_active = checkbox_name in self.data
        else:
            # CASE B: First page load. Look at Database/Initial.
            if self.instance and self.instance.pk:
                self.current_is_active = self.instance.is_active
            else:
                self.current_is_active = self.initial.get('is_active', True)

        # 3. Calculate the Name
        if student_obj:
            # Access the related Registration table
            # We use getattr in case the relationship is missing (prevents crash)
            reg_data = getattr(student_obj, 'registration_data', None)

            if reg_data:
                first = reg_data.first_name or ""
                middle = reg_data.middle_name or ""
                last = reg_data.last_name or ""

                # Logic: If middle name exists, add it with spaces
                full_name = f"{first} {middle} {last}".strip()

                # Assign to the readonly field
                self.fields['student_name'].initial = full_name
            self.fields['student_nisn'].initial = student_obj.nisn

    def clean(self):
        cleaned_data = super().clean()
        is_active = cleaned_data.get('is_active')
        na_reason = cleaned_data.get('na_reason')

        # Logic: If inactive (False) AND reason is empty, raise error
        if is_active is False and not na_reason:
            self.add_error('na_reason', "Reason is required when item is inactive.")

        return cleaned_data

# FormSet for Total Grading Step 1
TotalGradesFormSet = formset_factory(TotalGradesTestList, formset=StudentListFormSetBase, extra=0)


class AssignmentAvgForm(forms.Form):
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
    )
    # ADDED HTMX HERE: Level must trigger the Subject dropdown!
    level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.all(),
        widget=forms.Select(attrs={
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-subjects-assignment-avg/',
            'hx-trigger': 'change',
            'hx-target': '#assignment-avg-subject-select',
            'hx-swap': 'innerHTML',
        }),
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(), # Default to none until teacher/level is known
        widget=forms.Select(attrs={
            'id': 'assignment-avg-subject-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-courses-assignment-avg/',
            'hx-trigger': 'change',
            'hx-target': '#assignment-avg-course-select',
            'hx-swap': 'innerHTML',
        }),
    )
    period = forms.ModelChoiceField(
        queryset=LearningPeriod.objects.all(),
        label="Period",
        widget=forms.Select(attrs={
            'hx-get': '/gradebook/get-period-assignment-avg/',
            'class': 'custom-select mb-4'
        })
    )
    is_mid = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def __init__(self, *args, **kwargs):
        # 1. Grab the user from the view
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        data = self.data
        initial = self.initial

        acayear_id = data.get('0-academic_year') or initial.get('academic_year')
        level_id = data.get('0-level') or initial.get('level')
        subject_id = data.get('0-subject') or initial.get('subject')

        # # 2. Figure out who the logged-in teacher is
        # teacher_obj = None
        # if user:
        #     teacher_obj = Teacher.objects.filter(user=user).first()

        # 3. Filter SUBJECTS: Must belong to the teacher (and potentially the level)
        if level_id:
            self.fields['subject'].queryset = Subject.objects.all()
        else:
            self.fields['subject'].queryset = Subject.objects.none()

        # if subject_id:
        #     self.fields['period'].queryset = LearningPeriod.objects.none()
        # else:
        #     self.fields['period'].queryset = LearningPeriod.objects.all()

        # 4. Filter KELAS: Must belong to the teacher AND the selected subject
        if subject_id:
            # *NOTE: If this line gives an error, it's because Django doesn't know
            # how your Class model links to your Course model.
            self.fields['period'].queryset = LearningPeriod.objects.filter(Q(period_name__icontains='semester'))
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()


        self.fields['subject'].widget.attrs.update({
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-assignment-avg/',
        })

        self.fields['academic_year'].widget.attrs.update({
            'id': 'assignment-avg-acayear-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-assignment-avg/',
            'hx-trigger': 'change',
            'hx-target': '#assignment-avg-period-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['period'].widget.attrs.update({
            'id': 'assignment-avg-period-select',
            'class': 'custom-select mb-4',
        })


PDRPT_CHOICES = [
    (1, "Belum Melakukan"),
    (2, "Sudah Melakukan"),
    (3, "Biasa Melakukan"),
]

# Easy to update — just add/remove fields here
PERSONAL_DEV_FIELDS = {
    'Care': ['care1', 'care2', 'care3'],
    'Respect': ['respect1', 'respect2', 'respect3', 'respect4'],
    'Responsibility': ['responsibility1', 'responsibility2', 'responsibility3', 'responsibility4'],
    'Excellence': ['excellence1', 'excellence2', 'excellence3', 'excellence4'],
}

class PersonalDevSelectForm(forms.Form):
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
        label='Academic Year'
    )
    period = forms.ModelChoiceField(
        queryset=LearningPeriod.objects.none(),
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
        label='Period'
    )
    level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.none(),
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
        label='Grade Level'
    )
    # kelas = forms.ModelChoiceField(
    #     queryset=Class.objects.none(),
    #     widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
    #     label='Class'
    # )
    is_mid = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Mid Semester?"
    )
    student = forms.ModelChoiceField(
        queryset=StudentReportcard.objects.none(),
        widget=forms.Select(attrs={'class': 'custom-select mb-4'}),
        label='Student',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = self.data
        initial = self.initial

        acayear = data.get('0-academic_year') or initial.get('academic_year')
        period = data.get('0-period') or initial.get('period')
        level = data.get('0-level') or initial.get('level')
        kelas = data.get('0-kelas') or initial.get('kelas')
        is_mid = data.get('0-is_mid') or initial.get('is_mid')

        # self.fields['student'].label_from_instance = lambda obj: (
        #     f"{obj.student.registration_data.first_name} "
        #     f"{obj.student.registration_data.last_name} "
        #     f"({obj.academic_year} / {obj.period.period_name})"
        # )

        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.filter(
                academic_year_id=acayear,
                period_name__icontains='semester'
            )
            self.fields['level'].queryset = GradeLevel.objects.all()
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()
            self.fields['level'].queryset = GradeLevel.objects.none()

        if level:
            self.fields['student'].queryset = StudentReportcard.objects.all()
            # self.fields['student'].label_from_instance = lambda obj: obj.student.registration_data.first_name
        else:
            self.fields['student'].queryset = StudentReportcard.objects.none()

        # if kelas:
        #     self.fields['student'].queryset = StudentReportcard.objects.filter(
        #         student__classmember__kelas_id=kelas,
        #         student__classmember__is_active=True,
        #     ).select_related('student__registration_data').distinct()
        # else:
        #     self.fields['student'].queryset = StudentReportcard.objects.none()

        # HTMX cascade
        self.fields['academic_year'].widget.attrs.update({
            'id': 'pd-acayear-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-period-pd/',
            'hx-trigger': 'change',
            'hx-target': '#pd-period-select',
            'hx-swap': 'innerHTML',
        })

        self.fields['period'].widget.attrs.update({
            'id': 'pd-period-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-levels-pd/',
            'hx-trigger': 'change',
            'hx-target': '#pd-level-select',
            'hx-swap': 'innerHTML',
            'hx-include': '#pd-acayear-select',  # add this
        })

        self.fields['level'].widget.attrs.update({
            'id': 'pd-level-select',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-student-pd/',
            'hx-trigger': 'change',
            'hx-target': '#pd-student-select',
            'hx-swap': 'innerHTML',
            'hx-include': '#pd-acayear-select',
        })
        # self.fields['kelas'].widget.attrs.update({
        #     'id': 'pd-kelas-select',
        #     'hx-get': '/gradebook/get-student-pd/',
        #     'hx-trigger': 'change',
        #     'hx-target': '#pd-student-select',
        #     'hx-swap': 'innerHTML',
        #     'hx-include': '#pd-acayear-select',
        # })

        self.fields['is_mid'].widget.attrs.update({
            'id': 'pd-is-mid',
            'class': 'form-control',
            'hx-get': '/gradebook/get-student-pd/',
            'hx-trigger': 'change',
            'hx-target': '#pd-student-select',
            'hx-swap': 'innerHTML',
            'hx-include': '#pd-acayear-select, #pd-kelas-select, #pd-is-mid, #pd-period-select',   # include itself
        })

        self.fields['student'].widget.attrs.update({
            'id': 'pd-student-select',
            'class': 'custom-select mb-4',
        })


class PersonalDevGradeForm(forms.ModelForm):
    class Meta:
        model = ReportcardPersonalDev
        # exclude the FK — handled in done()
        exclude = ['reporcard']
        widgets = {
            # RadioSelect for all choice fields — easy to change per field if needed
            field: forms.RadioSelect(attrs={'class': 'radio radio-primary'})
            for field in [
                'care1', 'care2', 'care3',
                'respect1', 'respect2', 'respect3', 'respect4',
                'responsibility1', 'responsibility2', 'responsibility3', 'responsibility4',
                'excellence1', 'excellence2', 'excellence3', 'excellence4',
            ]
        }


    def __init__(self, *args, **kwargs):
        existing_instance = kwargs.pop('existing_instance', None)
        super().__init__(*args, **kwargs)


        self.fields['care1'].label = 'Menyapa orang lain (teman, guru, dan staff sekolah) dengan sopan'
        self.fields['care2'].label = 'Menunjukkan sikap rendah hati (tidak pamer / sombong)'
        self.fields['care3'].label = 'Memiliki inisiatif untuk membantu orang lain'

        self.fields['respect1'].label = 'Menghormati orang lain (teman, guru, karyawan dan tamu sekolah)'
        self.fields['respect2'].label = 'Bersedia mendengarkan pendapat orang lain'
        self.fields['respect3'].label = 'Menggunakan kata - kata yang positif saat berinteraksi sosial'
        self.fields['respect4'].label = 'Memperlakukan orang lain dengan baik'

        self.fields['responsibility1'].label = 'Inisiatif mengerjakan tugas sekolah secara mandiri'
        self.fields['responsibility2'].label = 'Mampu bekerja sama dalam kelompok'
        self.fields['responsibility3'].label = 'Kooperatif dalam menjalankan tugas dari guru'
        self.fields['responsibility4'].label = 'Mandiri mengatur waktu belajar secara mandiri'

        self.fields['excellence1'].label = 'Melakukan perencanaan capaian target secara bertahap'
        self.fields['excellence2'].label = 'Melaksanaan tindakan sesuai perencanaan yang telah dibuat'
        self.fields['excellence3'].label = 'Menunjukkan perubahan sikap / perilaku dalam kegiatan sekolah'
        self.fields['excellence4'].label = 'Terlibat aktif dalam segala kegiatan sekolah'



        # If an existing record is found, pre-fill
        if existing_instance:
            for field_name in self.fields:
                self.initial[field_name] = getattr(existing_instance, field_name)
                self.fields[field_name].widget.attrs.update({
                    'class': 'radio radio-primary'
                })


