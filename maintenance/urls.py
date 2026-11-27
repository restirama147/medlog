from django.urls import path
from . import views

app_name = 'maintenance'

urlpatterns = [
    path('', views.index, name='view'),
    path('save-preventive/', views.save_maintenance_preventive, name='save_preventive'),
    path('list/', views.maintenance_list, name='list'),
    path('<int:pk>/', views.work_order_detail, name='detail'),
    path('category-template/<int:category_id>/', views.category_template_api, name='category_template'),
    path('form/<slug:slug>/', views.category_form_html_view, name='category_form_html'),
]
