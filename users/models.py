from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator / Ka. IPSRS'),
        ('engineer', 'Teknisi / Engineer (IPSRS)'),
        ('user_unit', 'Staf Unit / Ruangan (User)'),
    ]

    nip = models.CharField(
        max_length=30, 
        unique=True, 
        null=True, 
        blank=True, 
        verbose_name="NIP / Nomor Induk Pegawai"
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='engineer',
        verbose_name="Peran Sistem"
    )
    unit_location = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        help_text="Contoh: Ruang ICU, Radiologi, Poliklinik (Khusus User Unit)",
        verbose_name="Lokasi Penugasan / Unit"
    )
    phone_number = models.CharField(
        max_length=20, 
        null=True, 
        blank=True, 
        verbose_name="Nomor WhatsApp / HP"
    )

    def __str__(self):
        full_name = self.get_full_name()
        name_display = full_name if full_name else self.username
        return f"{name_display} ({self.get_role_display()})"