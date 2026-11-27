from django.contrib import admin
from .models import MaintenanceRecord, SparePartReplacement, CalibrationRecord

class SparePartInline(admin.TabularInline):
    model = SparePartReplacement
    extra = 1

@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ('work_order_no', 'asset', 'maintenance_type', 'date', 'technician_name', 'result_status')
    list_filter = ('maintenance_type', 'result_status', 'urgency', 'date')
    search_fields = ('work_order_no', 'asset__name', 'asset__code', 'technician_name', 'reporter_name')
    inlines = [SparePartInline]

@admin.register(SparePartReplacement)
class SparePartReplacementAdmin(admin.ModelAdmin):
    list_display = ('part_name', 'quantity', 'serial_number', 'maintenance_record')
    search_fields = ('part_name', 'serial_number')

@admin.register(CalibrationRecord)
class CalibrationRecordAdmin(admin.ModelAdmin):
    list_display = ('certificate_no', 'asset', 'testing_institution', 'test_date', 'valid_until', 'result')
    list_filter = ('testing_institution', 'test_date')
    search_fields = ('certificate_no', 'asset__name', 'asset__code', 'testing_institution')
