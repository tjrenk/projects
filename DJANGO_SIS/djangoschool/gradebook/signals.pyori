from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from gradebook.models import Subject, GradeEntry, AssignmentHead, CourseMember, AssignmentDetail, ReportcardGrade

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
        if (instance.final_score > 89) and (instance.final_score < 101):
            instance.final_grade = "A"
        elif (instance.final_score > 85) and (instance.final_score < 90):
            instance.final_grade = "B"
        elif (instance.final_score > 79) and (instance.final_score < 86):
            instance.final_grade = "C"
        else:
            instance.final_grade = "D"

#untuk tabel subject saat hendak dan setelah disimpan
pre_save.connect(make_shortname, Subject)
post_save.connect(new_subject, Subject)

#untuk tabel GradeEntry setelah guru mengisi form isi nilai
post_save.connect(new_grade_entry, GradeEntry)

#konversi nilai raport ke huruf
pre_save.connect(set_final_grade, ReportcardGrade)