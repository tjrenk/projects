from pyexpat.errors import messages

from django.db import transaction
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, JsonResponse
import re
from formtools.wizard.views import SessionWizardView
from .forms import *
from .models import *
from admission.models import Class, ClassMember, Teacher, Student, User
from django.db.models import Sum, Avg, Count, Max, Min, Q
from django.db.models import F
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, cm
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Frame, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Line
from slick_reporting.views import ReportView, SlickReportView
from slick_reporting.fields import ComputationField
import io
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import modelformset_factory, formset_factory
from django.core.paginator import Paginator
from django import forms, template
from django.template.loader import render_to_string
from django.contrib.auth import logout
from django.db.models.functions import Ceil
from django.utils import timezone
from django_htmx.http import retarget
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_str

register = template.Library()


def log_activity(user, obj, action, message=""):
    """
    Reusable logger for frontend CRUD actions, mirrors what the admin
    panel does automatically for admin-based changes.

    action: 'add', 'change', or 'delete'
    """
    action_map = {
        'add': ADDITION,
        'change': CHANGE,
        'delete': DELETION,
    }

    LogEntry.objects.log_action(
        user_id=user.id,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=force_str(obj),
        action_flag=action_map.get(action, CHANGE),
        change_message=message or f"{action.capitalize()}d via frontend",
    )

# BUAT SORTING TABEL
def get_sort_params(request, sort_map, default_sort='id', default_dir='desc'):
    sort_by = request.GET.get('sort', default_sort)
    sort_dir = request.GET.get('dir', default_dir)
    order_field = sort_map.get(sort_by, sort_map.get(default_sort, 'id'))
    if sort_dir == 'desc':
        order_field = f'-{order_field}'

    return order_field, sort_by, sort_dir


def apply_filters(queryset, request, filter_map):
    for param, lookup in filter_map.items():
        value = request.GET.get(param)
        if value:
            queryset = queryset.filter(**{lookup: value}).distinct()
    return queryset


def gb_index(request):
    user = request.user

    # shared across all roles
    announcements = Announcement.objects.filter(
        is_active=True,
    ).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=timezone.now().date())
    ).select_related('author').order_by('-is_pinned', '-created_at')

    context = {
        'request': request,
        'announcements': announcements,
    }

    if user.is_authenticated:
        teacher = Teacher.objects.filter(user=user).select_related('user').first()
    else:
        teacher = None

    context = {
        'request': request,
        # other shared context
    }

    # if teacher:
    #     # teacher-specific context
    #     pass
    # elif user.is_authenticated and (user.is_staff or user.is_superuser):
    #     # admin context
    #     pass
    # else:
    #     # student / anonymous context
    #     pass

    if user.is_staff or user.is_superuser:
        # admin view — summary counts only, no heavy querysets


        context.update({
            'rpcard': ReportcardGrade.objects.select_related(
            'reportcard__student__registration_data', 'subject'
        ).order_by('-final_score').distinct()[:10],
            'student_count': Student.objects.filter(is_active=True).count(),
            'teacher_count': Teacher.objects.count(),
            'attendance_recent': StudentAttendance.objects.select_related('student__registration_data').order_by('-attendance_date')[:10],
        })

        context['announcements'] = Announcement.objects.filter(
            is_active=True,
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=timezone.now().date())
        ).select_related('author').order_by('-is_pinned', '-created_at')

    elif teacher:
        # teacher view
        context['teacher'] = teacher
        # context['is_homeroom'] = is_homeroom
        #
        # if is_homeroom:
        #     homeroom = Class.objects.filter(
        #         teacher=teacher, is_home_class=True
        #     ).prefetch_related('classmember_set__student').first()
        #     context['homeroom_class'] = homeroom

        # only fetch recent attendance for their students
        context['attendance_recent'] = StudentAttendance.objects.select_related('student__registration_data').order_by('-attendance_date').distinct()[:10]
        context['announcements'] = Announcement.objects.filter(
            is_active=True,
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=timezone.now().date())
        ).select_related('author').order_by('-is_pinned', '-created_at')

        # recent grades for their courses
        context['rpcard'] = ReportcardGrade.objects.filter(
            reportcard__student__coursemember__course__teacher=teacher
        ).select_related(
            'reportcard__student__registration_data', 'subject'
        ).order_by('-final_score').distinct()[:10]

    else:
        context['rpcard'] = ReportcardGrade.objects.select_related(
            'reportcard__student__registration_data', 'subject'
        ).order_by('-final_score').distinct()[:10]

        context['announcements'] = Announcement.objects.filter(
        is_active=True,
    ).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=timezone.now().date())
    ).select_related('author').order_by('-is_pinned', '-created_at')

    return render(request, "partials/gradebook/index.html", context)


def logout_view(request):
    logout(request)


@login_required
def get_courses(request):
    subject_id = request.GET.get('subject_id')
    if subject_id:
        courses = Course.objects.filter(subject_id=subject_id).values('id', 'name')
        return JsonResponse(list(courses), safe=False)
    return JsonResponse([], safe=False)


def teacher_list(request):
    return HttpResponse("pass")


def course_list(request):
    return HttpResponse("pass")


@login_required
def grade_entry(request):
    entry = GradeEntry.objects.get(pk=3)
    form = GradeEntryForm(instance=entry, user=request.user)
    context = {'form': form}
    return render(request, "partials/gradebook/entry.html", context)


def get_period(request):
    pass


def logout_view(request):
    logout(request)


@login_required
def attendance(request):  # musti di cek ini kefilter berdasarkan guru apa kgk list siswany
    # cannot unpack non-iterable ForwardManyToOneDescriptor object
    # current_teacher = get_object_or_404(Teacher, user=request.user)
    # filtered_students = Teacher.objects.filter(current_teacher)

    if request.method == 'POST':
        user = request.user
        # homeroom_check = Class.objects.filter(teacher__user=user, is_home_class=True).first()
        # if a user has a teacher relationship / if in the teacher model the logged in user matches with a data in the Teacher model
        # if homeroom_check:
        form = AttendanceForm(request.POST, user=request.user)
        # teach_form = TeacherForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, f"Data absensi sudah tersimpan!")

    # if not hasattr(request.user, 'teacher'):
    #     return redirect('gb-index')

    form = AttendanceForm(user=request.user)
    # teach_form = TeacherForm()

    # if 'student' in form.fields:
    #     form.fields['student'].queryset = filtered_students

    context = {
        'form': form,
        # 'classes': filtered_students
    }

    return render(request, 'partials/gradebook/attendance.html', context)


# @register.inclusion_tag('partials/gradebook/attendance_list.html', takes_context=True)
# def attendance_list(request):
#     attendance = StudentAttendance.objects.select_related('student')
#
#     pnation = Paginator(attendance, 15)  # Show 10 aktivitas per page
#     page = request.GET.get('page')
#     pnation_attend = pnation.get_page(page)
#
#     context = {
#         'attendance': attendance,
#         'pnation_attend': pnation_attend
#     }
#
#     return render(request, 'partials/gradebook/attendance_list.html', context)


def attendance_list_admin(request):
    attendance = StudentAttendance.objects.select_related('student')

    pnation = Paginator(attendance, 15)  # Show 10 aktivitas per page
    page = request.GET.get('page')
    pnation_attend = pnation.get_page(page)

    context = {
        'attendance': attendance,
        'pnation_attend': pnation_attend
    }

    return render(request, 'admin/attendance_list_homepage.html', context)


class GradeEntryForm(LoginRequiredMixin, SessionWizardView):
    template_name = "partials/gradebook/grade_entry.html"

    form_list = [
        ("0", GradeEntryForm),
        ("1", AssignmentHeadForm),
        ("2", AssignmentDetailFormSet),
    ]

    def _get_homeroom_class(self):
        return Class.objects.filter(
            teacher__user=self.request.user,
        ).first()

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)

        if step == '2':
            step0_data = self.get_cleaned_data_for_step('0')
            if not step0_data or 'course' not in step0_data:
                return initial

            # select_related here prevents N+1 when building initial_list
            members = CourseMember.objects.filter(
                course=step0_data['course'],
                is_active=True
            ).select_related('student').only(
                'student__id', 'is_active'  # only fetch what we actually use
            )

            return [
                {'student': m.student.id, 'is_active': m.is_active}
                for m in members
            ]

        return initial

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)

        if step == '0':
            kwargs['user'] = self.request.user

        if step == '2':
            step1_data = self.get_cleaned_data_for_step('1')
            if step1_data and 'max_score' in step1_data:
                kwargs['max_score'] = step1_data['max_score']

            initial = self.get_form_initial(step)
            kwargs['form_kwargs_list'] = [{'form_index': i} for i in range(len(initial))]

        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        # only query homeroom once and only on steps that need it
        if self.steps.current in ('0', '1'):
            context['is_homeroom'] = self._get_homeroom_class()

        step0_data = self.get_cleaned_data_for_step('0')
        if step0_data:
            cpmp_targets = step0_data.get('cpmp_target')
            context.update({
                'selected_academic_year': step0_data.get('academic_year'),
                'selected_period':        step0_data.get('period'),
                'selected_level':         step0_data.get('level'),
                'selected_subject':       step0_data.get('subject'),
                'selected_is_mid':        step0_data.get('is_mid'),
                'selected_assignment_type': step0_data.get('assignment_type'),
                'selected_cpmp_target': [t.text for t in cpmp_targets] if cpmp_targets else [],
            })

        step1_data = self.get_cleaned_data_for_step('1')
        if step1_data:
            context.update({
                'selected_topic': step1_data.get('topic'),
                'selected_date':  step1_data.get('date'),
            })

        return context

    def post(self, *args, **kwargs):
        wizard_goto_step = self.request.POST.get('wizard_goto_step')
        if wizard_goto_step:
            self.storage.current_step = wizard_goto_step
            return self.render(self.get_form())
        return super().post(*args, **kwargs)

    def done(self, form_list, **kwargs):
        data0 = form_list[0].cleaned_data
        data1 = form_list[1].cleaned_data
        formset = form_list[2]

        assignment_head = AssignmentHead(
            assignment=data0['assignment_type'],
            course=data0['course'],
            date=data1['date'],
            topic=data1['topic'],
            max_score=data1['max_score'],
        )
        assignment_head.save()
        assignment_head.cpmp_target.set(data0['cpmp_target'])

        max_score = assignment_head.max_score
        details_to_create = []

        for form in formset:
            if not form.is_valid() or not form.cleaned_data:
                continue
            detail = form.save(commit=False)
            detail.assignment_head = assignment_head
            detail.teacher_notes = form.cleaned_data.get('teacher_notes')
            if detail.score > max_score:
                # rollback the head we just saved
                assignment_head.delete()
                messages.error(self.request, f"Score for a student exceeds max score of {max_score}.")
                return redirect('grade-entry')
            details_to_create.append(detail)

        AssignmentDetail.objects.bulk_create(details_to_create)
        log_activity(self.request.user, assignment_head, 'add', "Created new grade entry")
        messages.success(self.request, "Grade entry saved successfully!")
        return redirect('grade-entry')


def midterm_report(request):
    # all_users = User.objects.filter(groups=1).order_by('-angkatan').all() # semuanya kecuali
    all_students = Student.objects.all()

    # This will be the final list we send to the template.
    # student_list = []
    # user_rekap_list_by_prodi = []
    # user_rekap_list_by_angkatan = []

    # Loop through each user to perform calculations.
    # for u in all_students:
    #     # Calculate total 'Aktivitas' points for this specific user.
    #     aktivitas_points = Aktivitas.objects.filter(user=u, status="approved").aggregate(
    #         total=Sum(F('aturan_merit__poin') * F('kuantitas'), default=0)
    #     )['total']

    #     # Calculate total 'Pelanggaran' points for this specific user.
    #     pelanggaran_points = Pelanggaran.objects.filter(user=u).aggregate(
    #         total=Sum(F('aturan_demerit__poin') * F('kuantitas'), default=0)
    #     )['total']

    #     modal_poin = u.modal_poin_awal

    #     # Calculate the final total points, starting with a base of 100.
    #     total_points = (aktivitas_points or 0) - (pelanggaran_points or 0) + modal_poin

    #     # Append a dictionary with this user's complete data to our list.
    #     user_rekap_list.append({
    #         'user_obj': u,
    #         'aktivitas': aktivitas_points,
    #         'pelanggaran': pelanggaran_points,
    #         'total': total_points,
    #         'modal_poin': modal_poin
    #     })

    # The context now only needs to contain our clean, processed list.
    context = {
        # 'user_rekap_list': user_rekap_list,
        'all_students': all_students
    }
    # print(f"Sort type: {sort_type}, Order field: {order_field}")
    # print(f"All users count: {all_users.count()}")
    # print(f"First user: {all_users.first()}")
    # return render(request, 'rekap.html', context)
    # if request.headers.get('HX-Request'):
    #     return render(request, 'partials/rekap_table.html', context)

    return render(request, "partials/gradebook/generate_report.html", context)


