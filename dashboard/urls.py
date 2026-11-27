from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='view'),
    path('index/', views.index, name='index'),
    path('admin/', views.index, name='admin_index'),
    path('engineer/', views.index, name='engineer_index'),
    path('unit/', views.index, name='unit_index'),
]
