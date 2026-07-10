from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.signals import user_logged_in
from django.urls import reverse_lazy
from .forms import CustomPasswordChangeForm
from admission.models import Teacher

# @login_required
def home(request):
    user = request.user
    teacher = request.user.groups.filter(name="Teachers").exists()
    if teacher:
        return redirect('gb-index')
    else:
        return render(request, 'index_new.html')

def logout_view(request):
    logout(request)
    return render(request, 'index_new.html')

# def gb_index(request):
#     user = request.user
#     is_homeroom = Class.objects.filter(
#             teacher__user=user,
#             is_home_class=True).exists()
#
#     return render(request, context)

class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'registration/password_change.html'
    success_url = reverse_lazy('password_change_done')