from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('ingreso/', views.login_view, name='ingreso'),
    path('registro/', views.register_view, name='registro'),
    path('perfil/', views.perfil_view, name='perfil'),
]
