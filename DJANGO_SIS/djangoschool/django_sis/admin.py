from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.urls import path
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.paginator import Paginator


@staff_member_required
def admin_statistics_view(request):
    return render(request, "admin/statistics.html", {
        "title": "Statistics"
    })


class CustomAdminSite(admin.AdminSite):
    def get_app_list(self, request, _=None):
        app_list = super().get_app_list(request)
        app_list += [
            {
                "name": "My Custom App",
                "app_label": "my_custom_app",
                "models": [
                    {
                        "name": "Statistics",
                        "object_name": "statistics",
                        "admin_url": "/admin/statistics",
                        "view_only": True,
                    }
                ],
            }
        ]
        return app_list

    def get_urls(self):
        urls = super().get_urls()
        urls += [
            path("statistics/", admin_statistics_view, name="admin-statistics"),
        ]
        return urls


class LogEntryAdmin(admin.ModelAdmin):
    # Prevent modifying logs from the panel for security
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ['action_time', 'user', 'content_type', 'object_repr', 'action_flag_description']
    list_filter = ['action_time', 'user', 'action_flag']
    search_fields = ['object_repr', 'change_message']

    def action_flag_description(self, obj):
        if obj.action_flag == ADDITION:
            return format_html('<span style="color: green;">Created</span>')
        elif obj.action_flag == CHANGE:
            return format_html('<span style="color: orange;">Updated</span>')
        elif obj.action_flag == DELETION:
            return format_html('<span style="color: red;">Deleted</span>')
        return "Unknown"

    action_flag_description.short_description = 'Action Type'

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    object_history_template = "admin/user/user_activity_history.html"

    def history_view(self, request, object_id, extra_context=None):
        response = super().history_view(request, object_id, extra_context)
        ctx = getattr(response, 'context_data', None)
        if ctx and 'object' in ctx:                      # skips the "not found" redirect
            qs = (LogEntry.objects.filter(user=ctx['object'])
                  .select_related('content_type')
                  .order_by('-action_time'))
            ctx['action_list'] = Paginator(qs, 100).get_page(request.GET.get('p'))
        return response