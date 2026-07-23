from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from admission.models import AcademicYear, Registration, ClassMember, Student

from django.db.models.functions import Replace
from django.db.models import Value
from django.db.models import ExpressionWrapper, F, TextField, CharField


def student_id_gen(sender, instance, **kwargs):
    if not instance.id_number:
        current_ay = AcademicYear.objects.order_by('-year').first()
        ay_year = int(current_ay.year) if current_ay else datetime.now().year

        batch_number = ay_year - 2022
        batch_str = f"{batch_number:02d}"
        year_str = f"{ay_year % 100:02d}"
        prefix = f"{batch_str}{year_str}"

        # Get existing id_numbers with this prefix, extract their sequence part
        existing_ids = Student.objects.filter(
            id_number__startswith=prefix
        ).values_list('id_number', flat=True)

        max_seq = 0
        for id_number in existing_ids:
            seq_part = id_number[len(prefix):]  # whatever comes after the prefix
            if seq_part.isdigit():
                max_seq = max(max_seq, int(seq_part))

        seq_str = f"{max_seq + 1:02d}"
        instance.id_number = f"{prefix}{seq_str}"


pre_save.connect(student_id_gen, Student)