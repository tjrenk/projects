from django.db import models
from datetime import datetime, date
from admission.models import AcademicYear, AbstractClass, Student, SchoolLevel, GradeLevel, Teacher, LearningPeriod
from simple_history.models import HistoricalRecords
# from account.models import User

# Create your models here.
GRADE_CHOICES = [
    ("A", "A"),
    ("B", "B"),
    ("C", "C"),
    ("D", "D"),
    ("E", "E"),
]
class Subject(models.Model):
    subject_name = models.CharField(max_length=35, unique=True)
    short_name = models.CharField(max_length=5, blank=True, null=True)
    def __str__(self):
        return self.subject_name

class AssignmentType(models.Model):
    name = models.CharField(max_length=25, unique=True)
    short_name = models.CharField(max_length=10)
    def __str__(self):
        return self.short_name

class Weighting(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    assignment = models.ForeignKey(AssignmentType, on_delete=models.CASCADE)
    weight = models.DecimalField(max_digits=2, decimal_places=2, default=0.0)

class Course(AbstractClass):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    def __str__(self):
        return self.short_name

class CourseMember(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    na_date = models.DateField(null=True, blank=True)
    na_reason = models.CharField(max_length=100, blank=True, null=True)

class PassingGrade(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE)
    passing_grade = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['academic_year', 'subject', 'level'],
                                    name='unique_passing_grades'),
        ]

class GradeEntry(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    period = models.ForeignKey(LearningPeriod, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE, default="--")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    assignment_type = models.ForeignKey(AssignmentType, on_delete=models.CASCADE)
    assignment_date = models.DateField(auto_now_add=True)
    assignment_topic = models.CharField(max_length=100, default="to be fill later.")
    # set table to readonly by disabling all save/delete methode

    #def save(self, *args, **kwargs):
    #    pass

    #def delete(self, *args, **kwargs):
    #    pass

    #def __delete__(self, instance):
    #    pass

class AssignmentHead(models.Model):
    assignment = models.ForeignKey(AssignmentType, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    topic = models.TextField(null=True, blank=True)
    max_score = models.IntegerField(default=100)

class AssignmentDetail(models.Model):
    assignment_head = models.ForeignKey(AssignmentHead, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    na_date = models.DateField(null=True, blank=True)
    na_reason = models.CharField(max_length=100, blank=True, null=True)

class Rubric(models.Model):
    RUBRIC_CHOICES = [("Spiritual", "Spiritual Behaviour"), ("Social", "Social Behaviour")]
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=RUBRIC_CHOICES)
    description = models.TextField(null=True, blank=True)
    index = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Rubrics"
        verbose_name = "Rubric"

    def __str__(self):
        return self.description

class RubricIndicator(models.Model):
    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE)
    indicator_text = models.TextField(null=True, blank=True, unique=True)
    index = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Rubric Indicators"
        verbose_name = "Rubric indicator"

    def __str__(self):
        return self.indicator_text

class StudentReportcard(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    period = models.ForeignKey(LearningPeriod, on_delete=models.CASCADE)
    is_mid = models.BooleanField(default=False)
    level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE, related_name="students_level_reportcard")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

class ReportcardGrade(models.Model):
    reportcard = models.ForeignKey(StudentReportcard, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    final_score = models.IntegerField(default=0)
    final_grade = models.CharField(max_length=1, choices=GRADE_CHOICES)
    teacher_notes = models.TextField(null=True, blank=True)

class StudentAttendance(models.Model):
    ATTD_CHOICES = [("S", "Sick"), ("P", "Permit"), ("A", "Absent"), ("L", "Late")]
    attendance_date = models.DateField(null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    attendance_type = models.CharField(max_length=1, choices=ATTD_CHOICES)
    notes = models.TextField(null=True, blank=True)

class ReportcardNotes(models.Model):
    reportcard = models.ForeignKey(StudentReportcard, on_delete=models.CASCADE)
    spiritual_char_statement = models.TextField(null=True, blank=True)
    spiritual_char_notes = models.TextField(null=True, blank=True)
    social_statement = models.TextField(null=True, blank=True)
    social_char_notes = models.TextField(null=True, blank=True)
    social_notes = models.TextField(null=True, blank=True)
    homeroom_notes = models.TextField(null=True, blank=True)

class StudentRubrics(models.Model):
    SCORE_CHOICES = [(1,"1"), (2,"2"), (3,"3"), (4,"4")]
    reportcard = models.ForeignKey(StudentReportcard, on_delete=models.CASCADE)
    indicator = models.ForeignKey(RubricIndicator, on_delete=models.CASCADE)
    score = models.IntegerField(default=0, choices=SCORE_CHOICES)
