from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Daftar URL yang BOLEH diakses tanpa login (bebas akses)
        exempt_urls = [
            reverse('users:login'),
            '/assets/p/',       # Halaman publik info aset, sertifikat kalibrasi & SPO melalui QR Code
            '/maintenance/',    # Detail lembar kerja maintenance / perbaikan publik (atau cetak PDF)
            '/media/',          # File PDF sertifikat & SPO untuk publik
        ]

        # Jika user belum login dan mencoba mengakses halaman terproteksi
        if not request.user.is_authenticated:
            # Pastikan path yang diakses bukan halaman login agar tidak terjadi infinite loop
            if not any(request.path.startswith(url) for url in exempt_urls):
                return redirect('users:login')

        response = self.get_response(request)
        return response