def midterm_report_pdf(request, student_id=None):
    buf = io.BytesIO()
    # student_id = Student.id

    header_data = []
    # If user_id provided, limit to that user's records and set filename accordingly
    if student_id:
        stud_obj = get_object_or_404(Student, id=student_id)
        class_obj = get_object_or_404(Class, id=student_id)
        lperiod_obj = get_object_or_404(LearningPeriod, id=student_id)
        filename = f'ekupoint_report_table_{stud_obj}.pdf'

        header_data = [
            ['Nama: ', stud_obj.registration_data.first_name],
            ['NIS: ', stud_obj.id_number],
            ['NISN: ', stud_obj.nisn],
            ['        '],
            ['Kelas: ', class_obj.name],
            ['Semester: ', lperiod_obj.period_name],
            ['Tahun Ajaran: ', lperiod_obj.academic_year],
        ]
    else:
        filename = 'ekupoint_report_table.pdf'

    doc = SimpleDocTemplate(buf, pagesize=(595, 842))
    flowables = []

    styles = getSampleStyleSheet()

    center_style = ParagraphStyle(
        'Center',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontName='Times-Roman'
    )

    center_style_small = ParagraphStyle(
        'Center',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=8,
        fontName='Times-Roman'
    )

    title_style = ParagraphStyle(
        'TitleStyle',  # A name for the style
        parent=styles['Heading3'],  # Base it on the default "Heading1"
        fontSize=20,  # "Really big" size
        alignment=TA_CENTER,  # Center the text
        fontName='Times-Bold'  # Make sure it's bold
    )

    heading_style = ParagraphStyle(
        'HeadingStyle',  # A name for the style
        parent=styles['Heading3'],
        # Base it on the default "Heading1"              # "Really big" size        # Center the text
        fontName='Times-Bold'  # Make sure it's bold
    )

    times_nr = ParagraphStyle(
        'TimesNewRoman',
        fontName='Times-Bold'
    )

    kopsurat_nama_institusi = ParagraphStyle(
        'KopSuratNamaInstitusi',
        parent=styles['Normal'],
        fontSize=24,
        leading=24,
        alignment=TA_CENTER,
        fontName='Times-Roman',
        textColor="#5A0303"
    )
    available_width = doc.width

    separator = Drawing(available_width, 2)

    line = Line(
        x1=1, y1=1,
        x2=available_width, y2=1,
        strokeColor=colors.HexColor("#510000"),
        strokeWidth=1
    )

    separator.add(line)

    # # kopsurat versi gambar
    # kop_surat = os.path.join(settings.BASE_DIR, 'media/ekupoint/kopsurat.jpg')

    # # logo STTE, buat rekreasi kopsurat
    # logo = os.path.join(settings.BASE_DIR, 'media/ekupoint/logo-stte-jakarta-bwt-kopsurat.png')

    # setting gambar
    # kopsur = Image(kop_surat)
    # logo_stte = Image(logo, width=120, height=90)

    # kopsurat yang diambil dari dokumen2 lain; kalo mau dipake tinggal di uncomment
    # flowables.append(kopsur)

    header_text = "LAPORAN HASIL BELAJAR PESERTA DIDIK"
    akt_text_raw = "Aktivitas Mahasiswa:"
    pel_text_raw = "Pelanggaran Mahasiswa:"
    akt_text = Paragraph(akt_text_raw, times_nr)
    pel_text = Paragraph(pel_text_raw, times_nr)
    # header_2 = f"Nama: {user_obj.get_full_name()}"
    # header_3 = f"NIM: {user_obj.nim}"
    # header_4 = f"Prodi: {user_obj.prodi}"
    # header_5 = f"Angkatan: {user_obj.angkatan}"
    header = Paragraph(header_text, title_style)
    # header_dua = Paragraph(header_2)
    # header_tiga = Paragraph(header_3)
    # header_empat = Paragraph(header_4)
    # header_lima = Paragraph(header_5)

    # data2 rekreasi kop surat
    # kop_left_content = [
    #     logo_stte,
    # ]

    # kop_right_content = [
    #     Paragraph("SEKOLAH TINGGI TEOLOGI EKUMENE JAKARTA", kopsurat_nama_institusi),
    #     Spacer(1, 4),
    #     Paragraph("Mall Artha Gading Lantai 3, Jl. Artha Gading Sel. No. 3, Kelapa Gading, Jakarta Utara, Indonesia 14240", center_style_small),
    #     Paragraph("+628197577740      institusi.stte@sttekumene.ac.id      sttekumene.ac.id", center_style_small),
    # ]

    # kopsurat_data_1 = [
    #     [kop_right_content],
    # ]

    # kopsurat_table = Table(kopsurat_data_1, colWidths=[100, 400])

    # kopsurat_table.setStyle(TableStyle([
    #         ('GRID', (0, 0), (-1, -1), 0.5, "#FFFFFFFF"), # No grid
    #         ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    #         ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # Align labels (col 0) to the left
    #         ('ALIGN', (1, 0), (1, -1), 'LEFT'), # Align values (col 1) to the left
    #         ('FONTNAME', (0, 0), (0, -1), 'Times-Roman') # Make labels bold
    #     ]))
    # # rekreasi kop surat
    # flowables.append(kopsurat_table)
    # flowables.append(separator)
    # flowables.append(Spacer(1, 24))

    # judul ("EKUPOINT REPORT")
    flowables.append(header)
    # flowables.append(Spacer(1, 12))
    # flowables.append(header_dua)
    flowables.append(Spacer(1, 24))
    # flowables.append(header_tiga)
    # flowables.append(Spacer(1, 12))
    # flowables.append(header_empat)
    # flowables.append(Spacer(1, 12))
    # flowables.append(header_lima)
    # flowables.append(Spacer(1, 12))

    # not functional
    # title_data = [
    #         ["EKUPOINT REPORT", ""]
    #     ]

    # title_table = Table(title_data, colWidths=[100, 740])

    # title_table.setStyle(TableStyle([
    #         ('GRID', (0, 0), (-1, -1), 0.5, "#FFFFFF"), # No grid
    #         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    #         ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Align labels (col 0) to the left
    #         ('ALIGN', (1, 0), (1, -1), 'LEFT'), # Align values (col 1) to the left
    #         ('FONTNAME', (0, 0), (0, -1), 'Times-Bold'), # Make labels bold
    #     ]))

    # table format, biar rapi
    # if student_id:

    header_table = Table(header_data, colWidths=[100, 300])

    header_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, "#FFFFFF"),  # No grid
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Align labels (col 0) to the left
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Align values (col 1) to the left
        ('FONTNAME', (0, 0), (0, -1), 'Times-Bold'),  # Make labels bold
        ('FONTNAME', (1, 0), (1, -1), 'Times-Roman')
    ]))

    # data2 mahasiswa
    flowables.append(header_table)
    separator.add(line)
    flowables.append(Spacer(1, 24))

    # access student id dari: ReportCardgrade > StudentReportcard > Student
    student_qs = Student.objects.all()
    stdnt_rpc = StudentReportcard.objects.get(student=student_id)
    rpcgrade = ReportcardGrade.objects.get(reportcard=stdnt_rpc)
    rpcard_to_print = ReportcardGrade.objects.filter(reportcard=stdnt_rpc)

    # Aktivitas table
    styles = getSampleStyleSheet()
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, leading=10, fontName='Times-Roman',
                           splitLongWords=1, wordWrap='LTR')
    # headers_aktivitas = ["Aktivitas", "Jenis", "Lingkup", "Poin", "Kuantitas", "Keterangan", "File", "Status", "Tanggal"]
    headers_nilai = ["Mata Pelajaran", "KKM", "Nilai", "Predikat"]
    # aktivitas_total = contactdata.aggregate(
    #     total=Sum(F('aturan_merit__poin') * F('kuantitas'))
    # )['total'] or 0

    # pelanggaran_total = pelanggaran.aggregate(
    #     total=Sum(F('aturan_demerit__poin') * F('kuantitas'))
    # )['total'] or 0
    data_nilai = [headers_nilai]

    for obj in rpcard_to_print:
        data_row = [
            obj.subject,
            obj.final_score,
            obj.final_grade,
            obj.teacher_notes

        ]
        data_nilai.append(data_row)

    table_aktivitas = Table(data_nilai, repeatRows=1)
    table_aktivitas.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, '#000000'),
        ('BACKGROUND', (0, 0), (-1, 0), '#eeeeee'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman')
    ]))
    flowables.append(akt_text)
    flowables.append(table_aktivitas)

    # total_para_text = f"<b>Total Aktivitas:</b> {aktivitas_total}"
    # # total_para = Paragraph(f"<b>Total Aktivitas:</b> {aktivitas_total}", styles['Normal'])
    # total_para = Paragraph(total_para_text, times_nr)
    # flowables.append(Spacer(1, 6))
    # flowables.append(total_para)

    # # Spacer between tables
    # flowables.append(Spacer(1, 24))

    # # Pelanggaran table
    # # styles = getSampleStyleSheet()
    # # small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, leading=10)
    # # headers_pelanggaran = ["Pelanggaran", "Lingkup", "Poin", "Kuantitas", "Keterangan", "Tanggal"]
    # headers_pelanggaran = ["Pelanggaran", "Poin", "Kuantitas", "Keterangan", "Tanggal"]
    # data_pelanggaran = [headers_pelanggaran]
    # for obj in pelanggaran:
    #     aturan_para = Paragraph(str(obj.aturan_demerit) if obj.aturan_demerit else '', small)
    #     pelanggaran_para = Paragraph(obj.aturan_demerit.pelanggaran or '', small)
    #     keterangan_para = Paragraph(obj.keterangan or '', small)
    #     lingkup_para = Paragraph(obj.aturan_demerit.lingkup or '', small)
    #     kuantitas_para = Paragraph(str(obj.kuantitas) or '', small)
    #     created_at_para = Paragraph(obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '', small)
    #     data_row = [
    #         # obj.user.get_full_name() if obj.user else '',
    #         aturan_para,
    #         # pelanggaran_para,
    #         # obj.aturan_demerit.lingkup or '',
    #         getattr(obj, 'poin', '') or '',
    #         kuantitas_para,
    #         keterangan_para,
    #         created_at_para,
    #     ]
    #     data_pelanggaran.append(data_row)

    # colWidths = [80, 180, 200, 60, 40, 40, 160, 80, 50, 80]

    # table_pelanggaran = Table(data_pelanggaran, repeatRows=1)
    # table_pelanggaran.setStyle(TableStyle([
    #     # ('BOX', (0, 0), (-1, 0), 1.1, '#000000'),
    #     ('GRID', (0,0), (-1,-1), 0.5, '#000000'),
    #     ('BACKGROUND', (0,0), (-1,0), '#eeeeee'),
    #     ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    #     ('FONTSIZE', (0,0), (-1, -1), 8),
    #     ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
    #     ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman')
    # ]))
    # flowables.append(pel_text)
    # flowables.append(table_pelanggaran)

    #     # add Pelanggaran total
    # total_pel_para_text = f"<b>Total Pelanggaran:</b> {pelanggaran_total}"
    # # total_pel_para = Paragraph(f"<b>Total Pelanggaran:</b> {pelanggaran_total}", styles['Normal'])
    # total_pel_para = Paragraph(total_pel_para_text, times_nr)
    # flowables.append(Spacer(1, 6))
    # flowables.append(total_pel_para)

    # # grand total
    # grand_total = aktivitas_total - pelanggaran_total + modal_poin
    # grand_para_text = f"<b>Total (+ Modal Poin {modal_poin}):</b> {grand_total}"
    # # grand_para = Paragraph(f"<b>Total (+ Modal Poin {modal_poin}):</b> {grand_total}", styles['Heading3'])
    # grand_para = Paragraph(grand_para_text, times_nr)
    # flowables.append(Spacer(1, 12))
    # flowables.append(grand_para)

    # sig_left_content = [
    #     Paragraph("Dosen Wali", center_style),
    #     Paragraph("Akademik", center_style),
    #     Spacer(1, 80),
    #     Paragraph("(_________________)", center_style),
    # ]

    # sig_right_content = [
    #     Paragraph(f"Jakarta, {timezone.now().strftime('%d %B %Y')}", center_style,),
    #     Paragraph("Wakil Ketua Bidang Kemahasiswaan, ", center_style),
    #     Paragraph("Alumni, dan Kerja Sama", center_style),
    #     Spacer(1, 60), # 60-point gap for signature
    #     Paragraph("(_________________)", center_style),
    # ]

    # footer_data_1 = [
    #     [sig_left_content,'  ', sig_right_content],
    # ]

    # footer1_table = Table(footer_data_1)

    # footer1_table.setStyle(TableStyle([
    #         ('GRID', (0, 0), (-1, -1), 0.5, "#FFFFFF"), # No grid
    #         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    #         ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Align labels (col 0) to the left
    #         ('ALIGN', (1, 0), (1, -1), 'LEFT'), # Align values (col 1) to the left
    #         ('FONTNAME', (0, 0), (0, -1), 'Times-Roman') # Make labels bold
    #     ]))
    # flowables.append(Spacer(1, 24))
    # flowables.append(footer1_table)
    # flowables.append(Spacer(1, 24))

    doc.build(flowables)
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename=filename)


class ReportCardForm(LoginRequiredMixin, SessionWizardView):
    template_name = "partials/gradebook/report_card.html"

    form_list = [
        ("0", StudentReportcardForm),
        ("1", ReportCardGradeFormset),
    ]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == '0':
            kwargs['user'] = self.request.user
        return kwargs

    def _get_homeroom_class(self):
        user = self.request.user
        return Class.objects.filter(teacher__user=user).first()

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)

        if step == '1':
            user = self.request.user
            data0 = self.get_cleaned_data_for_step('0')
            homeroom_class = self._get_homeroom_class()

            if not data0 or not homeroom_class:
                return initial

            academic_year = data0.get('academic_year')
            period = data0.get('period')
            is_mid = data0.get('is_mid')
            level = data0.get('level')
            kelas = data0.get('kelas')

            # admin/staff uses kelas from step 0
            # homeroom teacher is locked to their own class
            if user.is_staff or user.is_superuser:
                kelas = data0.get('kelas')
                if not kelas:
                    return initial
                members = ClassMember.objects.filter(
                    kelas=kelas,
                    is_active=True,
                ).select_related('student__registration_data')
            else:
                homeroom_class = Class.objects.filter(
                    teacher__user=user
                ).first()
                if not homeroom_class:
                    return initial
                members = ClassMember.objects.filter(
                    kelas=homeroom_class,
                    is_active=True,
                ).select_related('student__registration_data')

            # batch fetch existing reportcards to avoid N+1
            student_ids = [m.student_id for m in members]
            existing_reportcards = {
                rc.student_id: rc
                for rc in StudentReportcard.objects.filter(
                    student_id__in=student_ids,
                    academic_year=academic_year,
                    period=period,
                    is_mid=is_mid,
                    level=level
                )
            }


            initial_list = []
            for member in members:
                student = member.student

                # Check if a reportcard already exists for this student
                existing_reportcard = StudentReportcard.objects.filter(
                    student=student,
                    academic_year=academic_year,
                    period=period,
                    is_mid=is_mid,
                    level=level
                ).first()

                initial_list.append({
                    'student_id': student.id,
                    'student_name': f"{student.id_number} - {student.registration_data.first_name} {student.registration_data.last_name}",
                    'ht_comment': existing_reportcard.ht_comment if existing_reportcard else None,
                })

            return initial_list
        return initial

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        data0 = self.get_cleaned_data_for_step('0')
        if data0:
            context['selected_academic_year'] = data0.get('academic_year')
            context['selected_period'] = data0.get('period')
            context['selected_is_mid'] = data0.get('is_mid')
            context['selected_level'] = data0.get('level')

        if self.steps.current == '0' or self.steps.current == '1':
            context['homeroom_class'] = self._get_homeroom_class()

        if self.steps.current == '1':
            context['selected_academic_year'] = data0.get('academic_year')
            context['selected_period'] = data0.get('period')
            context['selected_is_mid'] = data0.get('is_mid')
            context['selected_level'] = data0.get('level')

        return context

    def done(self, form_list, **kwargs):
        data0 = form_list[0].cleaned_data
        formset = form_list[1]

        academic_year = data0['academic_year']
        period = data0['period']
        is_mid = data0['is_mid']
        level = data0['level']

        homeroom_class = self._get_homeroom_class()
        if not homeroom_class:
            messages.error(self.request, "No homeroom class found for this teacher.")
            return redirect('report-card')

        with transaction.atomic():
            for form in formset:
                if form.is_valid() and form.cleaned_data:
                    data = form.cleaned_data
                    student_id = data.get('student_id')

                    # Save the homeroom teacher comment into ht_comment on StudentReportcard
                    StudentReportcard.objects.update_or_create(
                        student_id=student_id,
                        academic_year=academic_year,
                        period=period,
                        is_mid=is_mid,
                        level=level,
                        defaults={
                            # 'level': level,
                            'ht_comment': data.get('ht_comment'),
                        }
                    )

        messages.success(self.request, "Homeroom comments saved successfully!")
        return redirect('report-card')

# Grade Entry dynamic fields
def get_levels_ge(request):
    # Check for the variable name sent by the 'academic_year' field
    # (Django form fields usually send '0-academic_year')
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')

    if acayear_id:
        # Load levels only if a year is selected
        levels = GradeLevel.objects.select_related('school_level')
    else:
        levels = GradeLevel.objects.none()

    context = {'levels': levels}
    # Use your existing folder structure
    return render(request, "partials/gradebook/gradeentry_partials/level.html", context)


def get_teachers(request):
    period_id = request.GET.get('0-period') or request.GET.get('period')
    user = request.user

    if period_id:
        teachers = Teacher.objects.filter(user=user).all()
        if user.is_staff:
            teachers = Teacher.objects.all()
    else:
        teachers = Teacher.objects.none()
    context = {'teachers': teachers}
    return render(request, "partials/gradebook/gradeentry_partials/teacher.html", context)


def get_courses(request):
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('1-academic_year')  or request.GET.get('subject')
    subject_id = request.GET.get('0-subject') or request.GET.get('1-subject') or request.GET.get('subject')
    selected_course = request.GET.get('0-course') or request.GET.get('1-course') or request.GET.get('course')
    if subject_id:
        courses = Course.objects.filter(subject_id=subject_id, academic_year_id=acayear_id)
    else:
        courses = Course.objects.all()
    context = {
        'courses': courses,
        'selected_course': selected_course
    }
    return render(request, "partials/gradebook/course_list.html", context)


def get_period_ge(request):
    # acayear_id = AcademicYear.objects.first().id
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('1-academic_year') or request.GET.get(
        'academic_year')
    selected_period = request.GET.get('0-period') or request.GET.get('1-period') or request.GET.get('period')
    if acayear_id:
        periods = LearningPeriod.objects.filter(Q(academic_year_id=acayear_id) & Q(period_name__icontains='semester'))
    else:
        periods = LearningPeriod.objects.none()
    # context = {
    #     'periods': periods,
    #     'selected_period': selected_period
    # }
    # return render(request, "partials/gradebook/gradeentry_partials/period.html", context)

    # Render period HTML as before
    html = render_to_string("partials/gradebook/gradeentry_partials/period.html", {
        'periods': periods,
        'selected_period': selected_period
    })

    # Also render level HTML for OOB update (populated if academic_year is set)
    level_queryset = GradeLevel.objects.select_related('school_level') if acayear_id else GradeLevel.objects.none()
    selected_level = request.GET.get('0-level') or request.GET.get('1-level') or request.GET.get('level')
    level_html = render_to_string("partials/gradebook/gradeentry_partials/level.html", {
        'levels': level_queryset,
        'selected_level': selected_level
    })

    # Return period HTML + OOB update for level
    return HttpResponse(html + f'<div hx-swap-oob="#level-select-ge">{level_html}</div>')


