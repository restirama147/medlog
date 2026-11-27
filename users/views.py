from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

def root_redirect_view(request):
    """Mengarahkan akses root URL '/' sesuai status login."""
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    return redirect('users:login')


def login_view(request):
    # Jika user sudah terautentikasi, alihkan langsung
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        username_input = request.POST.get('username')
        password_input = request.POST.get('password')

        user = authenticate(request, username=username_input, password=password_input)

        if user is not None:
            if not user.is_active:
                messages.error(request, 'Akun Anda sedang nonaktif. Hubungi Admin IPSRS.')
                return render(request, 'login.html')

            login(request, user)
            messages.success(request, f'Selamat datang, {user.get_full_name() or user.username}!')
            
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            return redirect_by_role(user)
        else:
            messages.error(request, 'Username atau password salah!')

    return render(request, 'login.html')


def redirect_by_role(user):
    """Helper function untuk mengarahkan user berdasarkan perannya."""
    return redirect('dashboard:view')


def logout_view(request):
    logout(request)
    messages.info(request, 'Anda telah keluar dari sistem Medlog.')
    return redirect('users:login')
