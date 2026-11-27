from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    
    # Kolom yang ditampilkan pada daftar user di Django Admin
    list_display = ('username', 'nip', 'first_name', 'last_name', 'role', 'unit_location', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'nip', 'first_name', 'last_name')
    
    # Form edit user di Django Admin
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Kepegawaian & IPSRS', {
            'fields': ('nip', 'role', 'unit_location', 'phone_number')
        }),
    )
    
    # Form tambah user baru di Django Admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informasi Kepegawaian & IPSRS', {
            'fields': ('nip', 'role', 'unit_location', 'phone_number')
        }),
    )