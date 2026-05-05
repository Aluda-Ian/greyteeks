from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login
from django.http import HttpResponseRedirect
from django.urls import reverse

def custom_login_view(request):
	User = get_user_model()
	admin_users = User.objects.filter(is_active=True).filter(is_superuser=True) | User.objects.filter(is_active=True).filter(is_staff=True)
	admin_users = admin_users.distinct()
	form = AuthenticationForm(request, data=request.POST or None)
	if request.method == 'POST' and form.is_valid():
		auth_login(request, form.get_user())
		return HttpResponseRedirect(reverse('dashboard'))
	return render(request, 'registration/login.html', {
		'form': form,
		'admin_users': admin_users,
	})
