from django.db import models
from django.conf import settings
from assets.models import Asset

class MaintenanceRecord(models.Model):
    TYPE_CHOICES = [
        ('preventive', 'Maintenance Preventif Rutin'),
        ('corrective', 'Tindakan Perbaikan / Korektif'),
    ]

    URGENCY_CHOICES = [
        ('low', 'Rendah (Minor / Estetika)'),
        ('medium', 'Sedang (Fungsi Terbatas)'),
        ('high', 'Tinggi / Emergency (Breakdown)'),
    ]

    RESULT_CHOICES = [
        ('Layak Pakai', 'Layak Pakai / Selesai'),
        ('Pending Part', 'Menunggu Suku Cadang (Pending Part)'),
        ('Afkir / Rusak Berat', 'Tidak Dapat Diperbaiki (Rekomendasi Afkir)'),
        ('Tidak Layak', 'Tidak Layak Pakai'),
    ]

    work_order_no = models.CharField(max_length=60, unique=True, verbose_name="No. Work Order / Perbaikan")
    maintenance_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='preventive', verbose_name="Jenis Pekerjaan")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='maintenance_records', verbose_name="Aset Terkait")
    
    # Tanggal & Waktu Pelaksanaan
    date = models.DateField(verbose_name="Tanggal Pelaksanaan / Lapor")
    start_time = models.TimeField(null=True, blank=True, verbose_name="Waktu Mulai")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Waktu Selesai")
    
    # Pihak Terlibat
    reporter_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Pelapor / Staf Ruangan")
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenances', verbose_name="Akun Teknisi")
    technician_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Nama Teknisi / Vendor")
    
    # Detail Perbaikan Korektif
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='medium', verbose_name="Tingkat Urgensi")
    damage_description = models.TextField(blank=True, default="", verbose_name="Deskripsi Kerusakan / Keluhan User")
    root_cause = models.TextField(blank=True, default="", verbose_name="Inti Kerusakan (Root Cause)")
    action_taken = models.TextField(blank=True, default="", verbose_name="Tindakan Pemeliharaan / Perbaikan")
    
    # Hasil & Catatan
    result_status = models.CharField(max_length=40, choices=RESULT_CHOICES, default='Layak Pakai', verbose_name="Hasil Kinerja / Status")
    notes = models.TextField(blank=True, default="", verbose_name="Catatan Pemeliharaan")

    # Checklist JSON (Preventif)
    accessories_check = models.JSONField(default=dict, blank=True, verbose_name="Uji Kelengkapan Aksesoris")
    physical_functional_check = models.JSONField(default=dict, blank=True, verbose_name="Pemeriksaan Fisik & Fungsi")

    # Tanda Tangan Digital (Base64 URL)
    signature_user = models.TextField(blank=True, default="", verbose_name="TTD User Ruangan")
    signature_user_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Nama User Ruangan")
    signature_engineer = models.TextField(blank=True, default="", verbose_name="TTD Engineer IPSRS")
    signature_engineer_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Nama Engineer IPSRS")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.work_order_no} - {self.asset.name} ({self.get_maintenance_type_display()})"

    @property
    def status_css(self):
        if self.result_status == 'Layak Pakai':
            return 'success'
        elif self.result_status == 'Pending Part':
            return 'warning'
        return 'danger'


class SparePartReplacement(models.Model):
    maintenance_record = models.ForeignKey(MaintenanceRecord, on_delete=models.CASCADE, related_name='spareparts')
    part_name = models.CharField(max_length=200, verbose_name="Nama Komponen / Sparepart")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Jumlah")
    serial_number = models.CharField(max_length=100, blank=True, default="", verbose_name="No. Seri Sparepart")

    def __str__(self):
        return f"{self.part_name} ({self.quantity} pcs) - {self.maintenance_record.work_order_no}"


class CalibrationRecord(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='calibrations', verbose_name="Aset Terkait")
    test_date = models.DateField(verbose_name="Tanggal Pengujian")
    testing_institution = models.CharField(max_length=200, verbose_name="Lembaga Penguji")
    certificate_no = models.CharField(max_length=100, verbose_name="No. Sertifikat")
    result = models.CharField(max_length=100, default='Lolos Kalibrasi', verbose_name="Hasil Kinerja")
    valid_until = models.DateField(verbose_name="Masa Berlaku")
    notes = models.TextField(blank=True, default="", verbose_name="Catatan")
    certificate_file = models.FileField(upload_to='certificates/', blank=True, null=True, verbose_name="File Sertifikat")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['-test_date']

    def __str__(self):
        return f"{self.certificate_no} - {self.asset.name} (Hingga: {self.valid_until})"
