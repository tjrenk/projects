from django.shortcuts import get_object_or_404
from django import forms
from datetime import datetime
from slick_reporting.forms import BaseReportForm
from django.forms import modelform_factory, formset_factory, modelformset_factory, BaseFormSet
from .models import GradeEntry, AssignmentHead, AssignmentDetail, StudentAttendance, ReportcardGrade, StudentReportcard, Subject, Course, LearningPeriod, AcademicYear, AssignmentType
from admission.models import Class, ClassMember, GradeLevel, Teacher, AbstractClass, Student, SchoolLevel
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
    class Meta:
        model = GradeEntry
        fields = ["level", "academic_year", "period", "teacher", "subject", "course", "assignment_type"]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. FIX: Must check for the wizard prefix '0-'
        data = self.data
        initial = self.initial
        
        acayear = data.get('0-academic_year') or initial.get('academic_year')
        level = data.get('0-level') or initial.get('level')
        period = data.get('0-period') or initial.get('period')
        teacher = data.get('0-teacher') or initial.get('teacher')
        subject = data.get('0-subject') or initial.get('subject')
        course = data.get('0-course') or initial.get('course')
        assignment_type = data.get('0-assignment_type') or initial.get('assignment_type')
        # 2. Logic: Period depends on Academic Year


        if acayear:
            self.fields['period'].queryset = LearningPeriod.objects.filter(academic_year_id=acayear)
            self.fields['level'].queryset = GradeLevel.objects.all()
        else:
            self.fields['period'].queryset = LearningPeriod.objects.none()
            self.fields['level'].queryset = GradeLevel.objects.none()

        

        # 3. Logic: Teacher depends on Period
        if period:
            self.fields['teacher'].queryset = Teacher.objects.all()
        else:
            self.fields['teacher'].queryset = Teacher.objects.none()

        # 4. Logic: Subject depends on Teacher
        if teacher:
            # Using your existing filtering logic
            self.fields['subject'].queryset = Subject.objects.filter(course__teacher__id=teacher).distinct()
        else:
            self.fields['subject'].queryset = Subject.objects.none()

        if subject:
            # Using your existing filtering logic
            self.fields['course'].queryset = Course.objects.filter(teacher_id=teacher).distinct()
        else:
            self.fields['course'].queryset = Course.objects.none()

        if course:
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

        # ... (Teacher and Subject logic remains the same) ...

        # --- 4. COURSE (Triggers Assignment Type) ---
        self.fields['course'].widget.attrs.update({
            'id': 'course-select-ge',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-assignment-types-ge/', # Separate View
            'hx-trigger': 'change',
            'hx-target': '#assignment-type-select-ge',
            'hx-swap': 'innerHTML',
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

        self.fields['subject'].widget.attrs.update({
            'id': 'subject-select-ge',
            'class': 'custom-select mb-4',
            'hx-get': '/gradebook/get-courses-ge/',
            'hx-trigger': 'change',
            'hx-target': '#course-select-ge',
            'hx-swap': 'innerHTML',
        })

        # --- 5. ASSIGNMENT TYPE ---
        self.fields['assignment_type'].widget.attrs.update({
            'id': 'assignment-type-select-ge',
            'class': 'custom-select mb-4',
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
        



class ReportCardComment(forms.ModelForm):
    class Meta:
        model = ReportcardGrade
        fields = ["teacher_notes"]

        

class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['user']


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
        self.fields['student'].queryset = Student.objects.all()
        
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
            'attendance_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        }

# Form Step 2
class AssignmentHeadForm(forms.ModelForm):
    class Meta:
        model = AssignmentHead
        fields = ['date', 'topic', 'max_score'] 
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        }
        # Note: course dan assignment type diambil dari step 1, jadi tidak perlu di-field lagi

# Form Step 3 (Detail per Siswa)
class AssignmentDetailItemForm(forms.ModelForm):
    student_name = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
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
        

        

# Membuat FormSet Factory
class AssignmentDetailFormSet(BaseFormSet):

    class Meta:
        widgets={
            'score': forms.NumberInput(attrs={'class': 'form-control'}),
            'na_reason': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    def __init__(self, *args, max_score=None, form_kwargs_list=None, **kwargs):
        form_kwargs_list = kwargs.pop('form_kwargs_list', [])
        super().__init__(*args, **kwargs)
        self.max_score = max_score
        if form_kwargs_list:
            self.form_kwargs_list = form_kwargs_list

        for i, form_kwargs in enumerate(form_kwargs_list):
            if i < len(self.forms):
                self.forms[i].form_index = form_kwargs.get('form_index', i)
                # Add HTMX attributes
                self.forms[i].fields['na_reason'].widget.attrs.update({
                    'hx-get': '/gradebook/toggle-na-reason/',
                    'hx-target': f'#na_reason_td_{self.forms[i].form_index}',
                    'hx-swap': 'innerHTML',
                    'hx-include': f'[name="form-{self.forms[i].form_index}-na_reason"], [name="form-{self.forms[i].form_index}-is_active"]',
                    'hx-trigger': 'change',
                    'id': f'na_reason_input_{self.forms[i].form_index}',
                    'class': 'form-control textarea textarea-bordered w-full min-w-24 focus:outline-0 transition-all focus:outline-offset-0'
                })
                self.forms[i].fields['is_active'].widget.attrs.update({
                    'hx-get': '/gradebook/toggle-na-reason/',
                    'hx-target': f'#na_reason_td_{self.forms[i].form_index}',
                    'hx-swap': 'innerHTML',
                    'hx-include': f'[name="form-{self.forms[i].form_index}-na_reason"], [name="form-{self.forms[i].form_index}-is_active"]',
                    'hx-trigger': 'change',
                    'id': f'is_active_{self.forms[i].form_index}'
                })
    
    def clean(self):
        super().clean()
        if self.max_score is not None:
            for form in self.forms:
                if form.cleaned_data and form.cleaned_data.get('score') is not None:
                    if form.cleaned_data['score'] > self.max_score:
                        form.add_error('score', f"Score cannot exceed {self.max_score}.")

AssignmentDetailFormSet = formset_factory(AssignmentDetailItemForm, formset=AssignmentDetailFormSet, extra=0)


class StudentReportcardForm(forms.ModelForm):
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    period = forms.ModelChoiceField(
        queryset=LearningPeriod.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'period-select'})
    )

    is_mid = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'level-select'})
    )

    class Meta:
        model = StudentReportcard
        fields = ["academic_year", "period", "is_mid", "level"]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select select2'}), # Assuming you use select2
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # BIAR NGGAK ERROR PAS MAU LANJUT KE STEP BERIKUTNYA
        data = self.data
        initial = self.initial
        acayear = data.get('0-academic_year') or initial.get('academic_year')
        level = data.get('0-level') or initial.get('level')
        period = data.get('0-period') or initial.get('period')
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
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = self.data
        initial = self.initial
        
        # data.get must use the wizard prefix '1-', whatever that means
        # kalo nggak ntar nggak bisa ke langkah 3
        course = data.get('1-course') or initial.get('course')
        subject = data.get('1-subject') or initial.get('subject')
        if subject:
            self.fields['course'].queryset = Course.objects.filter(subject_id=subject)
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