def get_subjects_ge(request):
    teacher_id = request.GET.get('0-teacher') or request.GET.get('1-teacher') or request.GET.get('teacher')
    selected_subject = request.GET.get('0-subject') or request.GET.get('1-subject') or request.GET.get('subject')
    if teacher_id:
        # subjects = Subject.objects.filter(course__coursemember__student__coursemember__course__coursemember__course__teacher__id=teacher_id).distinct()
        subjects = Subject.objects.filter(course__teacher__id=teacher_id, is_activity=False).distinct()
    else:
        subjects = Subject.objects.none()
    context = {
        'subjects': subjects,
        'selected_subject': selected_subject
    }
    return render(request, "partials/gradebook/gradeentry_partials/subject.html", context)


def get_kelas_ge(request):
    teacher_id = request.GET.get('0-teacher') or request.GET.get('teacher')
    selected_kelas = request.GET.get('0-kelas') or request.GET.get('kelas')
    if teacher_id:
        # Filter classes where the teacher is the homeroom teacher
        # classes = Class.objects.filter(teacher__id=teacher_id, is_home_class=True).distinct()
        classes = Class.objects.filter(teacher__id=teacher_id).distinct()
    else:
        classes = Class.objects.none()
    context = {
        'classes': classes,
        'selected_kelas': selected_kelas
    }
    return render(request, "partials/gradebook/gradeentry_partials/kelas.html", context)


def get_courses_ge(request):
    print(request.GET)
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')
    subject_id = request.GET.get('0-subject') or request.GET.get('subject')
    selected_course = request.GET.get('0-course') or request.GET.get('course')

    if subject_id and acayear_id:
        courses = Course.objects.filter(subject_id=subject_id, academic_year_id=acayear_id)
    elif subject_id:
        # fallback: filter by subject only if acayear didn't come through
        courses = Course.objects.filter(subject_id=subject_id)
    else:
        courses = Course.objects.none()

    context = {
        'courses': courses,
        'selected_course': selected_course
    }
    return render(request, "partials/gradebook/gradeentry_partials/course.html", context)


def get_assignment_types_ge(request):
    # Check for the course ID
    course_id = request.GET.get('0-course') or request.GET.get('course')

    if course_id:
        # Get the subject from the course
        course = Course.objects.get(id=course_id)
        subject_id = course.subject_id
        # Get assignment types associated with the subject via Weighting table
        assignment_ids = Weighting.objects.filter(subject_id=subject_id).values_list('assignment_id',
                                                                                     flat=True).distinct()
        # types = AssignmentType.objects.filter(id__in=assignment_ids)
        types = AssignmentType.objects.all()
    else:
        types = AssignmentType.objects.none()

    context = {'assignment_types': types}  # Make sure this key matches your template loop
    return render(request, "partials/gradebook/gradeentry_partials/assignment_type.html", context)


# Report Card / Teacher Notes dynamic fields
def get_period_reportcard(request):
    # acayear_id = AcademicYear.objects.first().id
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('1-academic_year') or request.GET.get(
        'academic_year')
    selected_period = request.GET.get('0-period') or request.GET.get('1-period') or request.GET.get('period')
    if acayear_id:
        periods = LearningPeriod.objects.filter(academic_year_id=acayear_id, period_name__icontains='semester')
    else:
        periods = LearningPeriod.objects.none()
    context = {
        'periods': periods,
        'selected_period': selected_period
    }
    return render(request, "partials/gradebook/reportcard_partials/period.html", context)


def get_level_reportcard(request):
    # Check for the variable name sent by the 'academic_year' field
    # (Django form fields usually send '0-academic_year')
    period_id = request.GET.get('0-period') or request.GET.get('1-period') or request.GET.get('period')

    if period_id:
        # Load levels only if a period is selected
        levels = GradeLevel.objects.all()
    else:
        levels = GradeLevel.objects.none()

    context = {'levels': levels}
    # Use your existing folder structure
    return render(request, "partials/gradebook/reportcard_partials/level.html", context)


def get_cpmp_target_ge(request):
    print(request.GET)  # keep this temporarily to verify params

    acayear_id = (request.GET.get('0-academic_year')
                  or request.GET.get('1-academic_year')
                  or request.GET.get('academic_year'))
    course_id = (request.GET.get('0-course')
                 or request.GET.get('1-course')
                 or request.GET.get('course'))
    selected_cpmp_target = (request.GET.get('0-cpmp_target')
                            or request.GET.get('1-cpmp_target')
                            or request.GET.get('cpmp_target'))
    subject_id = (request.GET.get('0-subject')
                  or request.GET.get('1-subject')
                  or request.GET.get('subject'))

    if course_id:
        # filter by course directly — most precise
        cpmp_ids = CapaianPemelajaranMataPelajaran.objects.filter(
    academic_year_id=acayear_id, subject_id=subject_id
)
        cpmp_trg = CapaianPemelajaranMataPelajaran.objects.filter(id__in=cpmp_ids)
    elif acayear_id:
        # fallback: filter by academic year
        cpmp_ids = CapaianPemelajaranMataPelajaran.objects.filter(
            academic_year_id=acayear_id
        ).values_list('id', flat=True).distinct()
        cpmp_trg = CapaianPemelajaranMataPelajaran.objects.filter(id__in=cpmp_ids)
    else:
        cpmp_trg = CapaianPemelajaranMataPelajaran.objects.none()

    return render(request, "partials/gradebook/gradeentry_partials/cpmp_target.html", {
        'cpmp_trg': cpmp_trg,
        'selected_cpmp_target': selected_cpmp_target
    })


def toggle_na_reason(request):
    form_index = request.GET.get('form_index', '0')
    step = request.GET.get('step', '2')
    base_name = f'{step}-{form_index}'
    is_active = request.GET.get(f'{base_name}-is_active') == 'on'
    student_id = request.GET.get(f'{base_name}-student', '')
    student_nisn = request.GET.get(f'{base_name}-student_nisn', '')
    student_name = request.GET.get(f'{base_name}-student_name', '')

    if is_active:
        score_attrs = ''
        na_attrs = 'readonly style="background-color:#e9ecef;cursor:not-allowed;"'
    else:
        score_attrs = 'readonly style="background-color:#e9ecef;cursor:not-allowed;"'
        na_attrs = 'placeholder="Enter reason..."'

    html = f'''
        <input type="hidden" name="{base_name}-student" value="{student_id}">
        <td>{student_nisn}</td>
        <td><input type="text" readonly class="form-control-plaintext" name="{base_name}-student_name" value="{student_name}"></td>
        <td id="score_td_{form_index}">
            <input type="number" class="input"
                   name="{base_name}-score" value="0" {score_attrs}>
        </td>
        <td id="na_reason_td_{form_index}">
            <input type="text" class="input"
                   name="{base_name}-na_reason" value="" {na_attrs}>
        </td>
        <td class="text-center">
            <input type="checkbox"
                   name="{base_name}-is_active"
                   {"checked" if is_active else ""}
                   hx-get="/gradebook/toggle-na-reason/?form_index={form_index}&step={step}"
                   hx-trigger="change"
                   hx-target="#row_{form_index}"
                   hx-swap="innerHTML"
                   hx-include="[name='{base_name}-is_active'],[name='{base_name}-student'],[name='{base_name}-student_name'],[name='{base_name}-student_nisn'], [name='{base_name}-score']">
        </td>
    '''
    return HttpResponse(html)


# biar short name subject keliatan
# kalau pakai cara ini berarti ComputationField yg biasanya dipake di ReportView
# diambil alih scr manual pake yg ini
class ScoreField(ComputationField):
    # nama bisa apa aja (INI PENTING, HARUS ADA)
    name = "scorecolumn"
    # metode penghitungan (Sum, Avg, Count, dll)
    # calculation_method = Max
    # field yg mana yg mau dihitung
    calculation_field = "final_score"
    # nama output / nama non-internal (mau ditampilin sebagai apa)
    verbose_name = "Score"  # Default fallback
    # mau ditotalin apa kgk
    is_summable = False

    @classmethod  # ----> msh blm ngerti ini buat apaan
    def get_crosstab_field_verbose_name(cls, model, id):
        """
        This runs for EVERY dynamic column.
        model: The model class of the crosstab field (e.g., Subject)
        id: The ID of the specific item (e.g., Subject ID 1)
        """
        # If the ID is invalid (e.g. remainder column), return generic name

        # Fetch the subject name directly
        # Note: 'model' here is automatically passed as the Subject model class
        subject = Subject.objects.get(pk=id)
        # Use short_name if available, else subject_name
        return subject.short_name


class ReportCardGradeSummary(LoginRequiredMixin, ReportView):
    template_name = "partials/gradebook/report.html"

    report_title = "Report Card Ledger"

    # model yg mau dipake
    report_model = ReportcardGrade

    # form utk filtering (dari forms.py)
    form_class = RequestLogForm

    # date_field = "reportcard__period__date_end"

    # di grup dari apa
    # NOTE: hanya value dari ini saja yg akan keliatan di kolom, gtau knp
    group_by = "reportcard__student"

    # sediain header yg mau ditampilin apa aja
    columns = [
        "registration_data__first_name",
        "registration_data__last_name",
    ]

    # 2. Crosstab
    # filtering berdasarkan field apa
    crosstab_field = "subject"
    # isi kolom
    crosstab_columns = [ScoreField]
    # total (utk skrg ga ada ngapa2in ini var)
    crosstab_compute_remainder = False

    # 3. What goes inside the cells? (The Score)
    # crosstab_columns = [
    #     ComputationField.create(
    #         Sum,
    #         "final_score",
    #         verbose_name="Score",
    #         is_summable=False
    #     )
    # ]

    # logic filter dari forms.py diulangi lagi disini
    def get_crosstab_ids(self):
        """
        Determine which Subjects to show as columns.
        """
        # Get filters from the request
        ay_id = self.request.GET.get('academic_year')
        period_id = self.request.GET.get('period')
        # Checkbox often comes as 'on' or 'true' or just present
        is_mid = self.request.GET.get('is_mid')

        # --- SCENARIO 1: NOT FILTERED (Default View) ---
        if not ay_id and not period_id:
            # Return just the first 5 subjects as placeholders
            return [s.pk for s in Subject.objects.order_by('id')[:5]]

        # --- SCENARIO 2: FILTERED (User selected Year/Period) ---
        # We start with all grades
        qs = ReportcardGrade.objects.all()

        # Apply the same filters that the report body uses
        if ay_id:
            qs = qs.filter(reportcard__academic_year_id=ay_id)
        if period_id:
            qs = qs.filter(reportcard__period_id=period_id)
        if is_mid:
            qs = qs.filter(reportcard__is_mid=True)

        # distinct() ensures we don't get duplicate IDs
        # values_list('subject_id', flat=True) returns a list of IDs like [1, 2, 5]
        subject_ids = qs.values_list('subject_id', flat=True).distinct().order_by('subject_id')

        return list(subject_ids)

    def get_crosstab_compute_remainder(self):
        return False

    export_actions = ["export_pdf"]

    def export_pdf(self, report_data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="grade_report.pdf"'

        # 2. Create a buffer to hold the PDF data
        buffer = io.BytesIO()

        # Use Landscape A4 because crosstabs tend to be wide
        doc = SimpleDocTemplate(buffer, pagesize=(800, 600))
        elements = []

        # 3. Prepare the Data for the Table
        # report_data['columns'] holds the definitions.
        # report_data['data'] holds the list of dictionaries (rows).

        columns = report_data['columns']

        # A. Create the Header Row
        # We extract 'verbose_name' to show "Biology" instead of "subject_1"
        headers = [col['verbose_name'] for col in columns]
        table_data = [headers]

        # B. Create the Data Rows
        # We must loop through columns to ensure order matches headers
        for record in report_data['data']:
            row = []
            for col in columns:
                # Use the column 'name' (id) to fetch value from the record dictionary
                key = col['name']
                value = record.get(key, "-")  # Default to "-" if empty
                row.append(str(value))  # Ensure it's a string
            table_data.append(row)

        # 4. Create and Style the Table
        # 'colWidths' can be set to None (auto) or specific values
        table = Table(table_data)

        # Add styling: Grid, Bold Header, Alternating Row Colors
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header background
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Header text color
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center align all text
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header font
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Header padding
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  # Default row background
            ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Add grid lines
        ])
        table.setStyle(style)

        # 5. Add Title and Table to the Document
        styles = getSampleStyleSheet()
        elements.append(Paragraph("Student Grade Crosstab Report", styles['Title']))
        elements.append(table)

        # 6. Build the PDF
        doc.build(elements)

        # 7. Get the value of the BytesIO buffer and write it to the response
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)

        return response
        # return FileResponse(buffer, as_attachment=False, filename='ledger.pdf')

    export_pdf.title = ("Export PDF")
    export_pdf.icon = "fa fa-file-pdf-o"
    export_pdf.css_class = "btn btn-primary"

    def export_csv(self, report_data):
        return super().export_csv(report_data)

    export_csv.title = ("Export Report Card to CSV")
    export_csv.css_class = "btn btn-success"

    filters = [
        "reportcard__student__id_number",
        "reportcard__student__registration_data__first_name",
        "reportcard__student__registration_data__last_name"
    ]


def get_period_ledger(request):
    acayear_id = request.GET.get('academic_year')
    selected_period = request.GET.get('period')
    periods = LearningPeriod.objects.filter(
        academic_year_id=acayear_id,
        period_name__icontains='semester'
    ) if acayear_id else LearningPeriod.objects.none()

    html = ''
    for p in periods:
        checked = 'checked' if selected_period == str(p.id) else ''
        html += f'''
        <div class="form-check">
            <input class="form-check-input" type="radio" name="period" 
                   id="id_period_{p.id}" value="{p.id}" {checked}>
            <label class="form-check-label" for="id_period_{p.id}">
                {p.period_name}
            </label>
        </div>'''

    return HttpResponse(html)

# @login_required
# @require_POST
# def ge_bulk_delete(request):
#     # Ambil list ID yang dicentang dari form
#     selected_ids = request.POST.getlist('selected_ids')
#
#     if selected_ids:
#         # Django otomatis nge-bulk delete data terkait secara teroptimasi
#         deleted_count, _ = AssignmentHead.objects.filter(id__in=selected_ids).delete()
#         messages.success(request, f"{deleted_count} data berhasil dibuang sekaligus.")
#     else:
#         messages.warning(request, "Belum ada data yang terpilih")
#
#     return redirect('ge-table')  # Sesuaikan dengan nama URL routing tabel kamu

@login_required
def ge_table(request):
    user = request.user
    teacher = Teacher.objects.filter(user=user).first()

    # sorting
    order_field, sort_by, sort_dir = get_sort_params(request, {
        'date': 'date',
        'course': 'course__name',
        'assignment': 'assignment__name',
        'topic': 'topic',
        'max_score': 'max_score',
    }, default_sort='date')

    # base queryset
    if teacher:
        ah = AssignmentHead.objects.filter(
            course__teacher=teacher
        ).select_related('course__subject', 'course__teacher', 'assignment')
    else:
        ah = AssignmentHead.objects.select_related(
            'course__subject', 'course__teacher', 'assignment'
        )

    # filtering — BEFORE pagination
    ah = apply_filters(ah, request, {
        'subject': 'course__subject_id',
        'course': 'course_id',
        'year': 'course__academic_year_id',
        'type': 'assignment_id'
    })

    # search — BEFORE pagination
    search_query = request.GET.get('q', '')
    if search_query:
        ah = ah.filter(
            Q(topic__icontains=search_query) |
            Q(course__name__icontains=search_query) |
            Q(assignment__name__icontains=search_query)
            # Q(max_score=search_query) if search_query.isdigit() else Q() |
            # Q(date__year=search_query) if search_query.isdigit() else Q()
        )

    # apply sort AFTER filtering
    ah = ah.order_by(order_field)

    # pagination — LAST
    pnation = Paginator(ah, 15)
    pnation_ah = pnation.get_page(request.GET.get('page'))

    return render(request, 'partials/gradebook/grade_entry_table.html', {
        'pnation_ah': pnation_ah,
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'search_query': search_query,
        'selected_subject': request.GET.get('subject', ''),
        'selected_course': request.GET.get('course', ''),
        'extra_filters': [
            {
                'label': 'Academic Year',
                'param': 'year',
                'options': AcademicYear.objects.all(),
                'selected': request.GET.get('year', ''),
            },
            # {
            #     'label': 'Subject',
            #     'param': 'subject',
            #     'options': Subject.objects.filter(is_activity=False),
            #     'selected': request.GET.get('subject', ''),
            # },
            {
                'label': 'Course',
                'param': 'course',
                'options': Course.objects.filter(teacher=teacher, is_activity=False).select_related('subject'),
                'selected': request.GET.get('course', ''),
            },
            {
                'label': 'Assignment Type',
                'param': 'type',
                'options': AssignmentType.objects.all(),
                'selected': request.GET.get('type', ''),
            },
        ],
        'academic_years': AcademicYear.objects.all(),
        'classes': Course.objects.filter(teacher=teacher, is_activity=False).select_related('subject') if teacher else Course.objects.none(),
        'selected_year': request.GET.get('year', ''),
        'selected_class': request.GET.get('class', ''),
    })


