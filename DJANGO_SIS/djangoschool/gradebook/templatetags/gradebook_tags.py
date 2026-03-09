from django import template
from django.core.paginator import Paginator
# Adjust the import below to match where your model actually lives
from gradebook.models import StudentAttendance 
from admission.models import *

register = template.Library()

# We point this tag to the specific HTML template you want to insert
@register.inclusion_tag('partials/gradebook/attendance_list_homepage.html', takes_context=True)
def render_attendance_dashboard_widget(context):
    request = context['request']

    # 1. Fetch the data (Logic copied from your view)
    # Added .order_by('-id') so you see the newest items first
    attendance_qs = StudentAttendance.objects.all().order_by('-id')

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