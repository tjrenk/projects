from email import header
import io
from multiprocessing import context
import os
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from formtools.wizard.views import SessionWizardView
from .forms import PersonalInfoForm, ContactInfoForm, ParentInfoForm
from .models import *
from .charts import months, colorPrimary, colorSuccess, colorDanger, generate_color_palette, get_year_dict
from django.db.models.functions import ExtractYear, ExtractMonth
from django.core.paginator import Paginator
from django.db.models import Q
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Frame, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.graphics.shapes import Drawing, Line
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import logout
from PIL import Image as PILImage

# Create your views here.
def index(request):
    student_count = Student.objects.count()
    context = {
        'student_count': student_count
    }
    return render(request, 'partials/admission/index.html', context)

class AdmissionView(LoginRequiredMixin, SessionWizardView):
    template_name = "partials/admission/admission.html"

    form_list = [
        ("0", PersonalInfoForm),
        ("1", ContactInfoForm),
        ("2", ParentInfoForm), # Step 3 pakai FormSet
    ]

    def done(self, form_list, **kwargs):
        if form_list:
            form_data = {}
            for form in form_list:
                form_data.update(form.cleaned_data)
            # Simpan data ke model Registration

            registration = Registration.objects.create(
                form_no=form_data.get('form_no'),
                first_name=form_data.get('first_name'),
                last_name=form_data.get('last_name'),
                middle_name=form_data.get('middle_name'),
                gender=form_data.get('gender'),
                nisn=form_data.get('nisn'),
                prev_school=form_data.get('prev_school'),
                prev_nis=form_data.get('prev_nis'),
                birth_order=form_data.get('birth_order'),
                date_of_birth=form_data.get('date_of_birth'),
                place_of_birth=form_data.get('place_of_birth'),
                religion=form_data.get('religion'),
                church_name=form_data.get('church_name'),
                current_address=form_data.get('current_address'),
                current_district=form_data.get('current_district'),
                current_region=form_data.get('current_region'),
                current_city=form_data.get('current_city'),
                current_province=form_data.get('current_province'),
                contact_whatsapp=form_data.get('contact_whatsapp'),
                contact_mobile=form_data.get('contact_mobile'),
                contact_email=form_data.get('contact_email'),
                contact_preference=form_data.get('contact_preference'),
                mother_name=form_data.get('mother_name'),
                mother_nik=form_data.get('mother_nik'),
                mother_religion=form_data.get('mother_religion'),
                mother_education=form_data.get('mother_education'),
                mother_occupation=form_data.get('mother_occupation'),
                mother_address_same2applicant=form_data.get('mother_address_same2applicant'),
                mother_address=form_data.get('mother_address'),
                mother_district=form_data.get('mother_district'),
                mother_region=form_data.get('mother_region'),
                mother_city=form_data.get('mother_city'),
                mother_province=form_data.get('mother_province'),
                mother_phone=form_data.get('mother_phone'),
                mother_mobile=form_data.get('mother_mobile'),
                mother_whatsapp=form_data.get('mother_whatsapp'),
                mother_email=form_data.get('mother_email'),
                father_name=form_data.get('father_name'),
                father_nik=form_data.get('father_nik'),
                father_religion=form_data.get('father_religion'),
                father_education=form_data.get('father_education'),
                father_occupation=form_data.get('father_occupation'),
                father_address_same2applicant=form_data.get('father_address_same2applicant'),
                father_address=form_data.get('father_address'),
                father_district=form_data.get('father_district'),
                father_region=form_data.get('father_region'),
                father_city=form_data.get('father_city'),
                father_province=form_data.get('father_province'),
                father_phone=form_data.get('father_phone'),
                father_mobile=form_data.get('father_mobile'),
                father_whatsapp=form_data.get('father_whatsapp'),
                father_email=form_data.get('father_email'),
            )

        registration.save()

        
        return render(self.request, "partials/admission/finished_screen.html")
    

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from formtools.wizard.views import SessionWizardView
from .forms import PersonalInfoForm, ContactInfoForm, ParentInfoForm
from .models import *
from .charts import months, colorPrimary, colorSuccess, colorDanger, generate_color_palette, get_year_dict
from django.db.models.functions import ExtractYear, ExtractMonth
from django.db.models import Count, Sum, Avg  # Add this import

# ...existing code...

def get_filter_options(request):
    options = AcademicYear.objects.all().order_by('-year').values_list('year', flat=True)

    return JsonResponse({
        "options": list(options)
    })

def logout_view(request):
    logout(request)

# Add this new view for student counts per grade level
def get_student_counts(request):
    year = request.GET.get('year')
    queryset = ClassMember.objects.filter(is_active=True)
    if year:
        queryset = queryset.filter(kelas__academic_year__year=year, kelas__is_home_class=True)
    counts = queryset.values('kelas__name').annotate(count=Count('student')).order_by('kelas__name')
    
    labels = [item['kelas__name'] for item in counts]
    data = [item['count'] for item in counts]
    
    return JsonResponse({
        'labels': labels,
        'data': data,
    })

