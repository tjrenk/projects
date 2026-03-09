from django.db import models
from django.contrib.auth.models import User


# Create your models here.    


class AbstractPerson(models.Model):
    GENDER_CHOICES = {"M": "Male", "F": "Female"}
    first_name = models.CharField(max_length=20)
    middle_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    place_of_birth = models.CharField(max_length=25)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, blank=True, choices=GENDER_CHOICES)
    class Meta:
        abstract = True

class Religion(models.Model):
    religion_name = models.CharField(max_length=20)
    def __str__(self):
        return self.religion_name

class Registration(AbstractPerson):
    CONTACT_PREFS = {"W": "Whatsapp", "P": "Phone", "E": "Email"}
    LAST_EDU = {"S3": "PhD", "S2": "Graduate", "S1": "Undergraduate", "Dipl": "Diploma", "SHS": "SMA", "JHS": "SMP", "OTH": "Other"}
    form_no = models.CharField(max_length=20, unique=True)
    nisn = models.CharField(max_length=20, unique=True, blank=True, null=True)
    prev_school = models.CharField(max_length=50, blank=True, null=True)
    prev_nis = models.CharField(max_length=20, blank=True, null=True)
    birth_order = models.CharField(max_length=1, blank=True, null=True)
    religion = models.ForeignKey(Religion, null=True, on_delete=models.CASCADE)
    church_name = models.CharField(max_length=30, blank=True, null=True)
    current_address = models.CharField(max_length=50, blank=True, null=True)
    current_district = models.CharField(max_length=50, blank=True, null=True)
    current_region = models.CharField(max_length=50, blank=True, null=True)
    current_city = models.CharField(max_length=50, blank=True, null=True)
    current_province = models.CharField(max_length=50, blank=True, null=True)
    contact_whatsapp = models.CharField(max_length=20, blank=True, null=True)
    contact_mobile = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.CharField(max_length=20, blank=True, null=True)
    contact_preference = models.CharField(max_length=1, blank=True, null=True, choices=CONTACT_PREFS)
    mother_name = models.CharField(max_length=20, blank=True, null=True)
    mother_nik = models.CharField(max_length=20, blank=True, null=True)
    mother_religion = models.ForeignKey(Religion, null=True, on_delete=models.CASCADE, related_name="mother_religion")
    mother_education = models.CharField(max_length=20, blank=True, choices=LAST_EDU)
    mother_occupation = models.CharField(max_length=20, blank=True, null=True)
    mother_address_same2applicant = models.BooleanField(default=True)
    mother_address = models.CharField(max_length=50, blank=True, null=True)
    mother_district = models.CharField(max_length=50, blank=True, null=True)
    mother_region = models.CharField(max_length=50, blank=True, null=True)
    mother_city = models.CharField(max_length=50, blank=True, null=True)
    mother_province = models.CharField(max_length=50, blank=True, null=True)
    mother_phone = models.CharField(max_length=20, blank=True, null=True)
    mother_mobile = models.CharField(max_length=20, blank=True, null=True)
    mother_whatsapp = models.CharField(max_length=20, blank=True, null=True)
    mother_email = models.CharField(max_length=20, blank=True, null=True)
    father_name = models.CharField(max_length=20, blank=True, null=True)
    father_nik = models.CharField(max_length=20, blank=True, null=True)
    father_religion = models.ForeignKey(Religion, null=True, on_delete=models.CASCADE, related_name="father_religion")
    father_education = models.CharField(max_length=20, blank=True, choices=LAST_EDU)
    father_occupation = models.CharField(max_length=20, blank=True, null=True)
    father_address_same2applicant = models.BooleanField(default=True)
    father_address = models.CharField(max_length=50, blank=True, null=True)
    father_district = models.CharField(max_length=50, blank=True, null=True)
    father_region = models.CharField(max_length=50, blank=True, null=True)
    father_city = models.CharField(max_length=50, blank=True, null=True)
    father_province = models.CharField(max_length=50, blank=True, null=True)
    father_phone = models.CharField(max_length=20, blank=True, null=True)
    father_mobile = models.CharField(max_length=20, blank=True, null=True)
    father_whatsapp = models.CharField(max_length=20, blank=True, null=True)
    father_email = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.form_no} ({self.first_name})" 

class AcademicYear(models.Model):
    year = models.CharField(max_length=4)
    begin_date = models.DateField()
    end_date = models.DateField()
    def __str__(self):
        return f"{self.year}"

class LearningPeriod(models.Model):
    academic_year = (models.ForeignKey(AcademicYear, on_delete=models.CASCADE))
    period_name = models.CharField(max_length=15)
    date_start = models.DateField()
    date_end = models.DateField()
    def __str__(self):
        return f"{self.academic_year} / {self.period_name}"

class Teacher(AbstractPerson):
    join_date = (models.DateField())
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

class Student(models.Model):
    registration_data = models.OneToOneField(Registration, on_delete=models.CASCADE)
    id_number = models.CharField(max_length=15, unique=True)
    nisn = models.CharField(max_length=15, default="000000000000000", unique=True)
    is_active = models.BooleanField(default=True)
    na_date = models.DateField(null=True, blank=True)
    na_reason = models.CharField(max_length=100, blank=True, null=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['registration_data', 'nisn', 'is_active'],
                                    name='unique_student_data'),
        ]
    def __str__(self):
        return f"{self.id_number}"


class AbstractClass(models.Model):
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=6)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete = models.CASCADE)
    class Meta:
        abstract = True

class Class(AbstractClass):
    is_home_class = models.BooleanField(default=False)
    def __str__(self):
        return self.name

class ClassMember(models.Model):
    kelas = models.ForeignKey(Class, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    na_date = models.DateField(null=True, blank=True)
    na_reason = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['kelas', 'student', 'is_active'],
                                    name='unique_class_members'),
        ]

    def __str__(self):
        return f"{self.student}"

class SchoolData(models.Model):
    school_name = models.CharField(max_length=100, unique=True)
    address1 = models.CharField(max_length=100)
    address2 = models.CharField(max_length=100)
    district1 = models.CharField(max_length=100)
    district2 = models.CharField(max_length=100)
    city_name = models.CharField(max_length=50)
    province = models.CharField(max_length=50)

    def __str__(self):
        return self.school_name

class SchoolLevel(models.Model):
    level_name = models.CharField(max_length=25, unique=True)
    short_name = models.CharField(max_length=4, unique=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "School Levels"
        verbose_name = "School Level"

    def __str__(self):
        return self.level_name

class GradeLevel(models.Model):
    school_level = models.ForeignKey(SchoolLevel, on_delete=models.CASCADE)
    grade_name = models.CharField(max_length=25, unique=True)
    short_name = models.CharField(max_length=4, unique=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Grade Levels"
        verbose_name = "Grade Level"

    def __str__(self):
        return self.grade_name

class HeadMaster(models.Model):
    school = models.ForeignKey(SchoolData, on_delete=models.CASCADE)
    level = models.ForeignKey(SchoolLevel, default=1, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "level", "full_name"],
                                    name="unique_head_masters")
        ]

    def __str__(self):
        return f"{self.full_name}: {self.school} ({self.level})"