# from .models import AssignmentDetail, CourseMember


# INGET YA ID ASSIGNMENTDETAIL != ID ASSIGNMENTHEAD PANTES DRTD NGACO MULU QUERYSETNYA
@login_required
def ge_edit(request, pk):
    parent_head = get_object_or_404(
        AssignmentHead.objects.select_related(
            'course', 'assignment'
        ).prefetch_related('cpmp_target'),
        pk=pk
    )

    active_members = CourseMember.objects.filter(
        course=parent_head.course, is_active=True
    ).select_related('student')

    # bulk sync — one query to check, one to insert
    existing_ids = set(
        AssignmentDetail.objects.filter(
            assignment_head=parent_head
        ).values_list('student_id', flat=True)
    )
    new_details = [
        AssignmentDetail(
            assignment_head=parent_head,
            student=member.student,
            score=0,
            is_active=True
        )
        for member in active_members
        if member.student_id not in existing_ids
    ]
    if new_details:
        AssignmentDetail.objects.bulk_create(new_details, ignore_conflicts=True)

    queryset = AssignmentDetail.objects.filter(
        assignment_head=parent_head
    ).order_by('student__id').select_related('student__registration_data')

    AssignmentFormSet = modelformset_factory(
        AssignmentDetail,
        fields=('score', 'na_reason', 'is_active'),
        extra=0,
    )

    if request.method == 'POST':
        formset = AssignmentFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            log_activity(request.user, parent_head, 'change', "Updated via Grade Entry form")
            return redirect('grade-entry-table')
    else:
        formset = AssignmentFormSet(queryset=queryset)

    for i, form in enumerate(formset):
        htmx_attrs = {
            'hx-get': f'/gradebook/toggle-na-reason/?form_index={i}',
            'hx-trigger': 'change',
            'hx-target': f'#na_reason_td_{i}',
            'hx-swap': 'innerHTML',
            'hx-include': f'[name="{form.add_prefix("na_reason")}"], [name="{form.add_prefix("is_active")}"]',
        }
        form.fields['na_reason'].widget.attrs.update({
            **htmx_attrs,
            'class': 'form-control textarea textarea-bordered w-full min-w-24 focus:outline-0 transition-all focus:outline-offset-0'
        })
        form.fields['is_active'].widget.attrs.update(htmx_attrs)

    return render(request, 'partials/gradebook/grade_entry_edit.html', {
        'formset': formset,
        'parent_head': parent_head,
        'title': parent_head.topic,
        'date': parent_head.date,
        'max_score': parent_head.max_score,
        'assign_type': parent_head.assignment,
        'cpmp_target': '\n'.join(t.text for t in parent_head.cpmp_target.all()) or '-',
    })


def ge_del(request, pk):
    ahead = get_object_or_404(AssignmentHead.objects.prefetch_related('cpmp_target'), pk=pk)
    cpmp_trg = '\n'.join(target.text for target in ahead.cpmp_target.all())
    # topic = ahead.topic
    if request.method == 'POST':
        log_activity(request.user, ahead, 'delete', "Deleted via table view")
        ahead.delete()
        return redirect('grade-entry-table')

    # For a GET request, show the empty form
    # form = PelanggaranForm()
    context = {
        'ahead': ahead,
        'cpmp_target': ahead.cpmp_target.all()
    }
    return render(request, 'partials/gradebook/grade_entry_delconf.html', context)


@login_required
def tc_table(request):
    user = request.user
    teacher = Teacher.objects.filter(user=user).first()
    homeroom_class = Class.objects.filter(teacher=teacher).first() if teacher else None
    order_field, sort_by, sort_dir = get_sort_params(request, {
        'academic_year': 'academic_year',
        'period': 'period',
        'student': 'student',
        'is_mid': 'is_mid',
        'level': 'level'
    }, default_sort='academic_year')

    src = StudentReportcard.objects.filter(
        ht_comment__isnull=False
    ).exclude(
        ht_comment=""
    ).select_related(
        'student__registration_data',
        'academic_year',
        'period',
    ).order_by(order_field)

    src = apply_filters(src, request, {
        'academic_year': 'academic_year_id',
        'period': 'period_id',
        'student': 'student_id',
        'is_mid': 'is_mid'
    })

    search_query = request.GET.get('q', '')
    if search_query:
        src = src.filter(
            Q(student__registration_data__first_name__icontains=search_query) |
            Q(student__registration_data__last_name__icontains=search_query) |
            Q(student__id_number__icontains=search_query) |
            Q(student__nisn__icontains=search_query) |
            Q(period__period_name__icontains=search_query)
        )

    # apply sort AFTER filtering
    src = src.order_by(order_field)

    pnation = Paginator(src, 15)
    pnation_src = pnation.get_page(request.GET.get('page'))


    return render(request, 'partials/gradebook/report_card_table.html', {
        'pnation_src': pnation_src,
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'search_query': search_query,
        'extra_filters': [
            {
                'label': 'Academic Year',
                'param': 'year',
                'options': AcademicYear.objects.all(),
                'selected': request.GET.get('year', ''),
            },
            {
                'label': 'Learning Period',
                'param': 'period',
                'options': LearningPeriod.objects.filter(period_name__icontains='semester'),
                'selected': request.GET.get('period', ''),
            },
            {
                'label': 'Student',
                'param': 'student',
                'options': Student.objects.filter(
                    classmember__kelas=homeroom_class,
                    classmember__is_active=True
                ).distinct() if homeroom_class else Student.objects.filter(
                    classmember__isnull=False
                ).distinct(),
                'selected': request.GET.get('student', ''),
            },
            # {
            #     'label': 'Midtest?',
            #     'param': 'is_mid',
            #     'options': [('true', 'True'), ('false', 'False')],
            #     'selected': request.GET.get('is_mid', ''),
            # },
        ],
    })

    # response = render(request, 'partials/gradebook/report_card_table.html',
    #                   {'pnation_src': pnation_src,
    #     'sort_by': sort_by,
    #     'sort_dir': sort_dir,)
    # if request.htmx:
    #     return retarget(response, '#grade-table-container')
    # return response


@login_required
def tc_view(request, pk):
    # 1. Get the reference detail to find the 'Head' assignment
    # target_detail = get_object_or_404(AssignmentDetail, pk=pk)
    user = request.user
    parent_head = get_object_or_404(StudentReportcard, pk=pk)
    selected_student = parent_head.student
    selected_ismid = parent_head.is_mid
    selected_acayear = parent_head.academic_year
    selected_period = parent_head.period


    # # 2. DATA SYNC: Ensure ALL active students in this course have a row for this assignment
    # # This fixes the issue where only 1 student shows up.
    # active_members = CourseMember.objects.filter(course=current_subject.id, is_active=True)

    # for member in active_members:
    #     # Create a blank row (score=0) if it doesn't exist yet
    #     ReportcardGrade.objects.get_or_create(
    #         reportcard=parent_head,
    #         student=member.student,
    #         defaults={'score': 0, 'is_active': True}
    #     )

    # print(f"Target Detail:  {target_detail}")
    # print(f"Parent: {parent_head}")
    # print(f"Course: {current_course}")

    # 3. Create the Queryset containing ALL students for this assignment
    # We order by student ID (or name if available) to keep the list stable
    queryset = StudentReportcard.objects.filter(student=selected_student, is_mid=selected_ismid, academic_year=selected_acayear, period=selected_period)

    # 4. Define the Formset
    class OptionalGradeForm(forms.ModelForm):
        class Meta:
            model = StudentReportcard
            # Include all fields you plan to use in the factory
            fields = ('student', 'ht_comment')
            # widgets = {
            #     'student': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
            #     'ht_comment': forms.TextInput(attrs={'class': 'form-control', 'rows': 1}),
            # }


    # --- 2. Pass the custom form to the factory ---
    ReportCardGradeFormset = modelformset_factory(
        StudentReportcard,
        form=OptionalGradeForm,  # <--- THIS IS THE KEY CHANGE
        extra=0
    )

    if request.method == 'POST':
        formset = ReportCardGradeFormset(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            return redirect('report-card-table')  # Make sure this URL name is correct in urls.py
        else:
            print(formset.errors)
    else:
        formset = ReportCardGradeFormset(queryset=queryset)

    return render(request, 'partials/gradebook/report_card_edit.html', {
        'formset': formset,
        'parent_head': parent_head
    })


def tc_del(request, pk):
    src = get_object_or_404(StudentReportcard, pk=pk)
    if request.method == 'POST':
        src.ht_comment = None
        src.save()
        return redirect('report-card-table')

    # For a GET request, show the empty form
    # form = PelanggaranForm()
    context = {
        'src': src,
    }
    return render(request, 'partials/gradebook/grade_entry_delconf.html', context)


@login_required
def toggle_na_reason(request):
    form_index = request.GET.get('form_index', '0')
    base_name = f'form-{form_index}'

    na_reason_name = f'{base_name}-na_reason'
    score_name = f'{base_name}-score'
    is_active = request.GET.get(f'{base_name}-is_active') == 'on'

    if is_active:
        na_reason_html = f'''<input id="na_reason_input_{form_index}"
               type="text" class="input"
               name="{na_reason_name}" value=""
               readonly style="background-color:#e9ecef;cursor:not-allowed;">'''
        score_html = f'''<input type="number" class="input"
               name="{score_name}" value="0">'''
    else:
        na_reason_html = f'''<input id="na_reason_input_{form_index}"
               type="text" class="input"
               name="{na_reason_name}" value=""
               placeholder="Enter reason...">'''
        score_html = f'''<input type="number" class="input"
               name="{score_name}" value="0"
               readonly style="background-color:#e9ecef;cursor:not-allowed;">'''

    return HttpResponse(
        na_reason_html +
        f'<div id="score_td_{form_index}" hx-swap-oob="innerHTML">{score_html}</div>'
    )




# Create FormSet for Step 1 (Student List)
StudentListFormSet = formset_factory(StudentListForm, formset=StudentListFormSetBase, extra=0)


# ENTRY NILAI SIKAP
class RubricEntryWizard(LoginRequiredMixin, SessionWizardView):
    # Definisikan template untuk setiap step (opsional, bisa pakai satu template saja)
    template_name = "partials/gradebook/rubric_entry.html"

    form_list = [
        ("0", RubricEntryForm),
        ("1", StudentListFormSet)
    ]

    # def get_template_names(self):
    #     return [self.templates[self.steps.current]]

    def get(self, request, *args, **kwargs):
        """Override GET to allow redirecting to a specific step without resetting storage."""
        goto_step = request.GET.get('step')

        # If we passed a specific step in the URL (?step=1) and it exists in our wizard
        if goto_step in self.steps.all:
            # Update the current step WITHOUT resetting the storage
            self.storage.current_step = goto_step
            # Return an unbound form. This ensures get_form_initial runs again
            # so the "Pending" badge updates to "Graded"!
            return self.render(self.get_form())

        # Default behavior for a normal GET request: wipe data and start fresh
        self.storage.reset()
        self.storage.current_step = self.steps.first
        return self.render(self.get_form())

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)

        if step == '1':
            data0 = self.get_cleaned_data_for_step('0')
            if not data0: return initial

            # Cari siapa aja yang udah punya nilai di session ini
            graded_student_ids = StudentBehaviourReport.objects.filter(
                behaviour__academic_year=data0['academic_year'],
                behaviour__period=data0['period'],
                behaviour__level=data0['level'],
                behaviour__is_mid=False
            ).values_list('student_id', flat=True).distinct()

            students = CourseMember.objects.filter(
                course=data0['kelas'],  # kelas now holds a Course instance
                is_active=True
            ).select_related('student')

            initial_list = []
            for member in students:
                initial_list.append({
                    'student': member.student.id,
                    'is_graded': member.student.id in graded_student_ids,  # Ini logic kuncinya
                    'is_active': member.is_active,
                })
            return initial_list
        return initial

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == '0':
            kwargs['user'] = self.request.user
        if step == '1':
            step0_data = self.get_cleaned_data_for_step('0')
            if step0_data and 'kelas' in step0_data:
                kwargs['kelas'] = step0_data['kelas']
            # Pass form_kwargs_list for each form in the formset
            initial = self.get_form_initial(step)
            kwargs['form_kwargs_list'] = [{'form_index': i} for i in range(len(initial))]
        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        if self.steps.current == '1':
            data_step0 = self.get_cleaned_data_for_step('0')
            if data_step0:
                context['selected_kelas'] = data_step0.get('kelas')  # actual selected Course instance

        if self.steps.current == '0':
            context['selected_acayear'] = AcademicYear.objects.all()
            context['selected_period'] = LearningPeriod.objects.all().select_related('academic_year')
            context['selected_kelas'] = Course.objects.all().select_related('subject')  # Course not Class
            context['selected_level'] = GradeLevel.objects.all()

        return context

    # def post(self, *args, **kwargs):
    #     """Handle the 'Back' button logic to delete data if going to step 0"""
    #     if self.request.POST.get('wizard_goto_step') == '0' and self.steps.current == '1':
    #         step0_data = self.get_cleaned_data_for_step('0')
    #         if step0_data:
    #             # Find the container
    #             behaviour = ReportcardBehaviour.objects.filter(
    #                 academic_year=step0_data.get('academic_year'),
    #                 period=step0_data.get('period'),
    #                 level=step0_data.get('level'),
    #                 is_mid=False
    #             ).first()
    #
    #             if behaviour:
    #                 # Delete all reports associated with this specific behavior grading session
    #                 # This acts as the 'Undo' logic for the Back button
    #                 StudentBehaviourReport.objects.filter(behaviour=behaviour).delete()
    #                 messages.info(self.request, "Previous grading progress cleared.")

        return super().post(*args, **kwargs)

    def done(self, form_list, **kwargs):
        form_data_0 = form_list[0].cleaned_data

        # 1. Safely get or create the Behaviour container
        # (Just in case they clicked 'Submit' without grading anyone yet)
        behaviour, created = ReportcardBehaviour.objects.get_or_create(
            academic_year=form_data_0['academic_year'],
            period=form_data_0['period'],
            level=form_data_0['level'],
            is_mid=False
        )

        # 2. DO NOT create score=0 entries here if the individual
        # grading view is already handling the database saves!
        # We can just leave this empty, or use it to mark the class as "Finalized"
        # if you have a status field on ReportcardBehaviour.

        # 3. Add a success message
        messages.success(self.request, "Class behavior grading has been finalized!")

        # 4. Redirect to wherever you want them to go next
        # (e.g., the main gradebook index or a specific table)
        return redirect('rubric-entry')


def get_kelas_rubric(request):
    teacher_id = request.GET.get('0-teacher') or request.GET.get('teacher')
    selected_kelas = request.GET.get('0-kelas') or request.GET.get('kelas')
    if teacher_id:
        classes = Course.objects.filter(teacher_id=teacher_id).select_related('subject')
    else:
        classes = Course.objects.none()
    return render(request, "partials/gradebook/gradeentry_partials/kelas.html", {
        'kelas_list': classes,  # ← match the template's variable name
        'selected_kelas': selected_kelas
    })

# def get_kelas_rubric(request):
#     rubric.existing_score = existing_scores.get(rubric.id, None)
#
#     # Process form submission
#
#
#     if request.method == 'POST':
#         # 1. Ensure the container exists
#         if academic_year and period and level:
#             behaviour_obj, _ = ReportcardBehaviour.objects.get_or_create(
#                 academic_year=academic_year,
#                 period=period,
#                 level=level,
#                 is_mid=False
#             )
#
#             # 2. Save each score from the radio buttons
#             for rubric in rubrics:
#                 score_val = request.POST.get(f'rubric_{rubric.id}')
#                 if score_val:
#                     StudentBehaviourReport.objects.update_or_create(
#                         student=student,
#                         behaviour=behaviour_obj,
#                         rubric=rubric,
#                         defaults={'score': int(score_val)}
#                     )
#
#         # 3. Manually set wizard back to Step 1 (the table screen)
#         wizard_key = 'wizard_rubric_entry_wizard'
#
#         if wizard_key in request.session:
#             data = request.session[wizard_key]
#             data['step'] = '1'
#             request.session[wizard_key] = data
#             request.session.modified = True
#
#             return redirect('rubric-entry')
#
#     context = {
#                   'student': student,
#     }


