import os, json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.conf import settings
from django.utils import timezone
from assets.models import Asset, Category
from .models import MaintenanceRecord, SparePartReplacement

@login_required
def index(request):
    asset_id = request.GET.get('asset_id')
    code = request.GET.get('code')
    category_id = request.GET.get('category_id')
    
    selected_asset = None
    if asset_id:
        selected_asset = Asset.objects.select_related('category').filter(id=asset_id).first()
    elif code:
        selected_asset = Asset.objects.select_related('category').filter(code=code).first()

    all_assets = Asset.objects.select_related('category').all().order_by('name')
    categories = Category.objects.all().order_by('name')

    # Tentukan kategori aktif awal
    current_category = None
    if selected_asset and selected_asset.category:
        current_category = selected_asset.category
    elif category_id:
        current_category = Category.objects.filter(id=category_id).first()
    
    if not current_category and categories.exists():
        # Default ke kategori Ventilator jika ada, atau kategori pertama
        current_category = Category.objects.filter(name='Ventilator').first() or categories.first()

    # Siapkan kamus template kategori ke JSON untuk pergantian instan di browser
    templates_dict = {}
    for cat in categories:
        templates_dict[cat.id] = {
            'id': cat.id,
            'name': cat.name,
            'slug': cat.slug,
            'k3': cat.k3_notes or [
                "Jika terjadi kontaminasi cairan tubuh/kimia, bersihkan & sterilkan dahulu alat sebelum pemeriksaan.",
                "Kenakan perlengkapan proteksi APD selama pemeliharaan.",
                "Kenakan gelang antistatik saat menangani PCB/komponen elektronika.",
                "Mengacu pada buku pedoman pabrik pembuat alat.",
                "Pastikan alat ukur/uji yang digunakan telah terkalibrasi."
            ],
            'accessories': cat.accessories_template or [],
            'inspections': cat.inspection_template or []
        }

    now = timezone.now()
    loc_prefix = (selected_asset.location[:3].upper() if selected_asset and selected_asset.location else "IPS")
    default_wo = f"WO-{loc_prefix}-{now.strftime('%Y%m%d%H%M')}"

    context = {
        'selected_asset': selected_asset,
        'all_assets': all_assets,
        'categories': categories,
        'current_category': current_category,
        'category_templates_json': json.dumps(templates_dict),
        'default_wo': default_wo,
        'today': now.strftime('%Y-%m-%d'),
        'current_time': now.strftime('%H:%M'),
    }
    return render(request, 'maintenance/index.html', context)


@login_required
def category_template_api(request, category_id):
    """API untuk mengambil template checklist per kategori."""
    cat = get_object_or_404(Category, id=category_id)
    return JsonResponse({
        'id': cat.id,
        'name': cat.name,
        'slug': cat.slug,
        'k3': cat.k3_notes,
        'accessories': cat.accessories_template,
        'inspections': cat.inspection_template
    })


@login_required
def category_form_html_view(request, slug):
    """Menampilkan atau mengarahkan ke form HTML kategori spesifik."""
    category = get_object_or_404(Category, slug=slug)
    
    # Cari berkas HTML di medlog/form-maintenance-word/
    folder = settings.BASE_DIR / 'form-maintenance-word'
    possible_files = [
        folder / f"Form Maintenance {category.name}.html",
        folder / f"Form Maintenance {category.name} .html",
        folder / f"{category.name}.html",
    ]

    html_file = next((f for f in possible_files if f.exists()), None)
    if html_file:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html')
    else:
        # Fallback redirect ke form dinamis
        return redirect(f"/maintenance/?category_id={category.id}")


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def save_maintenance_preventive(request):
    """Menyimpan lembar kerja pemeliharaan preventif dari web app maupun file HTML standalone."""
    if request.method == "OPTIONS":
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
        return response

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        wo_no = data.get('wo_no')
        asset_id = data.get('asset_id')
        code = data.get('code') or data.get('no_aset')
        name = data.get('name') or data.get('nama_alat') or data.get('category_name') or 'Peralatan Alkes'
        
        asset = None
        if asset_id and str(asset_id).isdigit():
            asset = Asset.objects.filter(id=int(asset_id)).first()
        if not asset and code:
            asset = Asset.objects.filter(code=code).first()

        # Jika aset belum ada di DB tapi ada kode dan nama yang dikirim, otomatis daftarkan!
        if not asset:
            if not code:
                return JsonResponse({'status': 'error', 'message': 'Pilih alat atau isi No. Aset / Kode Inventaris!'}, status=400)
            
            cat_name = data.get('category_name') or name
            matched_cat = Category.objects.filter(name__icontains=cat_name).first()

            asset = Asset.objects.create(
                code=code,
                name=name,
                brand=data.get('brand', ''),
                model_type=data.get('model_type', ''),
                serial_number=data.get('sn') or data.get('no_seri', ''),
                location=data.get('location') or data.get('lokasi', 'Ruang ICU'),
                installation_year=int(data.get('installation_year')) if data.get('installation_year') and str(data.get('installation_year')).isdigit() else timezone.now().year,
                category=matched_cat,
                status='active'
            )

        date_val = data.get('date') or timezone.now().date().isoformat()
        start_time = data.get('start_time') or None
        end_time = data.get('end_time') or None

        result_status = data.get('result_status', 'Layak Pakai')
        notes = data.get('notes', '')

        # Checklist data
        accessories_check = data.get('accessories_check', {})
        physical_check = data.get('physical_check', {})

        # Tanda tangan
        sig_user = data.get('signature_user', '')
        sig_user_name = data.get('signature_user_name', '')
        sig_eng = data.get('signature_engineer', '')
        sig_eng_name = data.get('signature_engineer_name', '')
        if not sig_eng_name and request.user.is_authenticated:
            sig_eng_name = request.user.get_full_name() or request.user.username
        if not sig_eng_name:
            sig_eng_name = "Teknisi IPSRS"

        if not wo_no:
            wo_no = f"WO-{asset.location[:3].upper()}-{timezone.now().strftime('%Y%m%d%H%M')}"

        record = MaintenanceRecord.objects.create(
            work_order_no=wo_no,
            maintenance_type='preventive',
            asset=asset,
            date=date_val,
            start_time=start_time,
            end_time=end_time,
            technician=request.user if request.user.is_authenticated else None,
            technician_name=sig_eng_name,
            result_status=result_status,
            notes=notes,
            accessories_check=accessories_check,
            physical_functional_check=physical_check,
            signature_user=sig_user,
            signature_user_name=sig_user_name,
            signature_engineer=sig_eng,
            signature_engineer_name=sig_eng_name,
        )

        # Update status aset
        if result_status == 'Layak Pakai':
            asset.status = 'active'
        else:
            asset.status = 'repair'
        asset.save()

        response = JsonResponse({
            'status': 'success',
            'message': f"Form Pemeliharaan Preventif {wo_no} ({asset.name}) berhasil disimpan ke database!",
            'wo_no': wo_no,
            'record_id': record.id
        })
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
        return response

    except Exception as e:
        response = JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        response["Access-Control-Allow-Origin"] = "*"
        return response


@login_required
def maintenance_list(request):
    records = MaintenanceRecord.objects.select_related('asset', 'technician').all()
    m_type = request.GET.get('type')
    if m_type:
        records = records.filter(maintenance_type=m_type)
    
    return render(request, 'maintenance/list.html', {'records': records})


def work_order_detail(request, pk):
    record = get_object_or_404(MaintenanceRecord.objects.select_related('asset', 'technician'), pk=pk)
    return render(request, 'maintenance/detail.html', {'record': record})
