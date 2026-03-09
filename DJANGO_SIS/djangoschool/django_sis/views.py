from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

# @login_required
def home(request):
    return render(request, 'index_new.html')

def logout_view(request):
    logout(request)
    return render(request, 'index_new.html')