@login_required
def student_behavior_grading(request, pk):
    try:
        student = Student.objects.select_related('registration_data').get(pk=pk)
    except Student.DoesNotExist:
        return HttpResponse("Student not found", status=404)

    # NAMA KEY HARUS SAMA: Sesuai nama class Wizard (snake_case)
    # Jika class: RubricEntryWizard -> key: wizard_rubric_entry_wizard
    wizard_key = 'wizard_rubric_entry_wizard'
    wizard_data = request.session.get(wizard_key, {})
    step_data = wizard_data.get('step_data', {}).get('0', {})

    # Helper buat ambil ID dari session (karena formatnya list: ['2'])
    def get_id(field):
        val = step_data.get(f'0-{field}')
        return val[0] if isinstance(val, list) and val else val

    ay_id = get_id('academic_year')
    p_id = get_id('period')
    l_id = get_id('level')

    # Ambil object untuk context template
    academic_year = AcademicYear.objects.filter(pk=ay_id).first()
    period = LearningPeriod.objects.filter(pk=p_id).first()
    level = GradeLevel.objects.filter(pk=l_id).first()

    # Ambil rubrik
    rubrics = list(Rubric.objects.all())

    # Ambil teks narasi
    desc = ReportcardRubricTemplate.objects.values_list('text', flat=True)

    # Ambil container Behaviour
    behaviour, _ = ReportcardBehaviour.objects.get_or_create(
        academic_year=academic_year,
        period=period,
        level=level,
        is_mid=False
    )

    # LOGIC SIMPAN (POST) - Ini yang tadi kamu belum ada:
    if request.method == 'POST':
        for rubric in rubrics:
            score = request.POST.get(f'rubric_{rubric.id}')
            if score:
                # Simpan atau update nilai per rubrik
                StudentBehaviourReport.objects.update_or_create(
                    student=student,
                    behaviour=behaviour,
                    rubric=rubric,
                    defaults={'score': int(score)}
                )

        # Redirect balik ke wizard step 1
        url = reverse('rubric-entry')
        return HttpResponseRedirect(f"{url}?step=1")

    # Ambil nilai yang sudah ada buat ditampilin di form
    existing_scores = {r.rubric_id: r.score for r in
                       StudentBehaviourReport.objects.filter(student=student, behaviour=behaviour)}
    for rubric in rubrics:
        rubric.existing_score = existing_scores.get(rubric.id)



    context = {
        'student': student,
        'academic_year': academic_year,
        'period': period,
        'level': level,
        'rubrics': rubrics,
    }
    return render(request, 'partials/gradebook/rubric_entry_behav_notes.html', context)



@login_required
def rb_table(request):
    user = request.user
    teacher = Teacher.objects.filter(user=user).first()

    order_field, sort_by, sort_dir = get_sort_params(request, {
        'academic_year': 'academic_year__year',
        'period': 'period__period_name',
        'is_mid': 'is_mid',
        'level': 'level__grade_name',
    }, default_sort='academic_year')

    rb = ReportcardBehaviour.objects.select_related(
        'academic_year', 'period', 'level'
    )

    # restrict to sessions relevant to this teacher's classes, if not staff
    if teacher and not user.is_staff:
        rb = rb.filter(
            level__students_level_reportcard_behaviour__isnull=False
        ).distinct()

    rb = apply_filters(rb, request, {
        'year': 'academic_year_id',
        'period': 'period_id',
        'level': 'level_id',
    })

    search_query = request.GET.get('q', '')
    if search_query:
        rb = rb.filter(
            Q(academic_year__year__icontains=search_query) |
            Q(period__period_name__icontains=search_query) |
            Q(level__grade_name__icontains=search_query)
        )

    rb = rb.order_by(order_field).distinct()

    pnation = Paginator(rb, 15)
    pnation_rb = pnation.get_page(request.GET.get('page'))

    return render(request, 'partials/gradebook/rubric_table.html', {
        'pnation_rb': pnation_rb,
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'search_query': search_query,
        'extra_filters': [
            {
                'label': 'Academic Year',
                'param': 'year',
                'options': AcademicYear.objects.all(),
                'selected': request.GET.get('year', ''),
            },
            {
                'label': 'Period',
                'param': 'period',
                'options': LearningPeriod.objects.filter(period_name__icontains='semester'),
                'selected': request.GET.get('period', ''),
            },
            {
                'label': 'Level',
                'param': 'level',
                'options': GradeLevel.objects.all(),
                'selected': request.GET.get('level', ''),
            },
        ],
    })

@login_required
def rb_edit(request, pk):
    behaviour = get_object_or_404(
        ReportcardBehaviour.objects.select_related('academic_year', 'period', 'level'),
        pk=pk
    )

    queryset = StudentBehaviourReport.objects.filter(
        behaviour=behaviour
    ).select_related('student__registration_data', 'rubric').order_by('student__id', 'rubric__id')

    BehaviourFormSet = modelformset_factory(
        StudentBehaviourReport,
        fields=('score', 'description'),
        extra=0,
    )

    if request.method == 'POST':
        formset = BehaviourFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            log_activity(request.user, behaviour, 'change', "Updated student behaviour grades")
            messages.success(request, "Behaviour grades updated successfully!")
            return redirect('rubric-table')
    else:
        formset = BehaviourFormSet(queryset=queryset)

    # pair each form with its underlying instance for template display
    rows = list(zip(formset.forms, queryset))

    return render(request, 'partials/gradebook/rubric_edit.html', {
        'formset': formset,
        'rows': rows,
        'behaviour': behaviour,
    })

# pls github i need this

# EXTRA REPORT FORM LOGIC
class ExtraReportWizard(LoginRequiredMixin, SessionWizardView):
    template_name = "partials/gradebook/report_extra.html"

    form_list = [
        ("0", ExtraGradeItemForm),
        ("1", ExtraGradeFormSet),
    ]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == '0':
            kwargs['user'] = self.request.user
        return kwargs

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)

        if step == '1':
            data0 = self.get_cleaned_data_for_step('0')
            if not data0:
                return initial

            kelas = data0.get('kelas')
            if not kelas:
                return initial

            act_subj = data0.get('subject')

            members = CourseMember.objects.filter(
                course=kelas,
                is_active=True,
            ).select_related('student__registration_data')

            initial_list = []
            for member in members:
                student = member.student
                initial_list.append({
                    'student_id': student.id,
                    'student_nisn': student.nisn,
                    'student_name': f"{student.registration_data.first_name} {student.registration_data.last_name}",
                    'extra_score': 0,
                    'extra_description': '',
                    'extra_notes': '',
                })
            return initial_list

        return initial

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        data0 = self.get_cleaned_data_for_step('0')
        if data0:
            context['selected_kelas'] = data0.get('kelas')
            context['selected_act_subj'] = data0.get('act_subj')
            context['selected_period'] = data0.get('period')
            context['selected_academic_year'] = data0.get('academic_year')

        return context

    def done(self, form_list, **kwargs):
        data0 = form_list[0].cleaned_data
        formset = form_list[1]

        academic_year = data0['academic_year']
        period = data0['period']
        level = data0['level']
        act_subj = data0['act_subj']

        # Determine extra_type from act_subj's is_activity flag
        # (adjust this logic if you have a more specific mapping)
        extra_type = "EK"  # default to Ekstrakurikuler

        with transaction.atomic():
            for form in formset:
                if form.is_valid() and form.cleaned_data:
                    data = form.cleaned_data
                    student_id = data.get('student_id')

                    reportcard, _ = StudentReportcard.objects.get_or_create(
                        student_id=student_id,
                        academic_year=academic_year,
                        period=period,
                        is_mid=False,
                        defaults={'level': level}
                    )

                    StudentReportExtra.objects.update_or_create(
                        reportcard=reportcard,
                        extra_type=extra_type,
                        defaults={
                            'extra_description': data.get('extra_description', ''),
                            'extra_score': data.get('extra_score', 0),
                            'extra_notes': data.get('extra_notes', ''),
                        }
                    )

        messages.success(self.request, "Extracurricular grades saved successfully!")
        return redirect('extra-report')


@login_required
def student_act_extra_grading(request, pk):
    """View for grading individual student behavior using rubrics and indicators"""
    try:
        student = Student.objects.select_related('registration_data').get(pk=pk)
    except Student.DoesNotExist:
        return HttpResponse("Student not found", status=404)

    # Get data from the first step of the Rubric Entry form (from session)
    wizard_key = 'wizard_rubric_entry_wizard'
    wizard_data = request.session.get(wizard_key, {})
    step_data = wizard_data.get('step_data', {})
    step0_data = step_data.get('0', {})

    # Helper to extract PK from raw wizard session data
    def get_pk_from_step0(key, fallback=None):
        # 1. Add the step prefix to the key (e.g., '0-academic_year')
        prefixed_key = f'0-{key}'
        val = step0_data.get(prefixed_key)

        # 2. Extract the string from the list if it's stored as a list
        if isinstance(val, list) and val:
            val = val[0]

        # 3. Return the string ID if it exists
        if val:
            return val

        return fallback

    academic_year_id = get_pk_from_step0('academic_year', request.GET.get('academic_year'))
    period_id = get_pk_from_step0('period', request.GET.get('period'))
    level_id = get_pk_from_step0('level', request.GET.get('level'))

    academic_year = None
    period = None
    level = None
    try:
        if academic_year_id:
            academic_year = AcademicYear.objects.get(pk=academic_year_id)
        if period_id:
            period = LearningPeriod.objects.get(pk=period_id)
        if level_id:
            level = GradeLevel.objects.get(pk=level_id)
    except (AcademicYear.DoesNotExist, LearningPeriod.DoesNotExist, GradeLevel.DoesNotExist):
        academic_year = period = level = None

    # Get all rubrics for this academic year (both Spiritual and Social)
    activities = Subject.objects.filter(is_activity=True)

    # 1. Fetch the Behaviour container if it already exists
    behaviour = None
    if academic_year and period and level:
        behaviour = ReportcardBehaviour.objects.filter(
            academic_year=academic_year,
            period=period,
            level=level,
            is_mid=False
        ).first()

    # 2. Get all rubrics (convert to list so we can inject temporary attributes)
    activities = list(Subject.objects.filter(is_activity=True))

    # 3. Create a dictionary of existing scores {rubric_id: score}
    existing_scores = {}
    if behaviour:
        reports = StudentBehaviourReport.objects.filter(student=student, behaviour=behaviour)
        for report in reports:
            existing_scores[report.rubric_id] = report.score

        # # 4. Attach the existing score directly to each rubric object
        # for activity in activities:
        #     # This creates a temporary 'existing_score' attribute for the template
        #     rubric.existing_score = existing_scores.get(rubric.id, None)

        # Process form submission
        if request.method == 'POST':
            # --- NEW SAVING LOGIC START ---

            # 1. Ensure the ReportcardBehaviour container exists
            if academic_year and period and level:
                behaviour, created = ReportcardBehaviour.objects.get_or_create(
                    academic_year=academic_year,
                    period=period,
                    level=level,
                    is_mid=False
                )

                # 2. Loop through rubrics and save the submitted scores
                # for rubric in rubrics:
                #     # Look for the input name we define in the HTML (e.g., 'rubric_1', 'rubric_2')
                #     score_val = request.POST.get(f'rubric_{rubric.id}')
                #
                #     if score_val:  # Only save if a value was actually typed in
                #         try:
                #             score_int = int(score_val)
                #             # Save or update the individual student's score
                #             StudentBehaviourReport.objects.update_or_create(
                #                 student=student,
                #                 behaviour=behaviour,
                #                 rubric=rubric,
                #                 defaults={'score': score_int}
                #             )
                # except ValueError:
                #     # Ignore if they somehow bypassed frontend validation and submitted text
                #     pass
                # --- NEW SAVING LOGIC END ---

        # 3. Define the wizard's session key
        wizard_key = 'wizard_rubric_entry_wizard'

        # 4. Update the session to set the current step back to '1'
        if wizard_key in request.session:
            data = request.session[wizard_key]
            data['step'] = '1'
            request.session[wizard_key] = data
            request.session.modified = True

        # 5. Add success message
        messages.success(request, f"Behavior grades successfully saved for {student}!")

        # 6. Redirect back to the Wizard instead of rendering a raw partial
        return redirect('rubric-entry')

    context = {
        'student': student,
        'academic_year': academic_year,
        'period': period,
        'level': level,
        'activities': activities,
        # 'score_choices' is no longer needed since we are using a textbox
    }
    return render(request, 'partials/gradebook/report_extra_extrac_grade.html', context)


def student_act_other_grading(request, pk):
    """View for grading individual student behavior using rubrics and indicators"""
    try:
        student = Student.objects.select_related('registration_data').get(pk=pk)
    except Student.DoesNotExist:
        return HttpResponse("Student not found", status=404)

    # Get data from the first step of the Rubric Entry form (from session)
    wizard_key = 'wizard_rubric_entry_wizard'
    wizard_data = request.session.get(wizard_key, {})
    step_data = wizard_data.get('step_data', {})
    step0_data = step_data.get('0', {})

    # Helper to extract PK from raw wizard session data
    def get_pk_from_step0(key, fallback=None):
        # 1. Add the step prefix to the key (e.g., '0-academic_year')
        prefixed_key = f'0-{key}'
        val = step0_data.get(prefixed_key)

        # 2. Extract the string from the list if it's stored as a list
        if isinstance(val, list) and val:
            val = val[0]

        # 3. Return the string ID if it exists
        if val:
            return val

        return fallback

    academic_year_id = get_pk_from_step0('academic_year', request.GET.get('academic_year'))
    period_id = get_pk_from_step0('period', request.GET.get('period'))
    level_id = get_pk_from_step0('level', request.GET.get('level'))

    academic_year = None
    period = None
    level = None
    try:
        if academic_year_id:
            academic_year = AcademicYear.objects.get(pk=academic_year_id)
        if period_id:
            period = LearningPeriod.objects.get(pk=period_id)
        if level_id:
            level = GradeLevel.objects.get(pk=level_id)
    except (AcademicYear.DoesNotExist, LearningPeriod.DoesNotExist, GradeLevel.DoesNotExist):
        academic_year = period = level = None

    # Get all rubrics for this academic year (both Spiritual and Social)
    rubrics = Rubric.objects.all()

    # 1. Fetch the Behaviour container if it already exists
    behaviour = None
    if academic_year and period and level:
        behaviour = ReportcardBehaviour.objects.filter(
            academic_year=academic_year,
            period=period,
            level=level,
            is_mid=False
        ).first()

    # 2. Get all rubrics (convert to list so we can inject temporary attributes)
    rubrics = list(Rubric.objects.all())

    # 3. Create a dictionary of existing scores {rubric_id: score}
    existing_scores = {}
    if behaviour:
        reports = StudentBehaviourReport.objects.filter(student=student, behaviour=behaviour)
        for report in reports:
            existing_scores[report.rubric_id] = report.score

        # 4. Attach the existing score directly to each rubric object
        for rubric in rubrics:
            # This creates a temporary 'existing_score' attribute for the template
            rubric.existing_score = existing_scores.get(rubric.id, None)

        # Process form submission
        if request.method == 'POST':
            # --- NEW SAVING LOGIC START ---

            # 1. Ensure the ReportcardBehaviour container exists
            if academic_year and period and level:
                behaviour, created = ReportcardBehaviour.objects.get_or_create(
                    academic_year=academic_year,
                    period=period,
                    level=level,
                    is_mid=False
                )

                # 2. Loop through rubrics and save the submitted scores
                for rubric in rubrics:
                    # Look for the input name we define in the HTML (e.g., 'rubric_1', 'rubric_2')
                    score_val = request.POST.get(f'rubric_{rubric.id}')

                    if score_val:  # Only save if a value was actually typed in
                        try:
                            score_int = int(score_val)
                            # Save or update the individual student's score
                            StudentBehaviourReport.objects.update_or_create(
                                student=student,
                                behaviour=behaviour,
                                rubric=rubric,
                                defaults={'score': score_int}
                            )
                        except ValueError:
                            # Ignore if they somehow bypassed frontend validation and submitted text
                            pass
                            # --- NEW SAVING LOGIC END ---

            # 3. Define the wizard's session key
            wizard_key = 'wizard_rubric_entry_wizard'

            # 4. Update the session to set the current step back to '1'
            if wizard_key in request.session:
                data = request.session[wizard_key]
                data['step'] = '1'
                request.session[wizard_key] = data
                request.session.modified = True

            # 5. Add success message
            messages.success(request, f"Behavior grades successfully saved for {student}!")

            # 6. Redirect back to the Wizard instead of rendering a raw partial
            return redirect('rubric-entry')

    context = {
        'student': student,
        'academic_year': academic_year,
        'period': period,
        'level': level,
        'rubrics': rubrics,
        # 'score_choices' is no longer needed since we are using a textbox
    }
    return render(request, 'partials/gradebook/report_extra_other_grade.html', context)





