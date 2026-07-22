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
EXTRA_CHOICES = [
    ("EK", "Ekstrakurikuler"),
    ("PD", "Pengembangan Diri"),
    ("P", "Prestasi"),
]

PDRPT_CHOICES = [
    (1, "Belum Melakukan"),
    (2, "Sudah Melakukan"),
    (3, "Biasa Melakukan"),
]

ASSIGNMENT_CAT_CHOICES = [
    ("WR", "WRITTEN"),
    ("PR", "PROJECT"),
    ("OB", "OBSERVATION"),
    ("OR", "ORAL")
]

class Subject(models.Model):
    subject_name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=5, blank=True, null=True)
    is_activity = models.BooleanField(default=False)
    def __str__(self):
        return self.subject_name

class AssignmentType(models.Model):
    name = models.CharField(max_length=25, unique=True)
    short_name = models.CharField(max_length=10)
    def __str__(self):
        return self.short_name

class Weighting(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    period = models.ForeignKey(LearningPeriod, on_delete=models.CASCADE)
    level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    assignment = models.ForeignKey(AssignmentType, on_delete=models.CASCADE)
    is_mid = models.BooleanField(default=False)
    weight = models.DecimalField(max_digits=2, decimal_places=2, default=0.0)

class Course(AbstractClass):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    is_activity = models.BooleanField(default=False)
    def __str__(self):
        return self.short_name

class CourseMember(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    na_date = models.DateField(null=True, blank=True)
    na_reason = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.student.__str__()

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
    level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    assignment_type = models.ForeignKey(AssignmentType, on_delete=models.CASCADE)
    assignment_category = models.CharField(max_length=10, choices=ASSIGNMENT_CAT_CHOICES)
    assignment_date = models.DateField(auto_now_add=True)
    assignment_topic = models.CharField(max_length=100, default="to be fill later.")
    # set table to readonly by disabling all save/delete methode

    #def save(self, *args, **kwargs):
    #    pass

    #def delete(self, *args, **kwargs):
    #    pass

    #def __delete__(self, instance):
    #    pass

class CapaianPemelajaranLulusan(models.Model):
    text = models.TextField(null=True, blank=True)

class CapaianPemelajaranMataPelajaran(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    cpl_root = models.ForeignKey(CapaianPemelajaranLulusan, on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)

class AssignmentHead(models.Model):
    assignment = models.ForeignKey(AssignmentType, on_delete=models.CASCADE)
    category = models.CharField(max_length=2, choices=ASSIGNMENT_CAT_CHOICES, default='WR')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    cpmp_target = models.ManyToManyField(CapaianPemelajaranMataPelajaran, related_name='assignments_tp', null=True)
    date = models.DateField(null=True)
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
#    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
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
    ht_comment = models.TextField(null=True, blank=True)

class ReportcardGrade(models.Model):
    reportcard = models.ForeignKey(StudentReportcard, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    final_score = models.IntegerField(default=0)
    final_grade = models.CharField(max_length=1, choices=GRADE_CHOICES)
    teacher_notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.reportcard.student}"

class StudentAttendance(models.Model):
    ATTD_CHOICES = [("S", "Sick"), ("P", "Permit"), ("A", "Absent")]
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

# class StudentRubrics(models.Model):
#     SCORE_CHOICES = [(1,"1"), (2,"2"), (3,"3"), (4,"4")]
#     reportcard = models.ForeignKey(StudentReportcard, on_delete=models.CASCADE)
#     indicator = models.ForeignKey(RubricIndicator, on_delete=models.CASCADE)
#     score = models.IntegerField(default=0, choices=SCORE_CHOICES)

class ReportcardBehaviour(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    period = models.ForeignKey(LearningPeriod, on_delete=models.CASCADE)
    is_mid = models.BooleanField(default=False)
    level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE, related_name="students_level_reportcard_behaviour")

class StudentBehaviourReport(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    behaviour = models.ForeignKey(ReportcardBehaviour, on_delete=models.CASCADE)
    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    grade = models.CharField(max_length=1, choices=GRADE_CHOICES)
    description = models.TextField(null=True, blank=True)

    def rendered_sentence(self):
        """Convenience method: render the linked template with this entry's data."""
        return self.student.render(self)

class StudentReportExtra(models.Model):
    reportcard = models.ForeignKey(StudentReportcard, on_delete=models.CASCADE)
    extra_type = models.CharField(max_length=2, choices=EXTRA_CHOICES)
    extra_description = models.TextField(null=True, blank=True)
    extra_score = models.IntegerField(default=0)
    extra_notes = models.TextField(null=True, blank=True)

class ReportcardRubricTemplate(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE)
    lookup_grade = models.CharField(max_length=1, choices=GRADE_CHOICES)
    text = models.TextField(null=True, blank=True)

    def render(self, data_entry):
        """Fill this template's pattern using a DataEntry instance's fields."""
        return self.text



class ReportcardPersonalDev(models.Model):
    reporcard = models.ForeignKey(StudentReportcard, on_delete=models.CASCADE)
    care1 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    care2 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    care3 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    respect1 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    respect2 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    respect3 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    respect4 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    responsibility1 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    responsibility2 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    responsibility3 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    responsibility4 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    excellence1 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    excellence2 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    excellence3 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
    excellence4 = models.IntegerField(default=0, choices=PDRPT_CHOICES)
