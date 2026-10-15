from django import template
from django.core.paginator import Paginator
# Adjust the import below to match where your model actually lives
from gradebook.models import *
from admission.models import *

register = template.Library()


BREADCRUMB_MAP = {
    'gb-index': (('Dashboard', None),),
    'grade-entry': (('Data Entry', None), ('Student Grade', 'grade-entry')),
    'student-attendance': (('Data Entry', None), ('Student Attendance', 'student-attendance')),
    'report-card': (('Data Entry', None), ("Hr Teacher's Comments", 'report-card')),
    'rubric-entry': (('Data Entry', None), ('Student Behaviour', 'rubric-entry')),
    'rp-comment': (('Data Entry', None), ("Academic Comments", 'rp-comment')),
    'dorm-rubric-entry': (('Data Entry', None), ("Student Behaviour in Dormitory", 'dorm-rubric-entry')),
    'extra-report': (('Data Entry', None), ('Extracurricular Grade', 'extra-report')),
    'personal-dev': (('Data Entry', None), ('Personal Development Grade', 'personal-dev')),
    'cpmp-create': (('Data Entry', None), ('Lesson Outcome', 'cpmp-create')),
    'assignment-avg-wizard': (('Processes', None), ('Final Grade Avg', 'assignment-avg-wizard')),
    'grade-entry-table': (('Reporting', None), ('Student Grade', 'grade-entry-table')),
    'ge-edit': (('Reporting', None), ('Student Grade', 'grade-entry-table')),
    'ge-delete': (('Reporting', None), ('Student Grade Delete', None)),
    'report-card-table': (('Reporting', None), ("Hr Teacher's Comments", 'report-card-table')),
    'tc-view': (('Reporting', None), ("Hr Teacher's Comments", 'report-card-table')),
    'tc-del': (('Reporting', None), ("Hr Teacher's Delete", None)),
    'teacher-notes-table': (('Reporting', None), ("Academic Comments", 'teacher-notes-table')),
    'teacher-notes-edit': (('Reporting', None), ("Academic Comments", 'teacher-notes-table')),
    'teacher-notes-del': (('Reporting', None), ("Academic Comment Delete", None)),
    'report-extra-table': (('Reporting', None), ("Extracurricular Table", 'report-extra-table')),
    'report-extra-edit': (('Reporting', None), ("Extracurricular Table", 'report-extra-table')),
    'report-extra-del': (('Reporting', None), ("Extracurricular Grade Delete", None)),
    'rcard-ledger': (('Reporting', None), ('Report Card Ledger', 'rcard-ledger')),
    'assignment-ledger': (('Reporting', None), ('Assignment Ledger', 'assignment-ledger')),
    'pdev-table': (('Reporting', None), ('Personal Development Table', 'pdev-table')),
    'pdev-edit': (('Reporting', None), ('Personal Development Table', 'pdev-table')),
    'pdev-del': (('Reporting', None), ("Personal Development Grade Delete", None)),
    'rubric-table': (('Reporting', None), ('Student Behavior Grades Table', 'rubric-table')),
    'rubric-edit': (('Reporting', None), ('Student Behavior Grades Table', 'rubric-table')),
    'rubric-delete': (('Reporting', None), ('Student Behavior Grade Delete', None)),
    'class-attendance-ledger': (('Reporting', None), ('Attendance Ledger', 'class-attendance-ledger')),
    'hr-monitor-table': (('Reporting', None), ('Hr Teacher Grade Monitor', 'hr-monitor-table')),
}

@register.simple_tag(takes_context=True)
def get_breadcrumb(context):
    request = context['request']
    url_name = request.resolver_match.url_name if request.resolver_match else None
    crumb = BREADCRUMB_MAP.get(url_name, ())
    extra = context.get('breadcrumb_extra')
    if extra:
        crumb = crumb + ((extra, None),)
    return crumb # tadi cuma return 2 value doang, tambahin 1 lg buat jaga2 sp tau mau ditambahin

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
    pnation = Paginator(attendance_qs, 9)
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


@register.simple_tag(takes_context=True)
def is_dorm_mentor(context):
    request = context['request']

    if not request.user.is_authenticated:
        return False


    return request.user.groups.filter(name='Dorm Mentor').exists()

@register.simple_tag(takes_context=True)
def is_counselor(context):
    request = context['request']

    if not request.user.is_authenticated:
        return False


    return request.user.groups.filter(name='Counselor').exists()


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