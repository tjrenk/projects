from django.urls import path

from . import views

urlpatterns = [
    path("", views.gb_index, name="gb-index"),
    path("teachers", views.teacher_list, name="teacher-list"),
    path("course", views.course_list, name="course-list"),
    # path("grade-entry", views.grade_entry, name="grade-entry"),
    path("grade-entry", views.GradeEntryForm.as_view(), name="grade-entry"),
    path("attendance", views.attendance, name="student-attendance"),
    path("midterm_pdf", views.midterm_report, name="midterm_report"),
    path("midterm_pdf_real/<int:student_id>/", views.midterm_report_pdf, name="midterm_report_pdf"),
    path("report-card", views.ReportCardForm.as_view(), name="report-card"),
    path('get-teachers-ge/',views.get_teachers, name='get_teachers-ge'),
    path('get-courses/', views.get_courses, name='get_courses'),
    path('get-period-ge/', views.get_period_ge, name='get_period_ge'),
    path('get-courses-ge/', views.get_courses, name='get_courses_ge'),
    path('get-subjects-ge/', views.get_subjects_ge, name='get_subjects_ge'),
    path('get-levels-ge/', views.get_levels_ge, name='get_levels_ge'),
    path('get-assignment-types-ge/', views.get_assignment_types_ge, name='get_assignment_types_ge'),
    path('toggle-na-reason/', views.toggle_na_reason, name='toggle_na_reason'),
    path('grade-entry-table', views.ge_table, name='grade-entry-table'),
    path('ge-edit/<int:pk>', views.ge_edit, name='ge-edit'),
    path('ge-delete/<int:pk>', views.ge_del, name='ge-delete'),
    path('report-card-table', views.tc_table, name='report-card-table'),
    path('tc-edit/<int:pk>', views.tc_edit, name='tc-edit'),
    path('tc-del/<int:pk>', views.tc_del, name='tc-del'),
    path('attendance-list-homepage', views.attendance_list_admin, name='attendance-list-homepage'),
    path('rcard-ledger/', views.ReportCardGradeSummary.as_view(), name='rcard-ledger'),
    path('get-level-reportcard/', views.get_level_reportcard, name='get_level_reportcard'),
    path('get-period-reportcard/', views.get_period_reportcard, name='get_period_reportcard'),   
    # path('reportcard_summary/', views.report_card_summary, name='reportcard_summary'),
    # path("finished-screen", views.finished, name="finished-screen")
    ]