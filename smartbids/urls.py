from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home', views.home, name='home'),
    path('ingreso/', views.login_view, name='ingreso'),
    path('registro/', views.register_view, name='registro'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('mensajeria/', views.mensajeria_view, name='mensajeria'),
    path('404/', views.handler404_view, name='handler404'),
    path('api/enviar-correo-bienvenida/', views.enviar_correo_bienvenida, name='enviar_correo_bienvenida'),
    path('api/enviar-codigo-login/', views.enviar_codigo_login, name='enviar_codigo_login'),
    path('api/enviar-correo-cambio-password/', views.enviar_correo_cambio_password, name='enviar_correo_cambio_password'),
]
