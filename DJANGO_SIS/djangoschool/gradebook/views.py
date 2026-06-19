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

register = template.Library()


def gb_index(request):
    user = request.user
    ge = GradeEntry.objects.all()
    ah = AssignmentHead.objects.all()
    ad = AssignmentDetail.objects.all()
    attendance_qs = StudentAttendance.objects.all().order_by('-id')
    ad_ahfilter = AssignmentDetail.objects.select_related('assignment_head', 'assignment_head__course', 'student')

    # sort by midterms
    midterms = AssignmentDetail.objects.filter(assignment_head__assignment__short_name='Midterm').select_related(
        'assignment_head', 'assignment_head__course', 'student')

    # sort by quizzes
    quizzes = AssignmentDetail.objects.filter(assignment_head__assignment__short_name='Quiz').select_related(
        'assignment_head', 'assignment_head__course', 'student')

    # sort by finals
    finals = AssignmentDetail.objects.filter(assignment_head__assignment__short_name='Finals').select_related(
        'assignment_head', 'assignment_head__course', 'student')

    pnation = Paginator(attendance_qs, 15)
    page = request.GET.get('page')
    pnation_attend = pnation.get_page(page)

    # average score of each student
    # score_avg = AssignmentDetail.objects.annotate(avg_score=Avg('score')).order_by('-avg_score')
    score_avg = Student.objects.annotate(avg_score=Ceil(Avg('assignmentdetail__score'))).order_by('-avg_score')
    return render(request, "partials/gradebook/index.html", {
        'ge': ge,
        'ah': ah,
        'ad': ad,
        'ad_ahfilter': ad_ahfilter,
        'midterms': midterms,
        'quizzes': quizzes,
        'finals': finals,
        'score_avg': score_avg,
        'pnation_attend': pnation_attend,
        'attendance': attendance_qs,
        'request': request,
    })


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


@register.inclusion_tag('partials/gradebook/attendance_list.html', takes_context=True)
def attendance_list(request):
    attendance = StudentAttendance.objects.all()

    pnation = Paginator(StudentAttendance.objects.all(), 15)  # Show 10 aktivitas per page
    page = request.GET.get('page')
    pnation_attend = pnation.get_page(page)

    context = {
        'attendance': attendance,
        'pnation_attend': pnation_attend
    }

    return render(request, 'partials/gradebook/attendance_list.html', context)


def attendance_list_admin(request):
    attendance = StudentAttendance.objects.all()

    pnation = Paginator(StudentAttendance.objects.all(), 15)  # Show 10 aktivitas per page
    page = request.GET.get('page')
    pnation_attend = pnation.get_page(page)

    context = {
        'attendance': attendance,
        'pnation_attend': pnation_attend
    }

    return render(request, 'admin/attendance_list_homepage.html', context)


