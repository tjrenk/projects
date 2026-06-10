from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from gradebook.models import Subject, GradeEntry, AssignmentHead, CourseMember, AssignmentDetail, ReportcardGrade, StudentBehaviourReport, ReportcardRubricTemplate, StudentReportExtra

from django.db.models.functions import Replace
from django.db.models import Value
from django.db.models import ExpressionWrapper, F, TextField, CharField

def new_subject(sender, instance, created, **kwargs):
    if created:
        print(f"Subject baru disimpan: {instance.subject_name} ({instance.short_name})")

def make_shortname(sender, instance, *args, **kwargs):
    if not instance.short_name:
        instance.short_name = instance.subject_name.replace(" ","")[:3].upper()

def new_grade_entry(sender, instance, created, **kwargs):
    if created:
        new_assignmenth_data = AssignmentHead(
            assignment_id = instance.assignment_type_id,
            course_id = instance.course_id,
            date = instance.assignment_date,
            topic = instance.assignment_topic
        )
        new_assignmenth_data.save()
        id_headnya = new_assignmenth_data.pk

        assign_head = AssignmentHead.objects.get(pk=id_headnya)
        course = assign_head.course
        students_in_course = CourseMember.objects.filter(
            course=course,
            is_active=True  # Usually, you only want to enroll active students
        )
        new_assignment_details = [
            AssignmentDetail(
                assignment_head=assign_head,
                student=member.student,
                is_active=member.is_active,
                na_date=member.na_date,
                na_reason=member.na_reason
            )
            for member in students_in_course
        ]
        assign_head = AssignmentHead.objects.get(pk=id_headnya)
        course = assign_head.course

        students_in_course = CourseMember.objects.filter(
            course=course,
            is_active=True  # Usually, you only want to enroll active students
        )
        print(students_in_course)
        new_assignment_details = [
            AssignmentDetail(
                assignment_head=assign_head,
                student=member.student,
                is_active=member.is_active,
                na_date=member.na_date,
                na_reason=member.na_reason
            )
            for member in students_in_course
        ]

        AssignmentDetail.objects.bulk_create(
            new_assignment_details,
            ignore_conflicts=True
        )

        #delete entry form record just saved
        idnya = instance.id
        print(f"idnya: {idnya}")
        try:
            record=GradeEntry.objects.get(pk=idnya)
            record.delete()
            print (f"Record for {idnya} is deleted")
        except GradeEntry.DoesNotExist:
            print (f"GradeEntry for {idnya} does not exist")

def set_final_grade(sender, instance, **kwargs):
    if not instance.final_grade:
        if (instance.final_score > 92) and (instance.final_score < 101):
            instance.final_grade = "A"
        elif (instance.final_score > 85) and (instance.final_score < 93):
            instance.final_grade = "B"
        elif (instance.final_score > 81) and (instance.final_score < 86):
            instance.final_grade = "C"
        elif (instance.final_score > 69) and (instance.final_score < 82):
            instance.final_grade = "D"
        else:
            instance.final_grade = "E"

# pemetaan grading untuk nilai sikap
def set_rubric_grade(sender, instance, **kwargs):
    if not instance.grade:
        if (instance.score > 92) and (instance.score < 101):
            instance.grade = "A"
        elif (instance.score > 85) and (instance.score < 93):
            instance.grade = "B"
        elif (instance.score > 81) and (instance.score < 86):
            instance.grade = "C"
        elif (instance.score > 69) and (instance.score < 82):
            instance.grade = "D"
        else:
            instance.grade = "E"

def set_extra_grade(sender, instance, **kwargs):
    if not instance.extra_description:
        if (instance.extra_score > 92) and (instance.extra_score < 101):
            instance.extra_description = "A"
        elif (instance.extra_score > 85) and (instance.extra_score < 93):
            instance.extra_description = "B"
        elif (instance.extra_score > 81) and (instance.extra_score < 86):
            instance.extra_description= "C"
        elif (instance.extra_score > 69) and (instance.extra_score < 82):
            instance.extra_description = "D"
        else:
            instance.extra_description = "E"

# def set_rubric_desc(sender, instance, **kwargs):
#     if not instance.description:
#         if instance.grade == "A":
#             # Filter:
#             # Lookup Grade depends on the grade gotten
#             # Rubric FK = Rubric's Description Field
#             instance.description = ReportcardRubricTemplate.objects.filter(lookup_grade='A', rubric__type=instance.rubric.description).values_list('text', flat=True).annotate(description=Replace('text', Value('[Nama Siswa]'), Value(str(instance.student)), output_field=CharField())).first()
#             # instance.description = ReportcardRubricTemplate.objects.filter(lookup_grade='A',
#             #                                                                rubric__type=instance.rubric.type).update(
#             #     text=Replace('text', Value('[Nama Siswa]'), Value(str(instance.student.registration_data.first_name))))
#         elif instance.grade == "B":
#             instance.description = ReportcardRubricTemplate.objects.filter(lookup_grade='B', rubric__type=instance.rubric.description).values_list('text', flat=True).annotate(description=Replace('text', Value('[Nama Siswa]'), Value(str(instance.student)), output_field=CharField())).first()
#         elif instance.grade == "C":
#             instance.description = ReportcardRubricTemplate.objects.filter(lookup_grade='C', rubric__type=instance.rubric.description).values_list('text', flat=True).annotate(description=Replace('text', Value('[Nama Siswa]'), Value(str(instance.student)), output_field=CharField())).first()
#         elif instance.grade == "D":
#             instance.description = ReportcardRubricTemplate.objects.filter(lookup_grade='D', rubric__type=instance.rubric.description).values_list('text', flat=True).annotate(description=Replace('text', Value('[Nama Siswa]'), Value(str(instance.student)), output_field=CharField())).first()
#         else:
#             instance.description = ReportcardRubricTemplate.objects.filter(lookup_grade='E', rubric__type=instance.rubric.description).values_list('text', flat=True).annotate(description=Replace('text', Value('[Nama Siswa]'), Value(str(instance.student)), output_field=CharField())).first()

def set_rubric_desc(sender, instance, **kwargs):
    if not instance.description:
        template_text = ReportcardRubricTemplate.objects.filter(
            lookup_grade=instance.grade,
            rubric=instance.rubric
        ).values_list('text', flat=True).first()

        if template_text:
            student_name = f"{instance.student.registration_data.first_name} {instance.student.registration_data.last_name}"
            instance.description = template_text.replace("[Nama Siswa]", student_name)

def tambah_record_rubriksiswa(sender, instance, created, **kwargs):
    if created:
        id_nilai_rapor = instance.id
        
        pass

#untuk tabel subject saat hendak dan setelah disimpan
pre_save.connect(make_shortname, Subject)
post_save.connect(new_subject, Subject)

#untuk tabel GradeEntry setelah guru mengisi form isi nilai
post_save.connect(new_grade_entry, GradeEntry)

#konversi nilai raport ke huruf
pre_save.connect(set_final_grade, ReportcardGrade)

#buat record rubrik untuk tiap 1 nilai raport
# post_save.connect(tambah_record_rubriksiswa, ReportcardGrade)

# konversi nilai sikap ke huruf
pre_save.connect(set_rubric_grade, StudentBehaviourReport)

pre_save.connect(set_rubric_desc, StudentBehaviourReport)

pre_save.connect(set_extra_grade, StudentReportExtra)