def get_period_extra(request):
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')
    teacher_id = request.GET.get('0-teacher') or request.GET.get('1-teacher') or request.GET.get('teacher')
    # period = LearningPeriod.objects.filter(academic_year_id=acayear_id, period_name__icontains='semester')
    if acayear_id:
        period = LearningPeriod.objects.filter(academic_year_id=acayear_id, period_name__icontains='semester')
    else:
        period = LearningPeriod.objects.none()
    context = {'period': period}
    # return render(request, "partials/gradebook/totalgrade_partials/period.html", context)

    return render(request, "partials/gradebook/reportextra_partials/period.html", {'periods': period})

def get_teachers_extra(request):
    period_id = request.GET.get('0-period') or request.GET.get('period')
    user = request.user

    if period_id:
        teachers = Teacher.objects.filter(user=user).all()
        if user.is_staff:
            teachers = Teacher.objects.all()
    else:
        teachers = Teacher.objects.none()
    context = {'teachers': teachers}
    return render(request, "partials/gradebook/reportextra_partials/teacher.html", context)

def get_kelas_extra(request):
    teacher_id = request.GET.get('0-teacher') or request.GET.get('teacher')
    selected_kelas = request.GET.get('0-kelas') or request.GET.get('kelas')
    if teacher_id:
        # Filter classes where the teacher is the homeroom teacher
        classes = Course.objects.filter(is_activity=True, teacher=teacher_id)
    else:
        classes = Course.objects.none()
    context = {
        'classes': classes,
        'selected_kelas': selected_kelas
    }

    return render(request, "partials/gradebook/reportextra_partials/kelas.html", context)


def get_level_extra(request):
    levels = GradeLevel.objects.all()
    context = {'levels': levels}
    return render(request, "partials/gradebook/reportextra_partials/level.html", context)


def get_act_subj(request):
    kelas_id = request.GET.get('0-kelas') or request.GET.get('kelas')
    selected_extra_info = request.GET.get('0-subject') or request.GET.get('subject')
    selected_course = request.GET.get('0-course') or request.GET.get('course')
    if kelas_id:
        # Filter classes where the teacher is the homeroom teacher
        subject = Subject.objects.filter(
            course__id=kelas_id,
            is_activity=True
        )
    else:
        subject = Subject.objects.none()
    context = {
        'extra_info': subject,
        'selected_extra_info': selected_extra_info
    }

    return render(request, "partials/gradebook/reportextra_partials/act_subj.html", context)


class TotalGrading(LoginRequiredMixin, SessionWizardView):
    template_name = "partials/gradebook/total_grade.html"

    form_list = [
        ("0", TotalGradesForm),
        ("1", TotalGradesFormSet)
    ]

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)

        if step == '1':
            step0_data = self.get_cleaned_data_for_step('0')
            if step0_data:
                period = step0_data.get('period')
                
                # Query StudentReportcard filtered by the selected period
                student_rc = StudentReportcard.objects.filter(
                    period=period
                ).select_related('student', 'student__registration_data')

                initial_list = []
                for rc in student_rc:
                    initial_list.append({
                        'student': rc.student.id,
                        # The student_name and student_nisn fields in TotalGradesTestList
                        # will be populated by the form's __init__ logic using this ID
                    })
                
                # Ensure we return the list for the formset
                return initial_list

        return initial

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == '1':
            # Pass form_kwargs_list for each form in the formset
            initial = self.get_form_initial(step)
            kwargs['form_kwargs_list'] = [{'form_index': i} for i in range(len(initial))]
            # Pass the current user to each individual form in the formset
            kwargs['form_kwargs'] = {'user': self.request.user}
        
        if step == '0':
            kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        if self.steps.current == '1':
            data_step0 = self.get_cleaned_data_for_step('0')
            if data_step0:
                context['selected_period'] = data_step0.get('period')

        if self.steps.current == '0':
            acayear = AcademicYear.objects.all()
            period = LearningPeriod.objects.all().select_related('academic_year')
            subject = Subject.objects.all()
            context['selected_acayear'] = acayear
            context['selected_period'] = period
            context['selected_subject'] = subject

        return context



    def done(self, form_list, **kwargs):
        form_data = form_list[0].cleaned_data

        academic_year = form_data.get('academic_year')
        level = form_data.get('level')
        kelas = form_data.get('kelas')
        subject = form_data.get('subject')
        is_mid = form_data.get('is_mid')  # Boolean

        # 1. Grab weightings filtered by is_mid — this is the key isolation
        weightings = Weighting.objects.filter(
            academic_year=academic_year,
            level=level,
            subject=subject,
            is_mid=is_mid,  # <-- only mid OR final weights, never both
        ).select_related('assignment')

        # 2. Determine date boundary so mid scores don't bleed into final and vice versa
        period = LearningPeriod.objects.filter(academic_year=academic_year).first()
        if is_mid:
            date_filter = {'assignment_head__date__lte': period.midterm_end_date}
        else:
            date_filter = {'assignment_head__date__gt': period.midterm_end_date}

        # 3. Students scoped to the selected kelas AND subject
        students = Student.objects.filter(
            coursemember__course__subject=subject,
            coursemember__course__academic_year=academic_year,
            coursemember__course__level=level,
            coursemember__course=kelas,  # ties to the specific class instance
            coursemember__is_active=True,
        ).distinct()

        student_results = []

        for student in students:
            total_weighted_avg = 0.0
            per_type_breakdown = []  # optional: useful for debugging in template

            for weighting in weightings:
                avg_result = AssignmentDetail.objects.filter(
                    student=student,
                    assignment_head__course__subject=subject,
                    assignment_head__course__level=level,
                    assignment_head__assignment=weighting.assignment,
                    is_active=True,
                    **date_filter,  # mid or final boundary applied here
                ).aggregate(avg=Avg('score'))['avg']

                avg_score = float(avg_result) if avg_result is not None else 0.0

                # weight is stored as 0.70 (not 70), so multiply directly
                contribution = avg_score * float(weighting.weight)
                total_weighted_avg += contribution

                per_type_breakdown.append({
                    'assignment_type': weighting.assignment,
                    'weight': weighting.weight,
                    'avg_score': round(avg_score, 2),
                    'contribution': round(contribution, 2),
                })

            student_results.append({
                'nisn': getattr(student, 'nisn', '-'),
                'student_name': str(student),
                'kelas': kelas,
                'subject': subject,
                'weighted_avg': round(total_weighted_avg, 2),
                'final_score': round(total_weighted_avg),  # int, ready for ReportcardGrade
                'breakdown': per_type_breakdown,
            })

        context = {
            'student_results': student_results,
            'selected_academic_year': academic_year,
            'selected_subject': subject,
            'selected_kelas': kelas,
            'selected_level': level,
            'is_mid': is_mid,
            'weightings': weightings,  # handy for rendering table headers
            'period': period,
        }



        return render(self.request, "partials/gradebook/assignment_avg_result.html", context)


def get_subject_totalg(request):
    subject_id = request.GET.get('subject_id')
    if subject_id:
        subject = Subject.objects.all()
    else:
        subject = Subject.objects.none()

    return render(request, "partials/gradebook/totalgrade_partials/subject.html", {'subject': subject})


def get_academic_year_totalg(request):
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')
    selected_subject = request.GET.get('0-subject') or request.GET.get('subject')
    if selected_subject:
        acayear_id = AcademicYear.objects.all()
    else:
        acayear_id = AcademicYear.objects.none()

    return render(request, "partials/gradebook/totalgrade_partials/academic_year.html", {'periods': periods})


def get_period_tgrade(request):
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')
    period = LearningPeriod.objects.filter(academic_year_id=acayear_id, period_name__icontains='semester')
    context = {'period': period}
    return render(request, "partials/gradebook/totalgrade_partials/period.html", context)


def assignm_avg(request):
    user = request.user
    teach = Teacher.objects.filter(user=user).first()
    avg = AssignmentDetail.objects.filter(assignment_head__course__teacher=teach).aggregate(Avg('score'))
    # weight = Weighting.objects.filter(assignment_head__course__teacher=teach) bwt weighting ntar aja
    context = {
        'avg' : avg
    }
    return render(request, "partials/gradebook/allassignm_avg.html", context)


import json
from django.core.serializers.json import DjangoJSONEncoder

# KALKULASI NILAI AKHIR (UTS & UAS)
def calculate_student_averages_optimized(academic_year, subject, level, is_mid, period):
    # 1. AMBIL BOBOT NILAI YANG AKTIF
    weightings = Weighting.objects.filter(academic_year=academic_year, level=level, subject=subject, period=period,
                                          is_mid=is_mid)
    weight_map = {w.assignment_id: float(w.weight) for w in weightings}

    assign_type_map = {
        at.id: at
        for at in AssignmentType.objects.filter(id__in=weight_map.keys())
    }

    if not weight_map:
        return [], None

    # 2. TENTUKAN RENTANG TANGGAL PERIODE (TERM / SEMESTER)
    terms = LearningPeriod.objects.filter(academic_year=academic_year, date_start__lte=period.date_end,
                                          date_end__gte=period.date_start, period_name__icontains='term').order_by('date_start')

    # print("============= DEBUG TANGGAL =============")
    # print(f"Periode yang dicek: {period.period_name}")
    # print(f"Academic Year: {academic_year}")
    # print(f"Start: {period.date_start}, End: {period.date_end}")
    # print(f"Hasil Query 'terms': {terms}")
    # print("=========================================")

    term_period = terms.first() if is_mid else terms.last()
    term_period = term_period or period

    # 3. AMBIL RATA-RATA NILAI TUGAS MURID LANGSUNG DARI DB
    grades_data = AssignmentDetail.objects.filter(
        assignment_head__course__subject=subject,
        assignment_head__course__academic_year=academic_year,
        assignment_head__assignment_id__in=weight_map.keys(),
        assignment_head__date__range=(term_period.date_start, term_period.date_end)
    ).values('student_id', 'assignment_head__assignment_id').annotate(avg_score=Avg('score'))

    all_terms = list(terms)

    all_individual_scores = AssignmentDetail.objects.filter(
        assignment_head__course__subject=subject,
        assignment_head__course__academic_year=academic_year,
        assignment_head__assignment_id__in=weight_map.keys(),
        assignment_head__date__range=(term_period.date_start, term_period.date_end)
    ).select_related(
        'assignment_head__assignment',
        'assignment_head'
    ).values(
        'student_id',
        'score',
        'assignment_head__topic',
        'assignment_head__date',
        'assignment_head__assignment__short_name',
        'assignment_head__assignment__name',
    )

    # group by student_id in Python — O(n) dict lookup, zero extra queries
    from collections import defaultdict
    scores_by_student = defaultdict(list)
    for row in all_individual_scores:
        scores_by_student[row['student_id']].append({
            'topic': row['assignment_head__topic'],
            'date': row['assignment_head__date'],
            'type': row['assignment_head__assignment__short_name'],
            'type_name': row['assignment_head__assignment__name'],
            'score': float(row['score']),
        })

    # 4. KHUSUS AKHIR SEMESTER (UAS): TARIK NILAI UTS (30%) DARI DB
    uts_scores = {}
    uts_weight = 0.0

    if not is_mid:
        # Ambil bobot UTS-nya
        uts_w_obj = Weighting.objects.filter(academic_year=academic_year, level=level, subject=subject, period=period,
                                             is_mid=True, assignment__short_name='SUMM').first()
        if uts_w_obj:
            uts_weight = float(uts_w_obj.weight) / 100.0 if float(uts_w_obj.weight) > 1 else float(uts_w_obj.weight)

        # Ambil semua nilai rapot UTS yang dulu pernah di-save
        uts_grades = ReportcardGrade.objects.filter(reportcard__academic_year=academic_year, reportcard__period=period,
                                                    reportcard__is_mid=True, subject=subject)
        uts_scores = {g.reportcard.student_id: float(g.final_score) for g in uts_grades}

    # 5. HITUNG TOTAL NILAI AKHIR PER MURID
    student_records = {}
    for row in grades_data:
        s_id = row['student_id']
        score = float(row['avg_score'] or 0)
        weight = weight_map.get(row['assignment_head__assignment_id'], 0)

        if s_id not in student_records:
            student_records[s_id] = {'raw_sum': 0, 'count': 0, 'weighted_sum': 0.0}

        student_records[s_id]['raw_sum'] += score
        student_records[s_id]['count'] += 1
        student_records[s_id]['weighted_sum'] += (score * weight)

    # 6. BUNGKUS HASIL AKHIR UNTUK DITAMPILKAN KE LAYAR
    results = []
    students = {s.id: s for s in Student.objects.filter(id__in=student_records.keys())}

    for s_id, record in student_records.items():
        student_obj = students.get(s_id)
        if not student_obj: continue

        raw_avg = record['raw_sum'] / record['count'] if record['count'] > 0 else 0
        final_score = record['weighted_sum']

        # JIKA UAS: Tambahkan nilai UTS (Hasil kali Nilai UTS * 30%)
        if not is_mid:
            final_score += (uts_scores.get(s_id, 0.0) * uts_weight)

        # build breakdown list for display
        breakdown = []
        for assign_id, weight in weight_map.items():
            assign_type = assign_type_map.get(assign_id)
            type_avg = next(
                (float(r['avg_score']) for r in grades_data
                 if r['student_id'] == s_id
                 and r['assignment_head__assignment_id'] == assign_id),
                0.0
            )
            breakdown.append({
                'label': assign_type.short_name if assign_type else str(assign_id),
                'avg': round(type_avg, 2),
                'weight': weight,
                'weighted': round(type_avg * weight, 2),
            })

        # per-term breakdown — one entry per term
        term_breakdown = []
        for term in all_terms:
            term_grades = AssignmentDetail.objects.filter(
                assignment_head__course__subject=subject,
                assignment_head__course__academic_year=academic_year,
                assignment_head__assignment_id__in=weight_map.keys(),
                assignment_head__date__range=(term.date_start, term.date_end),
                student_id=s_id,
            ).values('assignment_head__assignment_id').annotate(avg_score=Avg('score'))

            term_rows = []
            for row in term_grades:
                assign_type = assign_type_map.get(row['assignment_head__assignment_id'])
                term_rows.append({
                    'label': assign_type.short_name if assign_type else '-',
                    'avg': round(float(row['avg_score'] or 0), 2),
                })

            term_breakdown.append({
                'term_name': term.period_name,
                'rows': term_rows,
            })

        # UTS entry for UAS breakdown
        uts_breakdown = None
        if not is_mid and uts_scores.get(s_id):
            uts_breakdown = {
                'score': uts_scores.get(s_id, 0.0),
                'weight': uts_weight,
                'weighted': round(uts_scores.get(s_id, 0.0) * uts_weight, 2),
            }

        results.append({
            'student_obj': student_obj,
            'student_name': str(student_obj),
            'nisn': getattr(student_obj, 'nisn', '-'),
            'subject': subject,
            'level': level,
            'raw_avg': raw_avg,
            'weighted_avg': final_score,
            'final_score_preview': round(final_score),
            'period': period,
            'breakdown': breakdown,
            'term_breakdown': term_breakdown,
            'uts_breakdown': uts_breakdown,
            'individual_scores': sorted(
                scores_by_student.get(s_id, []),
                key=lambda x: (x['type'], x['date'])
            ),
        })

    return results, term_period