@login_required
def regist_table(request):
    # 1. Start with all students
    student_list = Student.objects.all().order_by('nisn') # Ordering is important for pagination

    # 2. Get the filter values from the URL (GET parameters)
    # These will be 'None' if the user hasn't filtered yet
    year_id = request.GET.get('year')
    class_id = request.GET.get('class')
    teacher_id = request.GET.get('teacher')
    search_query = request.GET.get('q')

    # 3. Apply Filters if values exist
    # Note: We use 'classmember__...' to filter across the relationships defined in your models
    if year_id:
        student_list = student_list.filter(classmember__kelas__academic_year__id=year_id)
    
    if class_id:
        student_list = student_list.filter(classmember__kelas__id=class_id)
        
    if teacher_id:
        student_list = student_list.filter(classmember__kelas__teacher__id=teacher_id)

    if search_query:
        # This checks if the query is in First Name OR Last Name OR NISN
        # We use 'icontains' for case-insensitive search (John == john)
        student_list = student_list.filter(
            Q(registration_data__first_name__icontains=search_query) |
            Q(registration_data__last_name__icontains=search_query) |
            Q(nisn__icontains=search_query)
        )

    # Prevent duplicates if a student appears in multiple filtered results
    student_list = student_list.distinct()

    # 4. Fetch options for the dropdown menus
    # We pass these to the template so the user can see options like "2024/2025" instead of just IDs
    academic_years = AcademicYear.objects.all()
    classes = Class.objects.all()
    teachers = Teacher.objects.all()

    # 5. Pagination Logic
    pnation = Paginator(student_list, 15)
    page = request.GET.get('page')
    pnation_regist = pnation.get_page(page)

    context = {
        'pnation_regist': pnation_regist,
        # Dropdown options
        'academic_years': academic_years,
        'classes': classes,
        'teachers': teachers,
        # Pass the selected values back to the template so the dropdowns stay set after clicking filter
        'selected_year': int(year_id) if year_id else None,
        'selected_class': int(class_id) if class_id else None,
        'selected_teacher': int(teacher_id) if teacher_id else None,
        'search_query': search_query if search_query else '',
    }

    return render(request, 'partials/admission/student_table.html', context)


