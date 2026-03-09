# -*- coding: utf-8 -*-

from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="adm-index"),
    path("registration-form/", views.AdmissionView.as_view(), name="registration-form"),
    path("get-filter-options/", views.get_filter_options, name="get-filter-options"),
    path("get_student_counts/", views.get_student_counts, name="get_student_counts"),
    path("student_table/", views.regist_table, name="student-table"),
    path("pdf_regist_table/", views.pdf_regist_table, name="pdf_regist_table")
    ]