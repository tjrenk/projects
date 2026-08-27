from django import template
from django.core.paginator import Paginator
# Adjust the import below to match where your model actually lives
from gradebook.models import *
from admission.models import *

register = template.Library()


# maps url_name -> (Section, Page Label)
BREADCRUMB_MAP = {
    'gb-index': ('Gradebook', 'Dashboard'),
    'grade-entry': ('Data Entry', 'Student Grade'),
    'student-attendance': ('Data Entry', 'Student Attendance'),
    'report-card': ('Data Entry', "Hr Teacher's Comments"),
    'rubric-entry': ('Data Entry', 'Student Behaviour'),
    'rp-comment': ('Data Entry', "Teacher's Comments"),
    'extra-report': ('Data Entry', 'Extracurricular Grade'),
    'personal-dev': ('Data Entry', 'Personal Development Grade'),
    'cpmp-create': ('Data Entry', 'Lesson Plan'),
    'assignment-avg-wizard': ('Processes', 'Final Grade Avg'),
    'grade-entry-table': ('Reporting', 'Student Grade'),
    'ge-edit': ('Reporting', 'Student Grade Edit'),
    'ge-delete': ('Reporting', 'Student Grade Delete'),
    'report-card-table': ('Reporting', "Hr Teacher's Comments"),
    'tc-view': ('Reporting', "View Hr Teacher's Comments"),
    'tc-del': ('Reporting', "Hr Teacher's Delete"),
    'teacher-notes-table': ('Reporting', "Academic Comments"),
    'teacher-notes-edit': ('Reporting', "Academic Comment Edit"),
    'teacher-notes-del': ('Reporting', "Academic Comment Delete"),
    'report-extra-table': ('Reporting', "Extracurricular Table"),
    'report-extra-edit': ('Reporting', "Extracurricular Grade Edit"),
    'report-extra-del': ('Reporting', "Extracurricular Grade Delete"),
    'rcard-ledger': ('Reporting', 'Report Card Ledger'),
    'assignment-ledger': ('Reporting', 'Assignment Ledger'),
    'pdev-table': ('Reporting', 'Personal Development Table'),
    'pdev-edit': ('Reporting', "Personal Development Grade Edit"),
    'pdev-del': ('Reporting', "Personal Development Grade Delete"),
    'rubric-table': ('Reporting', 'Student Behavior Grades Table'),
    'rubric-edit': ('Reporting', 'Student Behavior Grade Edit'),
    'rubric-delete': ('Reporting', 'Student Behavior Grade Delete'),
}

@register.simple_tag(takes_context=True)
def get_breadcrumb(context):
    request = context['request']
    url_name = request.resolver_match.url_name if request.resolver_match else None
    return BREADCRUMB_MAP.get(url_name, (None, None, None)) # tadi cuma return 2 value doang, tambahin 1 lg buat jaga2 sp tau mau ditambahin

@register.filter
def in_list(value, arg):
    """
    Exact-match membership check against a comma-separated string.
    Usage: {% if some_value|in_list:"a,b,c" %}
    """
    return str(value) in [x.strip() for x in arg.split(',')]

# We point this tag to the specific HTML template you want to insert
@register.inclusion_tag('partials/gradebook/attendance_list_homepage.html', takes_context=True)
def render_attendance_dashboard_widget(context):
    request = context['request']

    # 1. Fetch the data (Logic copied from your view)
    # Added .order_by('-id') so you see the newest items first
    attendance_qs = StudentAttendance.objects.select_related('student').order_by('-id')

    # 2. Handle Pagination
    # Note: Pagination on a dashboard can be tricky if multiple widgets use it.
    # If you just want the "Latest 10", you could skip Paginator and use [:10]
    pnation = Paginator(attendance_qs, 15)
    page = request.GET.get('page')
    pnation_attend = pnation.get_page(page)

    # 3. Return the context expected by your template
    return {
        'pnation_attend': pnation_attend,
        'attendance': attendance_qs,
        'request': request,
    }

@register.inclusion_tag('admin/students_list.html', takes_context=True)
def all_students_stats(context):
    total_students = Student.objects.count()
    context['total_students'] = total_students
    return context


@register.simple_tag(takes_context=True)
def is_homeroom_teacher(context):
    request = context['request']

    if not request.user.is_authenticated:
        return False


    return Class.objects.filter(
        teacher__user=request.user,
        # is_home_class=True,
    ).first()


@register.inclusion_tag('partials/gradebook/sortable_th.html')
def sortable_header(col, label, sort_by, sort_dir):
    if sort_by == col:
        next_dir = 'desc' if sort_dir == 'asc' else 'asc'
        icon = 'fa-sort-up' if sort_dir == 'asc' else 'fa-sort-down'
    else:
        next_dir = 'asc'
        icon = 'fa-sort'

    return {
        'col': col,
        'label': label,
        'next_dir': next_dir,
        'icon': icon,
        'is_active': sort_by == col,
    }