def pdf_regist_table(request):
    # 1. Start with the full list (Just like the normal view)
    student_list = Student.objects.all().order_by('nisn')

    # 2. Get Filters
    year_id = request.GET.get('year')
    class_id = request.GET.get('class')
    teacher_id = request.GET.get('teacher')
    search_query = request.GET.get('q')

    # 3. Apply Filters (Exactly the same as your HTML view)
    if year_id:
        student_list = student_list.filter(classmember__kelas__academic_year__id=year_id)
    
    if class_id:
        student_list = student_list.filter(classmember__kelas__id=class_id)
        
    if teacher_id:
        student_list = student_list.filter(classmember__kelas__teacher__id=teacher_id)

    if search_query:
        student_list = student_list.filter(
            Q(registration_data__first_name__icontains=search_query) |
            Q(registration_data__last_name__icontains=search_query) |
            Q(nisn__icontains=search_query)
        )

    # 4. Final Cleanup
    student_list = student_list.distinct()
    
    # --- PDF GENERATION STARTS HERE ---
    
    # Custom class to add watermark logo
    class PageWithWatermark(SimpleDocTemplate):
        def __init__(self, *args, **kwargs):
            self.watermark_image = kwargs.pop('watermark_image', None)
            super().__init__(*args, **kwargs)
        
        def _endPage(self):
            if self.watermark_image:
                self.canv.saveState()
                self.canv.setOpacity(1.15)  # Set opacity to 15% for watermark effect
                # Center the logo on the page
                img_width = 300
                img_height = 300
                x = (self.pagesize[0] - img_width) / 2
                y = (self.pagesize[1] - img_height) / 2
                self.canv.drawImage(
                    self.watermark_image, 
                    x, y, 
                    width=img_width, 
                    height=img_height,
                    preserveAspectRatio=True
                )
                self.canv.restoreState()
            super()._endPage()
    
    buf = io.BytesIO()
    watermark_logo_path = os.path.join(settings.BASE_DIR, 'static_files', 'images', 'logo_echs_vert.jpeg')
    
    # 1. Use the standard SimpleDocTemplate
    doc = SimpleDocTemplate(
        buf, 
        pagesize=A4, 
        rightMargin=30, 
        leftMargin=30, 
        topMargin=30, 
        bottomMargin=18
    )
    
    # 2. Define a background callback function
    def draw_watermark(canvas, doc):
        canvas.saveState()
        
        # Center the logo on the page
        img_width = 300
        img_height = 300
        x = (doc.pagesize[0] - img_width) / 2
        y = (doc.pagesize[1] - img_height) / 2
        
        # 1. Open the image with Pillow and force it into RGBA mode (adds an alpha channel)
        img = PILImage.open(watermark_logo_path).convert("RGBA")
        
        # 2. Extract the alpha channel and reduce its intensity to 15%
        r, g, b, a = img.split()
        alpha = a.point(lambda p: int(p * 0.15)) 
        img.putalpha(alpha)
        
        # 3. Wrap it in ReportLab's ImageReader and draw
        # mask='auto' tells ReportLab to respect the Pillow alpha channel
        canvas.drawImage(
            ImageReader(img), 
            x, y, 
            width=img_width, 
            height=img_height,
            preserveAspectRatio=True,
            mask='auto' 
        )
        canvas.restoreState()

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
        fontName='Times-Roman',
        textColor="#1C1F7E"
)
    # Kopsurat styling
    kopsurat_nama_institusi = ParagraphStyle(
        'KopSuratNamaInstitusi',
        parent=styles['Normal'],
        fontSize=30,
        leading=30,
        alignment=TA_CENTER,
        fontName='Times-Bold',
        textColor="#1C1F7E"
    )

    available_width = 595 - 10  # A4 width minus margins (595 - 30 - 30 = 535)

    separator = Drawing(available_width, 2)
    logo = os.path.join(settings.BASE_DIR, 'static_files\images\logo_echs_vert.jpeg')

    # # setting gambar
    logo_stte = Image(logo, width=100, height=90)


    line = Line(
        x1=-50, y1=1,
        x2=available_width, y2=1,
        strokeColor=colors.HexColor("#1C1F7E"),
        strokeWidth=2
    )

    separator.add(line)

    kop_left_content = [
        Spacer(1, -15),
        logo_stte,
    ]

    kop_right_content = [
        Paragraph("SMAK EKUMENE", kopsurat_nama_institusi),
        Spacer(1, 4),
        Paragraph("Pertokoan Gading Kirana A10 1-2 Kelapa Gading Barat, Jakarta Utara 14240, Indonesia", center_style_small),
        Paragraph("0813 9948 8499  |  info@ekumene.sch.id", center_style_small),
    ]

    kopsurat_data_1 = [
        [kop_left_content, kop_right_content],
    ]

    kopsurat_table = Table(kopsurat_data_1, colWidths=[100, 400])

    kopsurat_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, "#FFFFFFFF"), # No grid
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # Align labels (col 0) to the left
            ('ALIGN', (1, 0), (1, -1), 'LEFT'), # Align values (col 1) to the left
            ('FONTNAME', (0, 0), (0, -1), 'Times-Roman') # Make labels bold
        ]))
    # rekreasi kop surat
    # flowables.append(kopsurat_table)
    background = Image(logo, width=500, height=700)
    # flowables.append(background)
    flowables.append(kopsurat_table)
    flowables.append(separator)
    flowables.append(Spacer(1, 12))
    # flowables.append(Spacer(1, 24))
    
    # judul ("EKUPOINT REPORT")
    # flowables.append(header)
    # flowables.append(Spacer(1, 12))
    # flowables.append(header_dua)
    flowables.append(Spacer(1, 24))



    # Title
    title_style = ParagraphStyle(name='CenterTitle', parent=styles['Heading1'], alignment=TA_CENTER)
    flowables.append(Paragraph("Student Report", title_style))
    
    # Add a subtitle showing active filters (Optional but helpful)
    filter_info = []
    if year_id: filter_info.append(f"Year ID: {year_id}")
    if class_id: filter_info.append(f"Class ID: {class_id}")
    if search_query: filter_info.append(f"Search: {search_query}")
    
    flowables.append(Paragraph(f"{', '.join(filter_info)}", styles['Normal']))
    
    flowables.append(Spacer(1, 0.25 * inch))

    # Table Header
    data = [['NISN', 'Name', 'Active', 'Reason']]

    # Table Body
    for student in student_list:
        # Handle names safely (avoid "None" printing if middle name is empty)
        first = student.registration_data.first_name or ""
        mid = student.registration_data.middle_name or ""
        last = student.registration_data.last_name or ""
        full_name = f"{first} {mid} {last}".replace("  ", " ").strip()

        data.append([
            student.nisn,
            full_name,
            "Yes" if student.is_active else "No",
            student.na_reason or "-"
        ])

    # Table Styling
    # We calculate column widths to fit the page nicely
    # A4 width is roughly 595 points. Margins are 30+30=60. Usable = 535.
    col_widths = [100, 250, 50, 135] 

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    flowables.append(table)
    doc.build(
        flowables, 
        onFirstPage=draw_watermark, 
        onLaterPages=draw_watermark
    )

    # Return Response
    buf.seek(0)
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="student_report.pdf"'
    return response