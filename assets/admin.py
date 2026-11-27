from django.contrib import admin
from .models import Category, Asset

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'brand', 'serial_number', 'location', 'status', 'calibration_status')
    list_filter = ('status', 'calibration_status', 'location', 'category')
    search_fields = ('code', 'name', 'brand', 'serial_number', 'location')
    ordering = ('code',)
