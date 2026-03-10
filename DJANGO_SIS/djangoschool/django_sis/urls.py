"""
URL configuration for django_sis project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from . import views
from debug_toolbar.toolbar import debug_toolbar_urls
from .admin import admin_statistics_view
# postgres stuff
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.models import User
from rest_framework import routers, serializers, viewsets
from admission.models import AcademicYear, Registration, SchoolData


class RegSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Registration
        # fields = ['url', 'username', 'email', 'is_staff']
        # fields = ['url', 'first_name', 'middle_name', 'last_name', 'place_of_birth', 'date_of_birth', 'gender', 'form_no', 'nisn', 'prev_school', 'prev_nis', 'birth_order', 'church_name', 'current_address', 'current_district', 'current_region', 'current_city', 'current_province', 'contact_whatsapp', 'contact_mobile', 'contact_email', 'contact_preference', 'mother_name', 'mother_nik', 'mother_education', 'mother_occupation', 'mother_address_same2applicant', 'mother_address', 'mother_district', 'mother_region', 'mother_city', 'mother_province', 'mother_phone', 'mother_mobile', 'mother_whatsapp', 'mother_email', 'father_name', 'father_nik', 'father_education']
        fields = ['first_name', 'middle_name', 'last_name']

class SchDataSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SchoolData
        fields = '__all__'

# ViewSets define the view behavior.
class RegViewSet(viewsets.ModelViewSet):
    queryset = Registration.objects.all()
    serializer_class = RegSerializer

class SchDataViewSet(viewsets.ModelViewSet):
    queryset = SchoolData.objects.all()
    serializer_class = SchDataSerializer

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'registrations', RegViewSet)
router.register(r'school_data', SchDataViewSet)


urlpatterns = [
    path(   # new
        "admin/statistics/",
        admin.site.admin_view(admin_statistics_view),
        name="admin-statistics"
    ),
    path("accounts/", include("account.urls")),
    path("admission/", include("admission.urls")),
    path("gradebook/", include("gradebook.urls")),
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("logout/", views.logout_view, name="logout"),
    path('api-auth/', include('rest_framework.urls')),
    path('api/', include(router.urls)),
] + debug_toolbar_urls()

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

