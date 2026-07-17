from django.urls import path

from . import views

urlpatterns = [
    # MAIN ONES
    path("", views.gb_index, name="gb-index"),
    path("teachers", views.teacher_list, name="teacher-list"),
    path("course", views.course_list, name="course-list"),
    path("attendance", views.attendance, name="student-attendance"),
    path("midterm_pdf", views.midterm_report, name="midterm_report"),
    path("midterm_pdf_real/<int:student_id>/", views.midterm_report_pdf, name="midterm_report_pdf"),
    path('attendance-list-homepage', views.attendance_list_admin, name='attendance-list-homepage'),
    
    # GRADE ENTRY
    path("grade-entry", views.GradeEntryForm.as_view(), name="grade-entry"),
    path('grade-entry-table', views.ge_table, name='grade-entry-table'),
    path('ge-edit/<int:pk>', views.ge_edit, name='ge-edit'),
    path('ge-delete/<int:pk>', views.ge_del, name='ge-delete'),
    path('get-teachers-ge/',views.get_teachers, name='get_teachers-ge'),
    path('get-courses/', views.get_courses, name='get_courses'),
    path('get-period-ge/', views.get_period_ge, name='get_period_ge'),
    path('get-courses-ge/', views.get_courses, name='get_courses_ge'),
    path('get-subjects-ge/', views.get_subjects_ge, name='get_subjects_ge'),
    path('get-kelas-ge/', views.get_kelas_ge, name='get_kelas_ge'),
    path('get-levels-ge/', views.get_levels_ge, name='get_levels_ge'),
    path('get-assignment-types-ge/', views.get_assignment_types_ge, name='get_assignment_types_ge'),
    path('get-cpmp-ge/', views.get_cpmp_target_ge, name='get-cpmp-ge'),
    path('print-grade-list/<int:pk>', views.print_grade_list, name='print-grade-list'),

    # TEACHER COMMENTS / REPORT CARD
    path("report-card", views.ReportCardForm.as_view(), name="report-card"),
    path('report-card-table', views.tc_table, name='report-card-table'),
    path('tc-view/<int:pk>', views.tc_view, name='tc-view'),
    path('tc-del/<int:pk>', views.tc_del, name='tc-del'),
    path('get-level-reportcard/', views.get_level_reportcard, name='get_level_reportcard'),
    path('get-period-reportcard/', views.get_period_reportcard, name='get_period_reportcard'), 




    path('toggle-na-reason/', views.toggle_na_reason, name='toggle_na_reason'),

    # RUBRIC ENTRY
    path('rubric-entry/', views.RubricEntryWizard.as_view(), name="rubric-entry"),
    path('student-behavior-grading/<int:pk>', views.student_behavior_grading, name='student-behavior-grading'),
    path('get-kelas-rubric/', views.get_kelas_rubric, name='get-kelas-rubric'),
    path('rubric-table/', views.rb_table, name='rubric-table'),
    path('rubric-edit/<int:pk>', views.rb_edit, name='rubric-edit'),
    path('rubric-delete/<int:pk>', views.rb_del, name='rubric-delete'),
    path('rubric-pdf/<int:pk>', views.rb_pdf, name='rubric-pdf'),

    # EXTRA REPORT
    path('extra-report/', views.ExtraReportWizard.as_view(), name='extra-report'),
    path('report_extrac/<int:pk>',views.student_act_extra_grading, name='report_extrac'),
    path('report_other/<int:pk>',views.student_act_other_grading, name='report_other'),
    path('get-period-extra/', views.get_period_extra, name='get-period-extra'),
    path('get-level-extra/', views.get_level_extra, name='get-level-extra'),
    path('get-kelas-extra/', views.get_kelas_extra, name='get-kelas-extra'),
    # path('get-extra-type/', views.get_extra_type, name='get-extra-type'),
    path('get-teachers-extra/', views.get_teachers_extra, name='get-teachers-extra'),

    # EXTRA INFO
    # path('extra-info/', views.ExtraInfoWizard.as_view(), name='extra-info'),
    path('get-act-subj/', views.get_act_subj, name='get-act-subj'),

    # GRADES WIZARD
    path('grades-wizard/', views.GradesWizard.as_view(), name='grades-wizard'),

    # TOTAL GRADES
    path('total_grade/', views.TotalGrading.as_view(), name='total_grade'),
    path('get-subject-tgrade/', views.get_subject_totalg, name='get-subject-tgrade'),
    path('get-academic_year-tgrade/', views.get_academic_year_totalg, name='get-academic_year-tgrade'),
    path('get-period-tgrade/', views.get_period_tgrade, name='get-period_tgrade'),

    # REPORT CARD LEDGER
    path('rcard-ledger/', views.ReportCardGradeSummary.as_view(), name='rcard-ledger'),
    path('rcard-ledger-alt/', views.grade_ledger, name='rcard-ledger-alt'),
    path('get_period_ledger/', views.get_period_ledger, name='get_period_ledger'),


    # CHARACTER DEVELOPMENT GRADE ENTRY
    path('personal-dev/', views.PersonalDevWizard.as_view(), name='personal-dev'),
    path('get-period-pd/', views.get_period_pd, name='get_period_pd'),
    path('get-kelas-pd/', views.get_kelas_pd, name='get_kelas_pd'),
    path('get-levels-pd/', views.get_levels_pd, name='get_levels_pd'),
    path('get-student-pd/', views.get_student_pd, name='get_student_pd'),
    path('pdev-table/', views.pdev_table, name='pdev-table'),
    path('pdev-edit/<int:pk>', views.pdev_edit, name='pdev-edit'),
    path('pdev-print/<int:pk>', views.print_pdev_pdf, name='pdev-print'),
    path('pdev-del/<int:pk>', views.pdev_del, name='pdev-del'),
    

    # LEAVE THIS COMMENTED, JUST IN CASE
    # path('reportcard_summary/', views.report_card_summary, name='reportcard_summary'),
    # path("finished-screen", views.finished, name="finished-screen")
    # path("grade-entry", views.grade_entry, name="grade-entry"),
    path('get-period-grades/', views.get_period_grades, name='get_period_grades'),
    path('get-level-grades/', views.get_level_grades, name='get_level_grades'),
    path('assignm_avg/', views.assignm_avg, name='assignm_avg'),
    path('assignment-avg-wizard/', views.AssignmentAvgWizard.as_view(), name='assignment-avg-wizard'),
    path('get-period-assignment-avg/', views.get_period_assignment_avg, name='get-period-assignment-avg'),
    path('get-subjects-assignment-avg/', views.get_subjects_assignment_avg, name='get-subjects-assignment-avg'),
    path('get-courses-assignment-avg/', views.get_courses_assignment_avg, name='get-courses-assignment-avg'),
    path('save_grade_avg/', views.save_assignment_results, name='save_grade_avg')
]