# def calc_student_avg_redone(academic_year, subject, level, is_mid, period):
#     # bobot_formatif_sem_jalan = Weighting.objects.filter(
#     #         academic_year=academic_year,
#     #         level=level,
#     #         subject=subject,
#     #         period=period,
#     #         is_mid=is_mid
#     #     )
#     #
#     # bobot_sumatif_sem_akhir = Weighting.objects.filter(
#     #     academic_year=academic_year,
#     #     level=level,
#     #     subject=subject,
#     #     period=period,
#     #     is_mid=True,
#     #     assignment__short_name='SUMM'
#     # )
#     #
#     # selected_periods = LearningPeriod.objects.filter(
#     #     academic_year=academic_year,
#     #     date_start__lte=period.date_end,
#     #     date_end__gte=period.date_start
#     # )
#     #
#     #
#     # weight_map = {w.assignment_id: w.weight for w in bobot_formatif_sem_jalan}
#     # allowed_assignment_ids = list(weight_map.keys())
#     #
#     # if not allowed_assignment_ids:
#     #     return [], None
#     #
#     # # if not period:
#     # #     period = semester_periods.first()
#     #
#     # detail_qs = AssignmentDetail.objects.filter(
#     #     assignment_head__course__subject=subject,
#     #     assignment_head__course__academic_year=academic_year,
#     #     assignment_head__assignment_id__in=allowed_assignment_ids
#     # )
#     #
#     # # ========================================================
#     # # FIX 2: PENCARIAN TERM (DENGAN PENGECEKAN NULL)
#     # # ========================================================
#     # ordered_periods = selected_periods.order_by('date_start').filter(period_name__icontains='term')
#     #
#     # # Ambil periode, jika kosong gunakan periode default dari 'period'
#     # if ordered_periods.exists():
#     #     term_period = ordered_periods.first() if is_mid else ordered_periods.last()
#     # else:
#     #     term_period = period
#     #
#     #
#     #
#     # totals = Weighting.objects.aggregate(
#     #     sum1 = Sum('weight', filter=Q(academic_year=academic_year) & Q(level=level) & Q(subject=subject) & Q(period=period) & Q(is_mid=is_mid)),
#     #     sum2 = Sum('weight', filter=Q(academic_year=academic_year) & Q(level=level) & Q(subject=subject) & Q(period=period) & Q(is_mid=True) & Q(assignment__short_name='SUMM'))
#     # )
#     #
#     # grand_total = (totals['sum1'] or 0) + (totals['sum2'] or 0)
#     #
#     # # sum = bobot_formatif_sem_jalan + bobot_sumatif_sem_akhir
#     #
#     # results = 1 - grand_total
#     #
#     from decimal import Decimal
#     # return str(Decimal(results)), term_period
#
#     bobot_sem_jalan = Weighting.objects.filter(
#         academic_year=academic_year,
#         level=level,
#         subject=subject,
#         period=period,
#         is_mid=is_mid
#     )
#
#     weight_map = {w.assignment_id: w.weight for w in bobot_sem_jalan}
#     allowed_assignment_ids = list(weight_map.keys())
#
#     print(weight_map)
#
#     if not allowed_assignment_ids:
#         return [], None
#
#     # ========================================================
#     # 2. HITUNG SISA BOBOT UNTUK MID SEMESTER (Hasilnya 30%)
#     # ========================================================
#     # Kita totalin bobot yang aktif saat ini (Misal: 0.50 + 0.20 = 0.70)
#     current_total_weight = bobot_sem_jalan.aggregate(
#         weight_map=Sum('weight')
#     )['weight_map'] or Decimal('0.00')
#
#     # Cari sisanya (100% - Total Saat Ini)
#     # Catatan: Karena db lu pakai max_digits=2 (skala 0.00 - 0.99), 100% itu ditulis '1.0'
#     sisa_bobot = Decimal('1.0') - current_total_weight
#
#     # Pengaman biar nggak minus kalau kebetulan total bobotnya nyentuh/lebih dari 100%
#     if sisa_bobot < Decimal('0.00'):
#         sisa_bobot = Decimal('0.00')
#
#     # ========================================================
#     # 3. LANJUTAN LOGIKA QUERY DETAIL & TERM
#     # ========================================================
#     detail_qs = AssignmentDetail.objects.filter(
#         assignment_head__course__subject=subject,
#         assignment_head__course__academic_year=academic_year,
#         assignment_head__assignment_id__in=allowed_assignment_ids
#     )
#
#     selected_periods = LearningPeriod.objects.filter(
#         academic_year=academic_year,
#         date_start__lte=period.date_end,
#         date_end__gte=period.date_start
#     )
#
#     ordered_periods = selected_periods.order_by('date_start').filter(period_name__icontains='term')
#
#     # FIX 2: PENCARIAN TERM (DENGAN PENGECEKAN NULL)
#     if ordered_periods.exists():
#         term_period = ordered_periods.first() if is_mid else ordered_periods.last()
#     else:
#         term_period = period
#
#     # Mengembalikan nilai sisa bobot (str) dan term_period
#     return str(sisa_bobot), term_period


class AssignmentAvgWizard(LoginRequiredMixin, SessionWizardView):
    template_name = "partials/gradebook/assignment_avg.html"

    form_list = [
        ("0", AssignmentAvgForm),
    ]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == '0':
            kwargs['user'] = self.request.user
        return kwargs

    def done(self, form_list, **kwargs):
        form_data = form_list[0].cleaned_data

        academic_year = form_data.get('academic_year')
        level = form_data.get('level')
        # kelas = form_data.get('kelas')
        subject = form_data.get('subject')
        is_mid = form_data.get('is_mid')
        period = form_data.get('period')

        if period is None:
            semester_periods = LearningPeriod.objects.filter(
                academic_year=academic_year,
                period_name__icontains='Semester'
            ).order_by('date_start')
            # LANGSUNG ASSIGN KE PERIOD SUPAYA TIDAK NONE DI BAWAH
            period = semester_periods.first()

        # Tangkap 2 nilai: student_results dan decided_period
        # student_results, decided_period = calc_student_avg_redone(academic_year=academic_year,
        #                                                                        subject=subject, level=level,
        #                                                                        is_mid=is_mid, period=period)
        student_results, decided_period = calculate_student_averages_optimized(academic_year=academic_year,
                                                                               subject=subject, level=level,
                                                                               is_mid=is_mid, period=period)
        # print(academic_year)
        # print(level)
        # print(subject)
        # print(is_mid)
        # print(period)





        context = {
            'student_results': student_results,
            'selected_academic_year': academic_year,
            'selected_subject': subject,
            # 'selected_kelas': kelas,
            'selected_level': level,
            'selected_period': period,  # <--- SEKARANG ID-NYA PASTI ADA ISINYA
            'is_mid': is_mid,
        }

        # data = list(context.values())
        # print(json.dumps(data, indent=4, cls=DjangoJSONEncoder, default=str))

        return render(self.request, "partials/gradebook/assignment_avg_result.html", context)


@require_POST
def save_assignment_results(request):
    ay_id = request.POST.get('academic_year_id')
    sub_id = request.POST.get('subject_id')
    lvl_id = request.POST.get('level_id')
    period_id = request.POST.get('period_id')
    is_mid_str = request.POST.get('is_mid', 'False')
    is_mid = is_mid_str.lower() == 'true'

    # Validasi biar server lu aman dari crash kalau misal ke-skip
    if not period_id:
        messages.error(request, "Gagal. ID Periode tidak ditemukan dari template.")
        return redirect('assignment-avg-wizard')

    academic_year = AcademicYear.objects.get(id=ay_id)
    subject = Subject.objects.get(id=sub_id)
    level = GradeLevel.objects.get(id=lvl_id)
    period = LearningPeriod.objects.get(id=period_id)

    # Tangkap list muridnya aja di indeks [0]
    calculated_data = calculate_student_averages_optimized(academic_year=academic_year, subject=subject, level=level,
                                                           is_mid=is_mid, period=period)[0]

    # --- THE DUMP (Save to DB) ---
    with transaction.atomic():
        for data in calculated_data:
            student = data['student_obj']
            final_score_int = data['final_score_preview']

            reportcard, _ = StudentReportcard.objects.update_or_create(
                student=student,
                academic_year=academic_year,
                period=period,
                is_mid=is_mid,
                defaults={'level': level}
            )

            ReportcardGrade.objects.update_or_create(
                reportcard=reportcard,
                subject=subject,
                # defaults={
                #     'final_score': final_score_int,
                # }
                final_score=final_score_int
            )

    messages.success(request, f"Successfully saved grades for {subject.subject_name} ({period.period_name})!")
    return redirect('assignment-avg-wizard')


class GradesWizard(LoginRequiredMixin, SessionWizardView):
    template_name = "partials/gradebook/grades_wizard.html"

    form_list = [
        ("0", GradesSelectionForm),
        ("1", ReportCardGradeFormset),
    ]

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)

        if step == '1':
            # Get data from step 0
            step0_data = self.get_cleaned_data_for_step('0')
            if step0_data:
                academic_year = step0_data.get('academic_year')
                period = step0_data.get('period')
                level = step0_data.get('level')
                subject = step0_data.get('subject')
                is_mid = step0_data.get('is_mid')

                # Get students based on subject through courses
                if subject and academic_year:
                    # Get courses for this subject in this academic year
                    courses = Course.objects.filter(
                        subject=subject,
                        academic_year=academic_year
                    )
                    # Get students enrolled in these courses (active only)
                    students = Student.objects.filter(
                        coursemember__course__in=courses,
                        coursemember__is_active=True
                    ).distinct().order_by('id')

                    # For each student, create initial data
                    initial_list = []
                    for student in students:
                        initial_list.append({
                            'student_name': str(student),
                            'subject': subject.id if subject else None,
                            'subject_name': subject.subject_name if subject else '',
                            # Add other initials if needed
                        })
                    return initial_list
        return initial

    def post(self, *args, **kwargs):
        wizard_goto_step = self.request.POST.get('wizard_goto_step', None)
        if wizard_goto_step:
            # Skip current step validation entirely when navigating via Back button
            self.storage.current_step = wizard_goto_step
            return self.render(self.get_form())
        return super().post(*args, **kwargs)

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == '1':
            # For formset step, we need to pass initial data properly
            initial = self.get_form_initial(step)
            if initial:
                kwargs['initial'] = initial
        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        # Get cleaned data from step 0 if available
        step0_data = self.get_cleaned_data_for_step('0')
        if step0_data:
            context['selected_academic_year'] = step0_data.get('academic_year')
            context['selected_period'] = step0_data.get('period')
            context['selected_level'] = step0_data.get('level')
            context['selected_subject'] = step0_data.get('subject')
            context['selected_is_mid'] = step0_data.get('is_mid')

        return context

    def done(self, form_list, **kwargs):
        # Process the forms
        step0_data = form_list[0].cleaned_data
        step1_forms = form_list[1]

        academic_year = step0_data['academic_year']
        period = step0_data['period']
        level = step0_data['level']
        subject = step0_data['subject']
        is_mid = step0_data['is_mid']

        # Get students based on subject through courses
        courses = Course.objects.filter(
            subject=subject,
            academic_year=academic_year
        )
        students = list(Student.objects.filter(
            coursemember__course__in=courses,
            coursemember__is_active=True
        ).distinct().order_by('id'))

        # Create StudentReportcard for each student if not exists
        reportcards = {}
        for student in students:
            reportcard, created = StudentReportcard.objects.get_or_create(
                academic_year=academic_year,
                period=period,
                level=level,
                student=student,
                defaults={'is_mid': is_mid}
            )
            reportcards[student.id] = reportcard

        # Save the grades - assume order matches
        for form, student in zip(step1_forms, students):
            if form.is_valid() and form.cleaned_data:
                reportcard = reportcards[student.id]
                ReportcardGrade.objects.update_or_create(
                    reportcard=reportcard,
                    subject=subject,
                    defaults={
                        'final_score': form.cleaned_data.get('final_score'),
                        'final_grade': form.cleaned_data.get('final_grade'),
                        'teacher_notes': form.cleaned_data.get('teacher_notes'),
                    }
                )

        return HttpResponseRedirect('/gradebook/')


def get_period_grades(request):
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')
    if acayear_id:
        periods = LearningPeriod.objects.none()
    else:
        periods = LearningPeriod.objects.none()
    context = {
        'periods': periods,
    }
    return render(request, "partials/gradebook/gradeentry_partials/period.html", context)

def get_level_grades(request):
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')
    if acayear_id:
        levels = GradeLevel.objects.all()
    else:
        levels = GradeLevel.objects.none()
    context = {
        'levels': levels,
    }
    return render(request, "partials/gradebook/gradeentry_partials/period.html", context)


def get_period_assignment_avg(request):
    print(request.GET)
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')
    print(f"acayear_id: {acayear_id}")
    selected_period = request.GET.get('0-period') or request.GET.get('period')
    if acayear_id:
        # periods = LearningPeriod.objects.filter(academic_year_id=acayear_id)
        periods = LearningPeriod.objects.filter(academic_year=acayear_id, period_name__contains='semester').select_related('academic_year')
    else:
        periods = LearningPeriod.objects.none()
    html = render_to_string("partials/gradebook/assignment_avg_partials/period.html", {
        'periods': periods,
        'selected_period': selected_period
    })
    return HttpResponse(html)


def get_subjects_assignment_avg(request):
    # 1. Look at the ID badge of the person currently clicking the screen
    user = request.user

    # 2. Look up that person in the Teacher directory
    teacher = Teacher.objects.filter(user=user).first()

    level_id = request.GET.get('0-level') or request.GET.get('level')
    selected_subject = request.GET.get('0-subject') or request.GET.get('subject')

    # 3. Only search if a level is picked AND this person is actually a teacher
    if level_id:
        subjects = Subject.objects.all()
    else:
        subjects = Subject.objects.none()

    html = render_to_string("partials/gradebook/assignment_avg_partials/subject.html", {
        'subjects': subjects,
        'selected_subject': selected_subject
    })
    return HttpResponse(html)


def get_courses_assignment_avg(request):
    # 1. Get the logged-in teacher
    user = request.user
    teacher = Teacher.objects.filter(user=user).first()

    subject_id = request.GET.get('0-subject') or request.GET.get('subject')
    selected_kelas = request.GET.get('0-kelas') or request.GET.get('kelas')

    # 2. Filter classes by both Subject AND Teacher
    if subject_id:
        kelas = Class.objects.all()
    else:
        kelas = Class.objects.none()

    html = render_to_string("partials/gradebook/assignment_avg_partials/kelas.html", {
        'kelas': kelas,
        'selected_kelas': selected_kelas
    })
    return HttpResponse(html)

