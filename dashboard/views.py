import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from assets.models import Asset
from maintenance.models import MaintenanceRecord

@login_required
def index(request):
    room_filter = request.GET.get('room', 'ALL')
    
    # Queryset dasar
    asset_qs = Asset.objects.all()
    if room_filter != 'ALL':
        asset_qs = asset_qs.filter(location__icontains=room_filter)

    total_assets = asset_qs.count()
    layak_count = asset_qs.filter(status='active').count()
    layak_pct = round((layak_count / total_assets * 100), 1) if total_assets > 0 else 0
    repair_count = asset_qs.filter(status__in=['repair', 'broken', 'maintenance']).count()
    expired_count = asset_qs.filter(calibration_status='expired').count()

    # Chart 1: Status Kinerja
    active_cnt = asset_qs.filter(status='active').count()
    maint_cnt = asset_qs.filter(status='maintenance').count()
    broken_cnt = asset_qs.filter(status__in=['repair', 'broken']).count()
    retired_cnt = asset_qs.filter(status='retired').count()
    chart_status_data = [active_cnt, maint_cnt, broken_cnt, retired_cnt]

    # Chart 2: Distribusi per Ruangan
    room_counts = Asset.objects.values('location').annotate(count=Count('id')).order_by('-count')
    chart_room_labels = [item['location'] for item in room_counts]
    chart_room_values = [item['count'] for item in room_counts]

    # Chart 3: Status Kalibrasi
    calib_active = asset_qs.filter(calibration_status='active').count()
    calib_process = asset_qs.filter(calibration_status='process').count()
    calib_expired = asset_qs.filter(calibration_status='expired').count()
    chart_calib_data = [calib_active, calib_process, calib_expired]

    # Chart 4: Tren Work Order Bulanan (Tahun berjalan)
    current_year = timezone.now().year
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
    wo_preventive = [0] * 12
    wo_corrective = [0] * 12

    wo_qs = MaintenanceRecord.objects.filter(date__year=current_year)
    for wo in wo_qs:
        m_idx = wo.date.month - 1
        if wo.maintenance_type == 'preventive':
            wo_preventive[m_idx] += 1
        else:
            wo_corrective[m_idx] += 1

    context = {
        'room_filter': room_filter,
        'kpi_total': total_assets,
        'kpi_layak': f"{layak_count} ({layak_pct}%)" if total_assets > 0 else "0 (0%)",
        'kpi_perbaikan': repair_count,
        'kpi_expired': expired_count,
        'chart_status_json': json.dumps(chart_status_data),
        'chart_room_labels_json': json.dumps(chart_room_labels),
        'chart_room_values_json': json.dumps(chart_room_values),
        'chart_calib_json': json.dumps(chart_calib_data),
        'chart_wo_months_json': json.dumps(months),
        'chart_wo_prev_json': json.dumps(wo_preventive),
        'chart_wo_corr_json': json.dumps(wo_corrective),
    }

    return render(request, 'dashboard/index.html', context)
