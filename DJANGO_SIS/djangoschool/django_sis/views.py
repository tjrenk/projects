from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

# @login_required
def home(request):
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