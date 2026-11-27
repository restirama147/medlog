import io
import json
import base64
import qrcode
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db import models
from django.urls import reverse
from .models import Asset, Category, SPORecord
from maintenance.models import MaintenanceRecord, SparePartReplacement, CalibrationRecord
from django.utils.dateparse import parse_date


@login_required
def index(request):
    room_filter = request.GET.get('room', 'ALL')
    search_query = request.GET.get('q', '').strip()

    assets = Asset.objects.select_related('category').all()

    if room_filter != 'ALL':
        assets = assets.filter(location__icontains=room_filter)

    if search_query:
        assets = assets.filter(
            models.Q(name__icontains=search_query) |
            models.Q(brand__icontains=search_query) |
            models.Q(serial_number__icontains=search_query) |
            models.Q(code__icontains=search_query) |
            models.Q(location__icontains=search_query)
        )

    categories = Category.objects.all()

    context = {
        'assets': assets,
        'categories': categories,
        'room_filter': room_filter,
        'search_query': search_query,
    }
    return render(request, 'assets/index.html', context)


@login_required
@require_POST
def create_asset_ajax(request):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        code = data.get('code') or data.get('asset_id')
        name = data.get('name')
        brand = data.get('brand', '')
        sn = data.get('sn') or data.get('serial_number', '')
        location = data.get('location', '')
        year = data.get('installation_year') or data.get('year')
        status_raw = data.get('status', 'Layak Pakai')
        calib_raw = data.get('calibration_status', 'Aktif')

        if not code or not name:
            return JsonResponse({'status': 'error', 'message': 'Kode Aset dan Nama Alat wajib diisi!'}, status=400)

        # Mapping status kinerja
        status_map = {
            'Layak Pakai': 'active',
            'active': 'active',
            'Maintenance': 'maintenance',
            'maintenance': 'maintenance',
            'Perbaikan': 'repair',
            'repair': 'repair',
            'broken': 'broken',
            'Afkir': 'retired',
            'retired': 'retired',
        }
        status = status_map.get(status_raw, 'active')

        # Mapping status kalibrasi
        calib_map = {
            'Aktif': 'active',
            'active': 'active',
            'Proses': 'process',
            'process': 'process',
            'Expired': 'expired',
            'expired': 'expired',
        }
        calib_status = calib_map.get(calib_raw, 'active')

        year_val = int(year) if year and str(year).isdigit() else timezone.now().year

        cat_id = data.get('category_id')
        cat_name = data.get('category_name')
        category = None
        if cat_id and str(cat_id).isdigit():
            category = Category.objects.filter(id=int(cat_id)).first()
        elif cat_name:
            category = Category.objects.filter(name__icontains=cat_name).first()
        if not category and name:
            category = Category.objects.filter(name__icontains=name).first()

        asset, created = Asset.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'brand': brand,
                'serial_number': sn,
                'location': location,
                'installation_year': year_val,
                'status': status,
                'calibration_status': calib_status,
                'category': category,
            }
        )

        return JsonResponse({
            'status': 'success',
            'message': f"Aset {asset.name} ({asset.code}) berhasil disimpan!",
            'asset': {
                'id': asset.id,
                'code': asset.code,
                'name': asset.name,
                'brand': asset.full_brand,
                'sn': asset.serial_number,
                'location': asset.location,
                'status_label': asset.status_label,
                'status_css': asset.status_css,
                'calib_label': asset.calib_label,
                'calib_color': asset.calib_color,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def api_asset_detail(request, pk):
    asset = get_object_or_404(Asset, pk=pk)

    # Riwayat Maintenance
    maintenances = []
    for m in asset.maintenance_records.all():
        maintenances.append({
            'id': m.id,
            'wo_no': m.work_order_no,
            'date': m.date.strftime('%d %b %Y'),
            'type': m.get_maintenance_type_display(),
            'technician': m.technician_name or (m.technician.get_full_name() if m.technician else 'Teknisi IPSRS'),
            'status': m.result_status,
            'status_css': m.status_css,
        })

    # Riwayat Kalibrasi
    calibrations = []
    for c in asset.calibrations.all():
        cert_url = c.certificate_file.url if c.certificate_file else None
        calibrations.append({
            'id': c.id,
            'test_date': c.test_date.strftime('%d %b %Y'),
            'institution': c.testing_institution,
            'certificate_no': c.certificate_no,
            'result': c.result,
            'valid_until': c.valid_until.strftime('%d %b %Y'),
            'upload_date': c.created_at.strftime('%d %b %Y') if c.created_at else '-',
            'cert_url': cert_url,
        })

    # Riwayat SPO
    spo_records = []
    for s in asset.spo_records.all():
        spo_records.append({
            'id': s.id,
            'title': s.title,
            'version': s.version,
            'notes': s.notes,
            'uploaded_at': s.uploaded_at.strftime('%d %b %Y %H:%M'),
            'uploaded_by': s.uploaded_by.get_full_name() if s.uploaded_by else 'Admin',
            'file_url': s.file.url if s.file else None,
        })

    data = {
        'id': asset.id,
        'code': asset.code,
        'name': asset.name,
        'brand': asset.full_brand,
        'sn': asset.serial_number,
        'location': asset.location,
        'year': asset.installation_year or '-',
        'status': asset.status,
        'status_label': asset.status_label,
        'status_css': asset.status_css,
        'calibration_status': asset.calib_label,
        'calibration_color': asset.calib_color,
        'spo_text': asset.spo_text,
        'maintenances': maintenances,
        'calibrations': calibrations,
        'spo_records': spo_records,
    }
    return JsonResponse(data)


@login_required
@require_POST
def save_corrective_action(request):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        asset_id = data.get('asset_id')
        sn = data.get('sn')
        code = data.get('code')
        
        # Cari aset
        asset = None
        if asset_id and str(asset_id).isdigit():
            asset = Asset.objects.filter(id=int(asset_id)).first()
        if not asset and code:
            asset = Asset.objects.filter(code=code).first()
        if not asset and sn:
            asset = Asset.objects.filter(serial_number=sn).first()

        if not asset:
            return JsonResponse({'status': 'error', 'message': 'Aset terkait tidak ditemukan!'}, status=404)

        wo_no = data.get('wo_no') or f"CM-{asset.location[:3].upper()}-{timezone.now().strftime('%Y%m%d%H%M')}"
        tgl_lapor = data.get('tgl_lapor') or timezone.now().date().isoformat()
        pelapor = data.get('pelapor', '')
        urgency = data.get('urgency', 'medium').lower()
        if urgency not in ['low', 'medium', 'high']:
            urgency = 'medium'

        deskripsi = data.get('deskripsi', '')
        root_cause = data.get('root_cause', '')
        tindakan = data.get('tindakan', '')
        status_akhir = data.get('status_akhir', 'Layak Pakai')

        # Simpan Maintenance Record
        record = MaintenanceRecord.objects.create(
            work_order_no=wo_no,
            maintenance_type='corrective',
            asset=asset,
            date=tgl_lapor,
            reporter_name=pelapor,
            technician=request.user if request.user.is_authenticated else None,
            technician_name=request.user.get_full_name() or request.user.username,
            urgency=urgency,
            damage_description=deskripsi,
            root_cause=root_cause,
            action_taken=tindakan,
            result_status=status_akhir,
        )

        # Simpan Suku Cadang jika ada
        spareparts = data.get('spareparts', [])
        for sp in spareparts:
            part_name = sp.get('name', '').strip()
            if part_name:
                qty = int(sp.get('qty', 1))
                part_sn = sp.get('sn', '')
                SparePartReplacement.objects.create(
                    maintenance_record=record,
                    part_name=part_name,
                    quantity=qty,
                    serial_number=part_sn
                )

        # Update Status Aset sesuai status_akhir
        if status_akhir == 'Layak Pakai':
            asset.status = 'active'
        elif status_akhir == 'Pending Part':
            asset.status = 'maintenance'
        elif status_akhir == 'Afkir / Rusak Berat':
            asset.status = 'retired'
        else:
            asset.status = 'repair'
        asset.save()

        return JsonResponse({
            'status': 'success',
            'message': f"Laporan perbaikan {wo_no} berhasil disimpan dan status aset diperbarui!",
            'wo_no': wo_no
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def upload_calibration_certificate(request, asset_id):
    """Upload sertifikat kalibrasi PDF untuk suatu aset (multipart/form-data)."""
    try:
        asset = get_object_or_404(Asset, pk=asset_id)

        cert_file = request.FILES.get('certificate_file')
        if not cert_file:
            return JsonResponse({'status': 'error', 'message': 'File sertifikat wajib diunggah!'}, status=400)

        test_date_str = request.POST.get('test_date')
        valid_until_str = request.POST.get('valid_until')
        institution = request.POST.get('institution', '').strip()
        certificate_no = request.POST.get('certificate_no', '').strip()
        result = request.POST.get('result', 'Lolos Kalibrasi').strip()
        notes = request.POST.get('notes', '').strip()

        if not test_date_str or not valid_until_str or not institution or not certificate_no:
            return JsonResponse({'status': 'error', 'message': 'Tanggal kalibrasi, masa berlaku, lembaga penguji, dan no. sertifikat wajib diisi!'}, status=400)

        # Konversi string (YYYY-MM-DD) menjadi objek datetime.date
        test_date = parse_date(test_date_str)
        valid_until = parse_date(valid_until_str)

        if not test_date or not valid_until:
            return JsonResponse({'status': 'error', 'message': 'Format tanggal tidak valid! Gunakan format YYYY-MM-DD.'}, status=400)

        calib = CalibrationRecord.objects.create(
            asset=asset,
            test_date=test_date,
            valid_until=valid_until,
            testing_institution=institution,
            certificate_no=certificate_no,
            result=result,
            notes=notes,
            certificate_file=cert_file,
        )

        # Update status kalibrasi aset
        asset.calibration_status = 'active'
        asset.calibration_expiry = valid_until
        asset.save()

        return JsonResponse({
            'status': 'success',
            'message': f'Sertifikat kalibrasi No. {certificate_no} berhasil diunggah!',
            'record': {
                'id': calib.id,
                'test_date': calib.test_date.strftime('%d %b %Y'),
                'institution': calib.testing_institution,
                'certificate_no': calib.certificate_no,
                'result': calib.result,
                'valid_until': calib.valid_until.strftime('%d %b %Y'),
                'upload_date': calib.created_at.strftime('%d %b %Y') if calib.created_at else '-',
                'cert_url': calib.certificate_file.url if calib.certificate_file else None,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def upload_spo_document(request, asset_id):
    """Upload dokumen SPO PDF untuk suatu aset (multipart/form-data)."""
    try:
        asset = get_object_or_404(Asset, pk=asset_id)

        spo_file = request.FILES.get('spo_file')
        if not spo_file:
            return JsonResponse({'status': 'error', 'message': 'File PDF SPO wajib diunggah!'}, status=400)

        title = request.POST.get('title', 'SPO').strip()
        version = request.POST.get('version', '1.0').strip()
        notes = request.POST.get('notes', '').strip()

        spo = SPORecord.objects.create(
            asset=asset,
            title=title,
            version=version,
            notes=notes,
            file=spo_file,
            uploaded_by=request.user if request.user.is_authenticated else None,
        )

        return JsonResponse({
            'status': 'success',
            'message': f'Dokumen SPO "{title}" versi {version} berhasil diunggah!',
            'record': {
                'id': spo.id,
                'title': spo.title,
                'version': spo.version,
                'notes': spo.notes,
                'uploaded_at': spo.uploaded_at.strftime('%d %b %Y %H:%M'),
                'uploaded_by': spo.uploaded_by.get_full_name() if spo.uploaded_by else 'Admin',
                'file_url': spo.file.url if spo.file else None,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def public_asset_info(request, pk):
    """Halaman publik informasi aset medis, sertifikat kalibrasi, SPO, riwayat maintenance, dan riwayat perbaikan."""
    asset = get_object_or_404(
        Asset.objects.select_related('category').prefetch_related(
            'calibrations', 'spo_records', 'maintenance_records__spareparts'
        ),
        pk=pk
    )
    latest_calibration = asset.calibrations.first()
    latest_spo = asset.spo_records.first()

    all_maintenance = asset.maintenance_records.all()
    preventive_records = all_maintenance.filter(maintenance_type='preventive')
    corrective_records = all_maintenance.filter(maintenance_type='corrective')

    context = {
        'asset': asset,
        'latest_calibration': latest_calibration,
        'calibrations': asset.calibrations.all(),
        'latest_spo': latest_spo,
        'spo_records': asset.spo_records.all(),
        'preventive_records': preventive_records,
        'corrective_records': corrective_records,
        'total_preventive': preventive_records.count(),
        'total_corrective': corrective_records.count(),
    }
    return render(request, 'assets/public_asset_info.html', context)


@login_required
def print_qr_labels(request):
    """Mencetak label QR Code sekaligus (bisa banyak / semua / terpilih)."""
    selected_ids = request.GET.get('ids', '').strip()
    room_filter = request.GET.get('room', 'ALL')

    assets_qs = Asset.objects.select_related('category').all()

    if selected_ids:
        id_list = [int(i) for i in selected_ids.split(',') if i.strip().isdigit()]
        assets_qs = assets_qs.filter(id__in=id_list)
    elif room_filter != 'ALL':
        assets_qs = assets_qs.filter(location__icontains=room_filter)

    labels = []
    for asset in assets_qs:
        # Buat URL absolut untuk publik
        public_url = request.build_absolute_uri(reverse('assets:public_info', args=[asset.id]))

        # Generate QR Code ke base64
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=1,
        )
        qr.add_data(public_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        labels.append({
            'asset': asset,
            'qr_b64': qr_b64,
            'public_url': public_url,
        })

    context = {
        'labels': labels,
        'total_count': len(labels),
    }
    return render(request, 'assets/print_qr_labels.html', context)