def print_grade_list(request, pk):
    parent_head = get_object_or_404(AssignmentHead, pk=pk)
    current_course = parent_head.course
    cpmp_trg = "\n".join(target.text for target in parent_head.cpmp_target.all())

    user = request.user
    date = datetime.now().strftime("%d %B %Y, %H:%M")

    # Same data sync as ge_edit
    active_members = CourseMember.objects.filter(course=current_course, is_active=True)
    for member in active_members:
        AssignmentDetail.objects.get_or_create(
            assignment_head=parent_head,
            student=member.student,
            defaults={'score': 0, 'is_active': True}
        )

    queryset = AssignmentDetail.objects.filter(
        assignment_head=parent_head
    ).order_by('student__id').select_related('student__registration_data')

    # ─── PAGE SETUP ───────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Times-Bold',
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Times-Roman',
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Times-Roman',
        alignment=TA_LEFT,
        spaceAfter=2,
    )

    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        leading=10,
    )

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=5,
        fontName='Times-Italic',
        alignment=TA_LEFT,
        textColor=colors.grey,
    )

    # ─── HEADER ───────────────────────────────────────────────
    flowables = []


    # Meta info table (topic, date, max score, course)
    meta_data = [
        ['Topic',       ':', str(parent_head.topic or '-')],
        ['Date',        ':', str(parent_head.date or '-')],
        ['Max Score',   ':', str(parent_head.max_score)],
        ['Assignment',  ':', str(parent_head.assignment.name)],
        ['Learning Target', ':', str(cpmp_trg or '-')],
        # ['Printed by', ':', str(user or '-')],
        # ['Printed on', ':', str(date or '-')],
    ]

    meta_table = Table(meta_data, colWidths=[3*cm, 0.5*cm, 12*cm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME',  (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE',  (0, 0), (-1, -1), 9),
        ('FONTNAME',  (0, 0), (0, -1),  'Times-Bold'),
        ('VALIGN',    (0, 0), (1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))


    flowables.append(meta_table)
    flowables.append(Spacer(1, 0.5*cm))


    # ─── STUDENT GRADE TABLE ──────────────────────────────────
    table_data = [
        ['#', 'ID Number', 'Student Name', 'Score', 'Status', 'Notes'],
    ]

    for i, detail in enumerate(queryset, start=1):
        student = detail.student
        reg = student.registration_data
        full_name = f"{reg.first_name or ''} {reg.last_name or ''}".strip()

        table_data.append([
            str(i),
            student.id_number,
            full_name,
            str(detail.score),
            'Active' if detail.is_active else 'Inactive',
            Paragraph(detail.na_reason or '-', cell_style)
        ])

    grade_table = Table(
        table_data,
        colWidths=[1*cm, 3*cm, 5*cm, 2*cm, 2*cm, 4*cm],
    )

    grade_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND',      (0, 0), (-1, 0),  colors.HexColor('#4a4a4a')),
        ('TEXTCOLOR',       (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',        (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',        (0, 0), (-1, 0),  9),
        ('ALIGN',           (0, 0), (-1, 0),  'CENTER'),

        # Body
        ('FONTNAME',        (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',        (0, 1), (-1, -1), 8),
        ('ALIGN',           (0, 0), (0, -1),  'CENTER'),   # # column
        ('ALIGN',           (3, 1), (4, -1),  'CENTER'),   # score + status
        ('ROWBACKGROUNDS',  (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),

        # Inactive rows — light red background
        *[
            ('BACKGROUND', (0, i+1), (-1, i+1), colors.HexColor('#ffe0e0'))
            for i, detail in enumerate(queryset)
            if not detail.is_active
        ],

        # Grid
        ('GRID',            (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX',             (0, 0), (-1, -1), 1,   colors.black),

        # Padding
        ('TOPPADDING',      (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',   (0, 0), (-1, -1), 5),
        ('LEFTPADDING',     (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',    (0, 0), (-1, -1), 6),
    ]))

    flowables.append(grade_table)
    flowables.append(Spacer(1, 15.0 * cm))
    flowables.append(Paragraph(f"Printed by {user} on {date}", footer_style))

    # ─── BUILD ────────────────────────────────────────────────
    doc.build(flowables)
    buf.seek(0)

    filename = f"grade_entry_{current_course.short_name}_{parent_head.date}.pdf"
    return FileResponse(buf, as_attachment=False, filename=filename)


class PersonalDevWizard(LoginRequiredMixin, SessionWizardView):
    template_name = 'partials/gradebook/personal_dev.html'

    form_list = [
        ('0', PersonalDevSelectForm),
        ('1', PersonalDevGradeForm),
    ]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)

        if step == '1':
            data0 = self.get_cleaned_data_for_step('0')
            if not data0:
                return kwargs  # bail out early if step 0 isn't filled yet

            student = data0.get('student')
            academic_year = data0.get('academic_year')
            period = data0.get('period')
            is_mid = data0.get('is_mid', False)

            if not all([student, academic_year, period]):
                kwargs['existing_instance'] = None
                return kwargs

            reportcard = StudentReportcard.objects.filter(
                student=0,
                academic_year=academic_year,
                period=period,
                is_mid=is_mid,
            ).first()

            existing = ReportcardPersonalDev.objects.filter(
                reporcard=reportcard,
            ).first() if reportcard else None

            kwargs['existing_instance'] = existing

        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        data0 = self.get_cleaned_data_for_step('0')
        if data0:
            context['selected_student'] = data0.get('student')
            context['selected_academic_year'] = data0.get('academic_year')
            context['selected_period'] = data0.get('period')
            context['selected_level'] = data0.get('level')
            context['selected_is_mid'] = data0.get('is_mid')

        if self.steps.current == '1':
            context['field_groups'] = {
                group_name: [form[field_name] for field_name in fields]
                for group_name, fields in PERSONAL_DEV_FIELDS.items()
            }

        # Pass the grouped field structure for the template to loop over
        # Easy to update — just edit PERSONAL_DEV_FIELDS in forms.py
        # context['field_groups'] = PERSONAL_DEV_FIELDS

        return context

    def post(self, *args, **kwargs):
        # Allow going back without current step validation
        wizard_goto_step = self.request.POST.get('wizard_goto_step', None)
        if wizard_goto_step:
            self.storage.current_step = wizard_goto_step
            return self.render(self.get_form())
        return super().post(*args, **kwargs)

    def done(self, form_list, **kwargs):
        data0 = form_list[0].cleaned_data
        data1 = form_list[1].cleaned_data
        student = data0['student']
        reportcard = data0['student']
        academic_year = data0['academic_year']
        period = data0['period']
        level = data0['level']
        is_mid = data0.get('is_mid', False)

        with transaction.atomic():
            # Get or create the reportcard
            # reportcard, _ = StudentReportcard.objects.get_or_create(
            #     # student=student,
            #     academic_year=academic_year,
            #     period=period,
            #     is_mid=is_mid,
            #     defaults={'level': level}
            # )

            # Build the grade data from the form
            grade_data = {
                field: form_list[1].cleaned_data[field]
                for field in form_list[1].cleaned_data
            }

            # update_or_create so re-submissions update rather than duplicate
            ReportcardPersonalDev.objects.update_or_create(
                reporcard=reportcard,
                defaults=grade_data
            )

        messages.success(self.request, f"Personal development grades saved for {student}!")
        return redirect('personal-dev')


def get_period_pd(request):
    acayear_id = (request.GET.get('0-academic_year')
                  or request.GET.get('1-academic_year')
                  or request.GET.get('academic_year'))
    selected_period = (request.GET.get('0-period')
                       or request.GET.get('1-period')
                       or request.GET.get('period'))

    periods = LearningPeriod.objects.filter(
        academic_year_id=acayear_id,
        period_name__icontains='semester'
    ) if acayear_id else LearningPeriod.objects.none()

    return render(request, "partials/gradebook/pdevelopment_partials/period.html", {
        'periods': periods,
        'selected_period': selected_period
    })



def get_levels_pd(request):
    # Check for the variable name sent by the 'academic_year' field
    # (Django form fields usually send '0-academic_year')
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')

    if acayear_id:
        # Load levels only if a year is selected
        levels = GradeLevel.objects.all()
    else:
        levels = GradeLevel.objects.none()

    context = {'levels': levels}
    # Use your existing folder structure
    return render(request, "partials/gradebook/pdevelopment_partials/level.html", context)

def get_kelas_pd(request):
    user = request.user
    teacher = Teacher.objects.filter(user=user).first()
    level_id = request.GET.get('0-level') or request.GET.get('level')
    selected_kelas = request.GET.get('0-kelas') or request.GET.get('kelas')
    if level_id:
        # Filter classes where the teacher is the homeroom teacher
        # classes = Class.objects.filter(teacher__id=teacher_id, is_home_class=True).distinct()
        classes = Class.objects.filter(teacher_id=user).distinct()
    else:
        classes = Class.objects.none()
    context = {
        'classes': classes,
        'selected_kelas': selected_kelas
    }
    return render(request, "partials/gradebook/pdevelopment_partials/kelas.html", context)


def get_student_pd(request):
    level_id = request.GET.get('0-level') or request.GET.get('level')
    is_mid_status = request.GET.get('0-is_mid') or request.GET.get('is_mid')
    is_mid = is_mid_status in ('on', 'True', 'true', '1')
    period_id = request.GET.get('0-period') or request.GET.get('period')

    student = StudentReportcard.objects.select_related('student').filter(
        is_mid=is_mid, period_id=period_id
    )
    context = {'students': student}
    return render(request, "partials/gradebook/pdevelopment_partials/student.html", context)

@login_required
def pdev_table(request):
    srpc = ReportcardPersonalDev.objects.select_related('reporcard')

    pnation = Paginator(srpc, 15)
    pnation_srpc = pnation.get_page(request.GET.get('page'))

    return render(request, 'partials/gradebook/personal_dev_table.html', {
        'srpc': srpc,
        'pnation_srpc': pnation_srpc,
    })


@login_required
def pdev_edit(request, pk):
    instance = get_object_or_404(ReportcardPersonalDev, pk=pk)
    queryset = ReportcardPersonalDev.objects.filter(reporcard=instance.reporcard)

    pdev_fields = ['care1', 'care2', 'care3',
                   'respect1', 'respect2', 'respect3', 'respect4',
                   'responsibility1', 'responsibility2', 'responsibility3', 'responsibility4',
                   'excellence1', 'excellence2', 'excellence3', 'excellence4']

    PersonalDevFormSet = modelformset_factory(
        ReportcardPersonalDev,
        exclude=['reporcard', 'id'],
        extra=0,
        widgets={field: forms.RadioSelect for field in pdev_fields}
    )

    if request.method == 'POST':
        formset = PersonalDevFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Personal development grades updated!")
            return redirect('pdev-edit', pk=pk)
    else:
        formset = PersonalDevFormSet(queryset=queryset)

    if not formset.forms:
        messages.error(request, "No record found.")
        return redirect('pdev-table')

    form = formset.forms[0]
    reportcard = instance.reporcard  # fix undefined variable

    label_map = {
        'care1': 'Menunjukkan kepedulian terhadap sesama',
        'care2': 'Membantu teman yang membutuhkan',
        'care3': 'Peka terhadap lingkungan sekitar',
        'respect1': 'Menghormati guru dan staff',
        'respect2': 'Menghargai pendapat orang lain',
        'respect3': 'Bersikap sopan dalam berkomunikasi',
        'respect4': 'Menghormati perbedaan',
        'responsibility1': 'Mengerjakan tugas tepat waktu',
        'responsibility2': 'Bertanggung jawab atas tindakannya',
        'responsibility3': 'Menjaga kebersihan kelas',
        'responsibility4': 'Aktif dalam kegiatan kelas',
        'excellence1': 'Berusaha memberikan yang terbaik',
        'excellence2': 'Tidak mudah menyerah',
        'excellence3': 'Menyelesaikan pekerjaan dengan baik',
        'excellence4': 'Memiliki inisiatif tinggi',
    }
    for field_name, label in label_map.items():
        if field_name in form.fields:
            form.fields[field_name].label = label

    field_groups = {
        group_name: [form[field_name] for field_name in fields]
        for group_name, fields in PERSONAL_DEV_FIELDS.items()
    }

    return render(request, 'partials/gradebook/personal_dev_edit.html', {
        'formset': formset,
        'form': form,
        'instance': instance,
        'reportcard': reportcard,
        'field_groups': field_groups,
    })

def pdev_del(request, pk):
    pdev = get_object_or_404(ReportcardPersonalDev, pk=pk)
    if request.method == 'POST':
        pdev.delete()
        return redirect('pdev-table')

    # For a GET request, show the empty form
    # form = PelanggaranForm()
    context = {
        'pdev': pdev,
    }
    return render(request, 'partials/gradebook/grade_entry_delconf.html', context)


def print_pdev_pdf(request, pk):
    instance = get_object_or_404(
        ReportcardPersonalDev.objects.select_related(
            'reporcard__student__registration_data',
            'reporcard__period',
            'reporcard__academic_year',
            'reporcard__level',
        ),
        pk=pk
    )
    reportcard = instance.reporcard
    student = reportcard.student
    reg = student.registration_data
    user = request.user
    date = datetime.now().strftime("%d %B %Y, %H:%M")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Normal'],
        fontSize=14, fontName='Times-Bold',
        alignment=TA_CENTER, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=10, fontName='Times-Roman',
        alignment=TA_CENTER, spaceAfter=4,
    )
    group_style = ParagraphStyle(
        'Group', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        spaceAfter=4, spaceBefore=8,
    )

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=7,
        fontName='Times-Italic',
        alignment=TA_LEFT,
        textColor=colors.grey,
    )

    flowables = []

    # header
    flowables.append(Paragraph("Personal Development Report", title_style))
    flowables.append(Paragraph(
        f"{reg.first_name} {reg.last_name} — {reportcard.academic_year} / {reportcard.period.period_name}",
        subtitle_style
    ))
    flowables.append(Spacer(1, 0.3*cm))

    # meta info
    meta_data = [
        ['Student', ':', f"{reg.first_name} {reg.last_name}"],
        ['ID Number', ':', student.id_number],
        ['Academic Year', ':', str(reportcard.academic_year)],
        ['Period', ':', reportcard.period.period_name],
        ['Level', ':', str(reportcard.level)],
        ['Mid Term', ':', 'Yes' if reportcard.is_mid else 'No'],
    ]
    meta_table = Table(meta_data, colWidths=[4*cm, 0.5*cm, 10*cm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    flowables.append(meta_table)
    flowables.append(Spacer(1, 0.5*cm))

    # choice labels for header
    choice_labels = [label for val, label in PDRPT_CHOICES]

    # one table per group
    label_map = {
        'care1': 'Menunjukkan kepedulian terhadap sesama',
        'care2': 'Membantu teman yang membutuhkan',
        'care3': 'Peka terhadap lingkungan sekitar',
        'respect1': 'Menghormati guru dan staff',
        'respect2': 'Menghargai pendapat orang lain',
        'respect3': 'Bersikap sopan dalam berkomunikasi',
        'respect4': 'Menghormati perbedaan',
        'responsibility1': 'Mengerjakan tugas tepat waktu',
        'responsibility2': 'Bertanggung jawab atas tindakannya',
        'responsibility3': 'Menjaga kebersihan kelas',
        'responsibility4': 'Aktif dalam kegiatan kelas',
        'excellence1': 'Berusaha memberikan yang terbaik',
        'excellence2': 'Tidak mudah menyerah',
        'excellence3': 'Menyelesaikan pekerjaan dengan baik',
        'excellence4': 'Memiliki inisiatif tinggi',
    }

    for group_name, field_names in PERSONAL_DEV_FIELDS.items():
        flowables.append(Paragraph(group_name, group_style))

        table_data = [['Indicator'] + choice_labels]

        for field_name in field_names:
            value = getattr(instance, field_name)
            label = label_map.get(field_name, field_name)
            row = [label]
            for choice_val, _ in PDRPT_CHOICES:
                row.append('✓' if value == choice_val else ' ')
            table_data.append(row)

        col_widths = [9 * cm] + [2.5 * cm] * len(PDRPT_CHOICES)
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        flowables.append(table)
        flowables.append(Spacer(1, 0.3 * cm))

    flowables.append(Paragraph(f"Printed by {user} on {date}", footer_style))

    doc.build(flowables)
    buf.seek(0)

    filename = f"pd_{reg.first_name}_{reg.last_name}_{reportcard.period.period_name}.pdf"
    return FileResponse(buf, as_attachment=False, filename=filename)


@login_required
def grade_ledger(request):
    ay_id = request.GET.get('academic_year')
    period_id = request.GET.get('period')
    is_mid = request.GET.get('is_mid') in ('on', 'true', '1', 'True')
    level_id = request.GET.get('level')

    grade_qs = ReportcardGrade.objects.select_related('reportcard__student')
    if ay_id:
        grade_qs = grade_qs.filter(reportcard__academic_year_id=ay_id)
    if period_id:
        grade_qs = grade_qs.filter(reportcard__period_id=period_id)
    if is_mid:
        grade_qs = grade_qs.filter(reportcard__is_mid=True)
    if level_id:
        grade_qs = grade_qs.filter(reportcard__level_id=level_id)

    subjects = Subject.objects.filter(
        id__in=grade_qs.values('subject_id').distinct()
    ).order_by('id')

    students = Student.objects.filter(
        studentreportcard__reportcardgrade__in=grade_qs
    ).distinct().select_related('registration_data').order_by(
        'registration_data__first_name'
    )

    # one query, dict keyed by (student_id, subject_id)
    all_grades = {
        (g.reportcard.student_id, g.subject_id): g
        for g in grade_qs.select_related('reportcard')
    }

    rows = []
    for student in students:
        cells = []
        for subject in subjects:
            grade = all_grades.get((student.id, subject.id))
            cells.append({
                'final_score': grade.final_score if grade else '-',
                'final_grade': grade.final_grade if grade else '-',
            })
        rows.append({
            'student': student,
            'cells': cells,
        })

    # pass filter form context too
    academic_years = AcademicYear.objects.all().order_by('-year')
    periods = LearningPeriod.objects.filter(
        academic_year_id=ay_id,
        period_name__icontains='semester'
    ) if ay_id else LearningPeriod.objects.none()

    return render(request, 'partials/gradebook/grade_ledger_alt.html', {
        'subjects': subjects,
        'rows': rows,
        'academic_years': academic_years,
        'periods': periods,
        'sel_ay': ay_id,
        'sel_period': period_id,
        'sel_is_mid': is_mid,
    })