class GradeEntryForm(LoginRequiredMixin, SessionWizardView):
    # Definisikan template untuk setiap step (opsional, bisa pakai satu template saja)
    template_name = "partials/gradebook/grade_entry.html"

    form_list = [
        ("0", GradeEntryForm),
        ("1", AssignmentHeadForm),
        ("2", AssignmentDetailFormSet),  # Step 3 pakai FormSet
    ]

    # def get_template_names(self):
    #     return [self.templates[self.steps.current]]

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)

        # if step == '0':
        #     initial['academic_year'] = None
        #     initial['period'] = None
        #     initial['teacher'] = None
        #     initial['subject'] = None
        #     initial['course'] = None
        #     initial['assignment_type'] = None

        # Logika khusus untuk Step 3 (FormSet Siswa)
        if step == '2':
            # Ambil data dari Step 0 (GradeEntry)
            step0_data = self.get_cleaned_data_for_step('0')
            if step0_data and 'course' in step0_data:
                course = step0_data['course']

                # Ambil semua siswa yang aktif di course tersebut
                students = CourseMember.objects.filter(
                    course=course,
                    is_active=True
                ).select_related('student')

                # Siapkan initial data (list of dicts) untuk FormSet
                initial_list = []
                for member in students:
                    initial_list.append({
                        'student': member.student.id,  # Untuk Hidden Field
                        'is_active': member.is_active,
                    })
                return initial_list

        return initial


    def _get_homeroom_class(self):
        """Get the homeroom class of the currently logged in teacher."""
        return Class.objects.filter(
            teacher__user=self.request.user,
            is_home_class=True,
        ).first()

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == '0':
            kwargs['user'] = self.request.user
        if step == '2':
            step1_data = self.get_cleaned_data_for_step('1')
            # step0_data = self.get_cleaned_data_for_step('0')
            # topic = step1_data['topic']
            # date = step1_data['date']
            # assign_type = step0_data['assignment_type']

            if step1_data and 'max_score' in step1_data:
                kwargs['max_score'] = step1_data['max_score']
            # Pass form_kwargs_list for each form in the formset

            # if step1_data:
            #     kwargs['topic'] = step1_data['topic']

            initial = self.get_form_initial(step)
            kwargs['form_kwargs_list'] = [{'form_index': i} for i in range(len(initial))]
        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        # Get cleaned data from step 0 if available
        step0_data = self.get_cleaned_data_for_step('0')
        step1_data = self.get_cleaned_data_for_step('1')
        context['is_homeroom'] = self._get_homeroom_class()
        # step2_data = self.get_cleaned_data_for_step('2')
        if step0_data:
            context['selected_academic_year'] = step0_data.get('academic_year')
            context['selected_period'] = step0_data.get('period')
            context['selected_level'] = step0_data.get('level')
            context['selected_subject'] = step0_data.get('subject')
            context['selected_is_mid'] = step0_data.get('is_mid')
            context['selected_assignment_type'] = step0_data.get('assignment_type')
            cpmp_targets = step0_data.get('cpmp_target')
            if cpmp_targets:
                context['selected_cpmp_target'] = '\n'.join(target.text for target in cpmp_targets)
            else:
                context['selected_cpmp_target'] = ''
        if step1_data:
            context['selected_topic'] = step1_data.get('topic')
            context['selected_date'] = step1_data.get('date')


        return context



    def done(self, form_list, **kwargs):
        # Ambil data dari form yang sudah divalidasi
        form_data_0 = form_list[0].cleaned_data  # GradeEntry
        form_data_1 = form_list[1].cleaned_data  # AssignmentHead
        formset_data_2 = form_list[2]  # AssignmentDetailFormSet (ini formset object)

        # 1. Simpan GradeEntry (jika masih diperlukan sebagai log)
        # grade_entry_instance = form_list[0].save()

        # 2. Buat dan Simpan AssignmentHead
        # Kita gabungkan data dari Step 0 dan Step 1
        assignment_head = AssignmentHead(
            assignment=form_data_0['assignment_type'],  # Dari Step 0
            course=form_data_0['course'],  # Dari Step 0
            date=form_data_1['date'],  # Dari Step 1
            topic=form_data_1['topic'],  # Dari Step 1
            max_score=form_data_1['max_score'],
        )
        assignment_head.save()
        assignment_head.cpmp_target.set(form_data_0['cpmp_target'])

        # 3. Simpan AssignmentDetail (Looping FormSet)
        details_to_create = []
        max_score = assignment_head.max_score
        for form in formset_data_2:
            if form.is_valid() and form.cleaned_data:  # Pastikan form valid dan tidak kosong
                note_content = form.cleaned_data.get('teacher_notes')
                detail = form.save(commit=False)
                detail.assignment_head = assignment_head  # Link ke Head yang baru dibuat
                detail.teacher_notes = note_content
                if detail.score > max_score:
                    return HttpResponse("Error: Score exceeds maximum allowed.")
                # elif formset_data_2['form-0-student'] is None:
                #     return HttpResponse("Error: No students selected.")
                else:
                    # Student sudah ada di instance dari form clean (karena ModelForm)
                    details_to_create.append(detail)

        # Bulk create untuk performa lebih cepat
        AssignmentDetail.objects.bulk_create(details_to_create)

        messages.success(self.request, "Class behavior grading has been finalized!")
        # return render(self.request, "partials/gradebook/finished_screen.html")
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
        """Get the homeroom class of the currently logged in teacher."""
        return Class.objects.filter(
            teacher__user=self.request.user,
            is_home_class=True,
        ).first()

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)

        if step == '1':
            data0 = self.get_cleaned_data_for_step('0')
            homeroom_class = self._get_homeroom_class()

            if not data0 or not homeroom_class:
                return initial

            academic_year = data0.get('academic_year')
            period = data0.get('period')
            is_mid = data0.get('is_mid')
            level = data0.get('level')

            members = ClassMember.objects.filter(
                kelas=homeroom_class,
                is_active=True,
            ).select_related('student__registration_data')

            initial_list = []
            for member in members:
                student = member.student

                # Check if a reportcard already exists for this student
                existing_reportcard = StudentReportcard.objects.filter(
                    student=student,
                    academic_year=academic_year,
                    period=period,
                    is_mid=is_mid,
                ).first()

                initial_list.append({
                    'student_id': student.id,
                    'student_name': f"{student.id_number} - {student.registration_data.first_name} {student.registration_data.last_name}",
                    'ht_comment': existing_reportcard.ht_comment if existing_reportcard else '',
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
                        defaults={
                            'level': level,
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
        levels = GradeLevel.objects.all()
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
    else:
        teachers = Teacher.objects.none()

    # Use 'items' or 'teachers' consistently with your partial template
    return render(request, "partials/gradebook/gradeentry_partials/teacher.html", {'teachers': teachers})


def get_courses(request):
    subject_id = request.GET.get('0-subject') or request.GET.get('1-subject') or request.GET.get('subject')
    selected_course = request.GET.get('0-course') or request.GET.get('1-course') or request.GET.get('course')
    if subject_id:
        courses = Course.objects.filter(subject_id=subject_id)
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
    level_queryset = GradeLevel.objects.all() if acayear_id else GradeLevel.objects.none()
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
        subjects = Subject.objects.filter(course__teacher__id=teacher_id).distinct()
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
        classes = Class.objects.filter(teacher__id=teacher_id, is_home_class=True).distinct()
    else:
        classes = Class.objects.none()
    context = {
        'classes': classes,
        'selected_kelas': selected_kelas
    }
    return render(request, "partials/gradebook/gradeentry_partials/kelas.html", context)


def get_courses_ge(request):
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('1-academic_year') or request.GET.get('academic_year')
    subject_id = request.GET.get('0-subject') or request.GET.get('1-subject') or request.GET.get('subject')
    selected_course = request.GET.get('0-course') or request.GET.get('1-course') or request.GET.get('course')
    if subject_id and acayear_id:
        courses = Course.objects.filter(academic_year=acayear_id, subject=subject_id)
    else:
        courses = Course.objects.none()
    context = {
        'courses': courses,
        'selected_course': selected_course
    }
    # return render(request, "partials/gradebook/course_list.html", context)
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


@login_required
def toggle_na_reason(request):
    form_index = request.GET.get('form_index', '0')

    na_reason_keys = [k for k in request.GET.keys() if k.endswith('-na_reason')]
    if na_reason_keys:
        na_reason_name = na_reason_keys[0]
    else:
        na_reason_name = f'2-{form_index}-na_reason'

    is_active_name = na_reason_name.replace('-na_reason', '-is_active')
    score_name = na_reason_name.replace('-na_reason', '-score')
    is_active_value = request.GET.get(is_active_name, '')
    is_active = is_active_value == 'on'

    if is_active:
        # active — show empty na_reason, keep score editable
        input_html = f'''
        <input id="na_reason_input_{form_index}"
            type="text"
            class="form-control"
            name="{na_reason_name}"
            value=""
            placeholder="N/A"
            disabled />
        '''
    else:
        # inactive — clear score, show na_reason input
        input_html = f'''
        <input id="na_reason_input_{form_index}"
            type="text"
            class="form-control"
            name="{na_reason_name}"
            value=""
            placeholder="Reason required..." />
        '''

    # OOB swap to clear score when toggled
    score_html = f'''
    <input id="id_2-{form_index}-score"
        type="number"
        class="form-control"
        name="{score_name}"
        value="0" />
    '''

    return HttpResponse(
        input_html +
        f'<div hx-swap-oob="innerHTML:#score_td_{form_index}">{score_html}</div>'
    )


# biar short name subject keliatan
# kalau pakai cara ini berarti ComputationField yg biasanya dipake di ReportView
# diambil alih scr manual pake yg ini
class ScoreField(ComputationField):
    # nama bisa apa aja (INI PENTING, HARUS ADA)
    name = "scorecolumn"
    # metode penghitungan (Sum, Avg, Count, dll)
    calculation_method = Sum
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
        response['Content-Disposition'] = 'attachment; filename="grade_report.pdf"'

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
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')
    period = LearningPeriod.objects.filter(academic_year_id=acayear_id, period_name__icontains='semester')
    context = {'period': period}
    return render(request, "partials/gradebook/rcledger_partials/period.html", context)

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
    teach = Teacher.objects.filter(user=user).first()
    ge = GradeEntry.objects.all()
    # ah = AssignmentHead.objects.all()
    ad = AssignmentDetail.objects.all()

    if teach:
        ah = AssignmentHead.objects.filter(course__teacher=teach).order_by('-date')
    else:
        ah = AssignmentHead.objects.all().order_by('-date')

    pnation = Paginator(ah, 15)  # Show 10 aktivitas per page
    page = request.GET.get('page')
    pnation_ah = pnation.get_page(page)

    context_table = {
        'ge': ge,
        'ah': ah,
        'ad': ad,
        'pnation_ah': pnation_ah
    }

    return render(request, 'partials/gradebook/grade_entry_table.html', context_table)


from .models import AssignmentDetail, CourseMember


# INGET YA ID ASSIGNMENTDETAIL != ID ASSIGNMENTHEAD PANTES DRTD NGACO MULU QUERYSETNYA
@login_required
def ge_edit(request, pk):
    # 1. Get the reference detail to find the 'Head' assignment
    # target_detail = get_object_or_404(AssignmentDetail, pk=pk)
    parent_head = get_object_or_404(AssignmentHead, pk=pk)
    current_course = parent_head.course
    assign_type = parent_head.assignment
    cpmp_trg = '\n'.join(target.text for target in parent_head.cpmp_target.all())

    # 2. DATA SYNC: Ensure ALL active students in this course have a row for this assignment
    # This fixes the issue where only 1 student shows up.
    active_members = CourseMember.objects.filter(course=current_course, is_active=True)

    for member in active_members:
        # Create a blank row (score=0) if it doesn't exist yet
        AssignmentDetail.objects.get_or_create(
            assignment_head=parent_head,
            student=member.student,
            defaults={'score': 0, 'is_active': True}
        )

    # print(f"Target Detail:  {target_detail}")
    # print(f"Parent: {parent_head}")
    # print(f"Course: {current_course}")

    # 3. Create the Queryset containing ALL students for this assignment
    # We order by student ID (or name if available) to keep the list stable
    queryset = AssignmentDetail.objects.filter(
        assignment_head=parent_head
    ).order_by('student__id')

    # 4. Define the Formset
    AssignmentFormSet = modelformset_factory(
        AssignmentDetail,
        fields=('score', 'na_reason', 'is_active'),
        extra=0,  # We don't want blank extra rows, we just want the students
        # widgets={
        #     'score': forms.NumberInput(attrs={'class': 'form-control'}),
        #     'na_reason': forms.TextInput(attrs={'class': 'form-control'}),
        #     'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        # }
    )

    if request.method == 'POST':
        formset = AssignmentFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            return redirect('grade-entry-table')  # Make sure this URL name is correct in urls.py
    else:
        formset = AssignmentFormSet(queryset=queryset)

    # Add HTMX attributes to the forms
    for i, form in enumerate(formset):
        form.fields['na_reason'].widget.attrs.update({
            'hx-get': f'/gradebook/toggle-na-reason/?form_index={i}',
            'hx-trigger': 'change',
            'hx-target': f'#na_reason_td_{i}',
            'hx-swap': 'innerHTML',
            'hx-include': f'[name="{form.add_prefix("na_reason")}"], [name="{form.add_prefix("is_active")}"]',
            'class': 'form-control textarea textarea-bordered w-full min-w-24 focus:outline-0 transition-all focus:outline-offset-0'
        })
        form.fields['is_active'].widget.attrs.update({
            'hx-get': f'/gradebook/toggle-na-reason/?form_index={i}',
            'hx-trigger': 'change',
            'hx-target': f'#na_reason_td_{i}',
            'hx-swap': 'innerHTML',
            'hx-include': f'[name="{form.add_prefix("na_reason")}"], [name="{form.add_prefix("is_active")}"]'
        })

    return render(request, 'partials/gradebook/grade_entry_edit.html', {
        'formset': formset,
        'parent_head': parent_head,
        'title': parent_head.topic,
        'date': parent_head.date,
        'max_score': parent_head.max_score,
        'assign_type': assign_type,
        'cpmp_target': cpmp_trg or '-'
    })


def ge_del(request, pk):
    ahead = get_object_or_404(AssignmentHead, pk=pk)
    if request.method == 'POST':
        ahead.delete()
        return redirect('grade-entry-table')

    # For a GET request, show the empty form
    # form = PelanggaranForm()
    # context = {
    #     'form': form,
    # }
    return render(request, 'partials/gradebook/grade_entry_delconf.html')


@login_required
def tc_table(request):
    src = StudentReportcard.objects.all()

    pnation = Paginator(StudentReportcard.objects.all(), 15)  # Show 10 aktivitas per page
    page = request.GET.get('page')
    pnation_src = pnation.get_page(page)

    context = {
        'src': src,
        'pnation_src': pnation_src
    }

    return render(request, 'partials/gradebook/report_card_table.html', context)


@login_required
def tc_edit(request, pk):
    # 1. Get the reference detail to find the 'Head' assignment
    # target_detail = get_object_or_404(AssignmentDetail, pk=pk)
    parent_head = get_object_or_404(StudentReportcard, pk=pk)
    selected_student = parent_head.student
    selected_ismid = parent_head.is_mid

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
    queryset = StudentReportcard.objects.filter(student=selected_student, is_mid=selected_ismid)

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
        src.delete()
        return redirect('report-card-table')

    # For a GET request, show the empty form
    # form = PelanggaranForm()
    # context = {
    #     'form': form,
    # }
    return render(request, 'partials/gradebook/grade_entry_delconf.html')


@login_required
def toggle_na_reason(request):
    # 1. Extract the step and form index from the keys (e.g., '2-0-is_active')
    step_prefix = ""
    form_idx = ""

    for key in request.GET.keys():
        if '-is_active' in key:
            parts = key.split('-')  # ['2', '0', 'is_active']
            step_prefix = parts[0]
            form_idx = parts[1]
            break

    if not form_idx:
        return HttpResponse("")

    # 2. Get the current state
    is_active = request.GET.get(f'{step_prefix}-{form_idx}-is_active') == 'on'
    score = request.GET.get(f'{step_prefix}-{form_idx}-score', '')
    na_reason = request.GET.get(f'{step_prefix}-{form_idx}-na_reason', '')

    # We also need the student info which is in hidden fields or NISN/Name
    # but since we are just re-rendering the inputs, we can just pass values
    student_name = request.GET.get(f'{step_prefix}-{form_idx}-student_name', '')
    student_nisn = request.GET.get(f'{step_prefix}-{form_idx}-student_nisn', '')

    # 3. APPLY BACKEND LOGIC (The "Wipe")
    if is_active:
        na_reason = ""
    else:
        score = ""

    # 4. SEND BACK THE ROW HTML
    # We use a small partial template for a single row to keep it clean
    context = {
        'step': step_prefix,
        'idx': form_idx,
        'score': score,
        'na_reason': na_reason,
        'is_active': is_active,
        'student_name': student_name,
        'student_nisn': student_nisn,
    }

    html = render_to_string("partials/gradebook/gradeentry_partials/row_partial.html", context)
    return HttpResponse(html)


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

            students = ClassMember.objects.filter(
                kelas=data0['kelas'],
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
                context['selected_kelas'] = data_step0.get('kelas')

        if self.steps.current == '0':
            acayear = AcademicYear.objects.all()
            period = LearningPeriod.objects.all().select_related('academic_year')
            kelas = Class.objects.all()
            level = GradeLevel.objects.all()
            context['selected_acayear'] = acayear
            context['selected_period'] = period
            context['selected_kelas'] = kelas
            context['selected_level'] = level

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
    # class_id = request.GET.get('class_id')
    # if class_id:
    #     kelas = Class.objects.filter(id=class_id)
    # else:
    #     kelas = Class.objects.none()
    #
    # return render(request, "partials/gradebook/rubric_entry_partials/kelas.html", {'kelas': kelas})
    teacher_id = request.GET.get('0-teacher') or request.GET.get('teacher')
    selected_kelas = request.GET.get('0-kelas') or request.GET.get('kelas')
    if teacher_id:
        # Filter classes where the teacher is the homeroom teacher
        # classes = Class.objects.filter(teacher__id=teacher_id).distinct()
        classes = Class.objects.all()
    else:
        classes = Class.objects.none()
    context = {
        'classes': classes,
        'selected_kelas': selected_kelas
    }
    return render(request, "partials/gradebook/gradeentry_partials/kelas.html", context)

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

            members = ClassMember.objects.filter(
                kelas=kelas,
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
    else:
        teachers = Teacher.objects.none()
    context = {'teachers': teachers}
    return render(request, "partials/gradebook/reportextra_partials/teacher.html", context)

def get_kelas_extra(request):
    teacher_id = request.GET.get('0-teacher') or request.GET.get('teacher')
    selected_kelas = request.GET.get('0-kelas') or request.GET.get('kelas')
    if teacher_id:
        # Filter classes where the teacher is the homeroom teacher
        classes = Class.objects.filter(teacher__id=teacher_id, is_activity=True).distinct()
    else:
        classes = Class.objects.none()
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
    if kelas_id:
        # Filter classes where the teacher is the homeroom teacher
        subject = Subject.objects.filter(is_activity=True)
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

    if not weight_map:
        return [], None

    # 2. TENTUKAN RENTANG TANGGAL PERIODE (TERM / SEMESTER)
    terms = LearningPeriod.objects.filter(academic_year=academic_year, date_start__lte=period.date_end,
                                          date_end__gte=period.date_start, period_name__icontains='term').order_by('date_start')

    print("============= DEBUG TANGGAL =============")
    print(f"Periode yang dicek: {period.period_name}")
    print(f"Academic Year: {academic_year}")
    print(f"Start: {period.date_start}, End: {period.date_end}")
    print(f"Hasil Query 'terms': {terms}")
    print("=========================================")

    term_period = terms.first() if is_mid else terms.last()
    term_period = term_period or period

    # 3. AMBIL RATA-RATA NILAI TUGAS MURID LANGSUNG DARI DB
    grades_data = AssignmentDetail.objects.filter(
        assignment_head__course__subject=subject,
        assignment_head__course__academic_year=academic_year,
        assignment_head__assignment_id__in=weight_map.keys(),
        assignment_head__date__range=(term_period.date_start, term_period.date_end)
    ).values('student_id', 'assignment_head__assignment_id').annotate(avg_score=Avg('score'))

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

        results.append({
            'student_obj': student_obj,
            'student_name': str(student_obj),
            'nisn': getattr(student_obj, 'nisn', '-'),
            'subject': subject,
            'level': level,
            'raw_avg': raw_avg,
            'weighted_avg': final_score,
            'final_score_preview': round(final_score),
            'period': period
        })

    return results, term_period

def calc_student_avg_redone(academic_year, subject, level, is_mid, period):
    # bobot_formatif_sem_jalan = Weighting.objects.filter(
    #         academic_year=academic_year,
    #         level=level,
    #         subject=subject,
    #         period=period,
    #         is_mid=is_mid
    #     )
    #
    # bobot_sumatif_sem_akhir = Weighting.objects.filter(
    #     academic_year=academic_year,
    #     level=level,
    #     subject=subject,
    #     period=period,
    #     is_mid=True,
    #     assignment__short_name='SUMM'
    # )
    #
    # selected_periods = LearningPeriod.objects.filter(
    #     academic_year=academic_year,
    #     date_start__lte=period.date_end,
    #     date_end__gte=period.date_start
    # )
    #
    #
    # weight_map = {w.assignment_id: w.weight for w in bobot_formatif_sem_jalan}
    # allowed_assignment_ids = list(weight_map.keys())
    #
    # if not allowed_assignment_ids:
    #     return [], None
    #
    # # if not period:
    # #     period = semester_periods.first()
    #
    # detail_qs = AssignmentDetail.objects.filter(
    #     assignment_head__course__subject=subject,
    #     assignment_head__course__academic_year=academic_year,
    #     assignment_head__assignment_id__in=allowed_assignment_ids
    # )
    #
    # # ========================================================
    # # FIX 2: PENCARIAN TERM (DENGAN PENGECEKAN NULL)
    # # ========================================================
    # ordered_periods = selected_periods.order_by('date_start').filter(period_name__icontains='term')
    #
    # # Ambil periode, jika kosong gunakan periode default dari 'period'
    # if ordered_periods.exists():
    #     term_period = ordered_periods.first() if is_mid else ordered_periods.last()
    # else:
    #     term_period = period
    #
    #
    #
    # totals = Weighting.objects.aggregate(
    #     sum1 = Sum('weight', filter=Q(academic_year=academic_year) & Q(level=level) & Q(subject=subject) & Q(period=period) & Q(is_mid=is_mid)),
    #     sum2 = Sum('weight', filter=Q(academic_year=academic_year) & Q(level=level) & Q(subject=subject) & Q(period=period) & Q(is_mid=True) & Q(assignment__short_name='SUMM'))
    # )
    #
    # grand_total = (totals['sum1'] or 0) + (totals['sum2'] or 0)
    #
    # # sum = bobot_formatif_sem_jalan + bobot_sumatif_sem_akhir
    #
    # results = 1 - grand_total
    #
    from decimal import Decimal
    # return str(Decimal(results)), term_period

    bobot_sem_jalan = Weighting.objects.filter(
        academic_year=academic_year,
        level=level,
        subject=subject,
        period=period,
        is_mid=is_mid
    )

    weight_map = {w.assignment_id: w.weight for w in bobot_sem_jalan}
    allowed_assignment_ids = list(weight_map.keys())

    print(weight_map)

    if not allowed_assignment_ids:
        return [], None

    # ========================================================
    # 2. HITUNG SISA BOBOT UNTUK MID SEMESTER (Hasilnya 30%)
    # ========================================================
    # Kita totalin bobot yang aktif saat ini (Misal: 0.50 + 0.20 = 0.70)
    current_total_weight = bobot_sem_jalan.aggregate(
        weight_map=Sum('weight')
    )['weight_map'] or Decimal('0.00')

    # Cari sisanya (100% - Total Saat Ini)
    # Catatan: Karena db lu pakai max_digits=2 (skala 0.00 - 0.99), 100% itu ditulis '1.0'
    sisa_bobot = Decimal('1.0') - current_total_weight

    # Pengaman biar nggak minus kalau kebetulan total bobotnya nyentuh/lebih dari 100%
    if sisa_bobot < Decimal('0.00'):
        sisa_bobot = Decimal('0.00')

    # ========================================================
    # 3. LANJUTAN LOGIKA QUERY DETAIL & TERM
    # ========================================================
    detail_qs = AssignmentDetail.objects.filter(
        assignment_head__course__subject=subject,
        assignment_head__course__academic_year=academic_year,
        assignment_head__assignment_id__in=allowed_assignment_ids
    )

    selected_periods = LearningPeriod.objects.filter(
        academic_year=academic_year,
        date_start__lte=period.date_end,
        date_end__gte=period.date_start
    )

    ordered_periods = selected_periods.order_by('date_start').filter(period_name__icontains='term')

    # FIX 2: PENCARIAN TERM (DENGAN PENGECEKAN NULL)
    if ordered_periods.exists():
        term_period = ordered_periods.first() if is_mid else ordered_periods.last()
    else:
        term_period = period

    # Mengembalikan nilai sisa bobot (str) dan term_period
    return str(sisa_bobot), term_period


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
        periods = LearningPeriod.objects.filter(academic_year_id=acayear_id, period_name__icontains='semester')
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
    acayear_id = request.GET.get('0-academic_year') or request.GET.get('academic_year')
    selected_period = request.GET.get('0-period') or request.GET.get('period')
    if acayear_id:
        # periods = LearningPeriod.objects.filter(academic_year_id=acayear_id)
        periods = LearningPeriod.objects.all()
    else:
        periods = LearningPeriod.objects.all()
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

    # ─── HEADER ───────────────────────────────────────────────
    flowables = []


    # Meta info table (topic, date, max score, course)
    meta_data = [
        ['Topic',       ':', str(parent_head.topic or '-')],
        ['Date',        ':', str(parent_head.date or '-')],
        ['Max Score',   ':', str(parent_head.max_score)],
        ['Assignment',  ':', str(parent_head.assignment.name)],
        ['Learning Target', ':', str(cpmp_trg or '-')]
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
            detail.na_reason or '-',
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

    # ─── BUILD ────────────────────────────────────────────────
    doc.build(flowables)
    buf.seek(0)

    filename = f"grade_entry_{current_course.short_name}_{parent_head.date}.pdf"
    return FileResponse(buf, as_attachment=False, filename=filename)



