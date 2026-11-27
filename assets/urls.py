from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    path('', views.index, name='view'),
    path('create/', views.create_asset_ajax, name='create'),
    path('<int:pk>/api/', views.api_asset_detail, name='api_detail'),
    path('corrective/save/', views.save_corrective_action, name='save_corrective'),
    path('<int:asset_id>/calibration/upload/', views.upload_calibration_certificate, name='upload_calibration'),
    path('<int:asset_id>/spo/upload/', views.upload_spo_document, name='upload_spo'),
    path('labels/print/', views.print_qr_labels, name='print_labels'),
    path('p/<int:pk>/', views.public_asset_info, name='public_info'),
]