class ReportCardGradeForm(forms.ModelForm):
    # Dummy field for display purposes only
    subject_name = forms.CharField(
        required=False,
        # widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext fw-bold'})
        widget=PlainTextWidget
    )

    student_name = forms.CharField(
        required=False,
        # widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext fw-bold'})
        widget=PlainTextWidget
    )
    

    # This must be required=False, as you haven't entered a score yet
    final_score = forms.DecimalField(required=False, max_digits=5, decimal_places=2, initial=0) 
    
    # This must be required=False, as you haven't entered a grade yet
    final_grade = forms.ChoiceField(choices=FINAL_GRADE_CHOICES, required=False) 
    
    # Hidden field for the Subject ID: MUST NOT BE required=True
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), required=False)

    teacher_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Notes...'}),
        required=False
    )

    def __init__(self, *args, subject_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply a filtered queryset when provided (passed via formset form_kwargs)
        if subject_queryset:
            self.fields['subject'].queryset = subject_queryset
        else:
            self.fields['subject'].queryset = Subject.objects.all()

        # UI tweaks
        # Keep the subject value submitted: use readonly/display field for name
        self.fields['subject'].widget.attrs.pop('disabled', None)
        self.fields['subject'].widget.attrs['readonly'] = True
        self.fields['subject'].widget.attrs['class'] = 'form-control bg-light'

        self.fields['final_score'].widget.attrs.pop('disabled', None)
        self.fields['final_score'].widget.attrs['readonly'] = True
        self.fields['final_score'].widget.attrs['class'] = 'form-control bg-light'

        self.fields['final_grade'].disabled = True
        self.fields['final_grade'].widget.attrs['readonly'] = True
        # self.fields['final_grade'].widget.attrs['class'] = 'form-control bg-light'

        # Populate subject_name for display if initial data exists
        if self.initial.get('subject'):
            try:
                subj = Subject.objects.get(pk=self.initial['subject'])
                self.fields['subject_name'].initial = subj.subject_name
            except Subject.DoesNotExist:
                pass

        # Populate student_name for display if initial data exists
        if self.initial.get('student_name'):
            self.fields['student_name'].initial = self.initial['student_name']

    class Meta:
        model = ReportcardGrade
        fields = ['student_name', 'subject', 'final_score', 'final_grade', 'teacher_notes']
        widgets = {
            'student_name': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
            'subject': forms.HiddenInput(),
            'final_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'final_grade': forms.Select(attrs={'class': 'form-select'}),
            'teacher_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
        }
        exclude = ('reportcard',)
        

ReportCardGradeFormset = formset_factory(ReportCardGradeForm, extra=0)
# ReportCardGradeFormset = modelformset_factory(
#     ReportcardGrade,  # Use the Model
#     form=ReportCardGradeForm, # Use your custom form
#     extra=0
# )

class ReportCardFilterForm(BaseReportForm):
    subject_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext fw-bold'})
    )

    student_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext fw-bold'})
    )
    

    # This must be required=False, as you haven't entered a score yet
    final_score = forms.DecimalField(required=False, max_digits=5, decimal_places=2, initial=0) 
    
    # This must be required=False, as you haven't entered a grade yet
    final_grade = forms.ChoiceField(choices=FINAL_GRADE_CHOICES, required=False) 
    
    # Hidden field for the Subject ID: MUST NOT BE required=True
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), required=False)

    teacher_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Notes...'}),
        required=False
    )

    def __init__(self, *args, subject_queryset=None, **kwargs):
        object().__init__(*args, **kwargs)

        # Apply a filtered queryset when provided (passed via formset form_kwargs)
        if subject_queryset:
            self.fields['subject'].queryset = subject_queryset
        else:
            self.fields['subject'].queryset = Subject.objects.all()

        # UI tweaks
        # Keep the subject value submitted: use readonly/display field for name
        self.fields['subject'].widget.attrs.pop('disabled', None)
        self.fields['subject'].widget.attrs['readonly'] = True
        self.fields['subject'].widget.attrs['class'] = 'form-control bg-light'

        self.fields['final_score'].widget.attrs.pop('disabled', None)
        self.fields['final_score'].widget.attrs['readonly'] = True
        self.fields['final_score'].widget.attrs['class'] = 'form-control bg-light'

        self.fields['final_grade'].disabled = True
        self.fields['final_grade'].widget.attrs['readonly'] = True
        # self.fields['final_grade'].widget.attrs['class'] = 'form-control bg-light'

        # Populate subject_name for display if initial data exists
        if self.initial.get('subject'):
            try:
                subj = Subject.objects.get(pk=self.initial['subject'])
                self.fields['subject_name'].initial = subj.subject_name
            except Subject.DoesNotExist:
                pass

        # Populate student_name for display if initial data exists
        if self.initial.get('student_name'):
            self.fields['student_name'].initial = self.initial['student_name']

    class Meta:
        model = ReportcardGrade
        fields = ['student_name', 'subject', 'final_score', 'final_grade', 'teacher_notes']
        widgets = {
            'student_name': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
            'subject': forms.HiddenInput(),
            'final_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'final_grade': forms.Select(attrs={'class': 'form-select'}),
            'teacher_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
        }
        exclude = ('reportcard',)

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
        widget=forms.Select(attrs={
            'class': 'form-control plaintext',
            'hx-get': 'load_periods/',
            'hx-target': '#period-container',  # Target a stable DIV, not the input
            'hx-swap': 'outerHTML',            # Swap the INSIDE of the div
            'hx-trigger': 'change'
        })
    )

    period = forms.ModelChoiceField(
        queryset = LearningPeriod.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'hx-swap': 'outerHTML',
            'id': 'id_period'             # Must match hx-target above
        })
    )

    is_mid = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput()
    )



    def __init__(self, *args, **kwargs):
        # super(RequestLogForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
    #     # provide initial values and ay needed customization
        self.fields["start_date"].initial = datetime.date
        self.fields["end_date"].initial = datetime.date

        

        # self.fields["start_date"].widget.is_hidden = True



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