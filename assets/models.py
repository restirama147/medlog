from django.db import models
from django.conf import settings


class SPORecord(models.Model):
    """Riwayat revisi Standar Prosedur Operasional (SPO) per aset."""
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE, related_name='spo_records', verbose_name="Aset Terkait")
    title = models.CharField(max_length=200, verbose_name="Judul / Versi SPO", default="SPO")
    version = models.CharField(max_length=50, blank=True, default="1.0", verbose_name="Versi")
    file = models.FileField(upload_to='spo_documents/', verbose_name="File PDF SPO")
    notes = models.TextField(blank=True, default="", verbose_name="Catatan Revisi")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='spo_uploads', verbose_name="Diunggah Oleh"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Tanggal Unggah")

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "SPO Record"
        verbose_name_plural = "SPO Records"

    def __str__(self):
        return f"{self.asset.name} - SPO {self.version} ({self.uploaded_at.strftime('%d %b %Y')})"

class Category(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name="Nama Kategori Alkes")
    slug = models.SlugField(max_length=150, blank=True, null=True, unique=True)
    description = models.TextField(blank=True, default="")
    k3_notes = models.JSONField(default=list, blank=True, verbose_name="Catatan K3 / Pedoman")
    accessories_template = models.JSONField(default=list, blank=True, verbose_name="Template Aksesoris (Bagian 3)")
    inspection_template = models.JSONField(default=list, blank=True, verbose_name="Template Pemeriksaan Fisik & Fungsi (Bagian 4)")

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Asset(models.Model):
    STATUS_CHOICES = [
        ('active', 'Layak Pakai / Beroperasi'),
        ('maintenance', 'Dalam Perawatan'),
        ('repair', 'Butuh Perbaikan'),
        ('broken', 'Rusak'),
        ('retired', 'Afkir / Disimpan'),
    ]

    CALIBRATION_CHOICES = [
        ('active', 'Aktif / Terkalibrasi'),
        ('process', 'Proses Didaftarkan'),
        ('expired', 'Expired'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="ID Aset / Kode")
    name = models.CharField(max_length=200, verbose_name="Nama Alat")
    brand = models.CharField(max_length=100, blank=True, default="", verbose_name="Merk")
    model_type = models.CharField(max_length=100, blank=True, default="", verbose_name="Model / Tipe")
    serial_number = models.CharField(max_length=100, blank=True, default="", verbose_name="Nomor Seri (SN)")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    location = models.CharField(max_length=200, verbose_name="Lokasi / Ruangan")
    installation_year = models.IntegerField(null=True, blank=True, verbose_name="Tahun Pemasangan")
    purchase_date = models.DateField(null=True, blank=True, verbose_name="Tanggal Pembelian")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Status Kinerja")
    calibration_status = models.CharField(max_length=20, choices=CALIBRATION_CHOICES, default='active', verbose_name="Status Kalibrasi")
    calibration_expiry = models.DateField(null=True, blank=True, verbose_name="Masa Berlaku Kalibrasi")
    spo_text = models.TextField(blank=True, default="", verbose_name="Standar Prosedur Operasional")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        brand_info = f" ({self.brand} {self.model_type})".strip() if self.brand or self.model_type else ""
        return f"{self.code} - {self.name}{brand_info}"

    @property
    def full_brand(self):
        parts = [p for p in [self.brand, self.model_type] if p]
        return " ".join(parts) if parts else "-"

    @property
    def status_label(self):
        mapping = {
            'active': 'Layak Pakai',
            'maintenance': 'Maintenance',
            'repair': 'Perbaikan',
            'broken': 'Rusak',
            'retired': 'Afkir',
        }
        return mapping.get(self.status, self.get_status_display())

    @property
    def status_css(self):
        if self.status == 'active':
            return 'success'
        elif self.status == 'maintenance':
            return 'warning'
        elif self.status in ['repair', 'broken']:
            return 'danger'
        return 'secondary'

    @property
    def calib_label(self):
        mapping = {
            'active': 'Aktif',
            'process': 'Proses',
            'expired': 'Expired',
        }
        return mapping.get(self.calibration_status, self.calibration_status)

    @property
    def calib_color(self):
        if self.calibration_status == 'active':
            return 'var(--success)'
        elif self.calibration_status == 'process':
            return 'var(--warning)'
        return 'var(--danger)'
