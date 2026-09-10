from django.urls import path
from . import views
from .views import obtener_alertas_activas

urlpatterns = [
    path('', views.home, name='home'),
    path('home', views.home, name='home'),
    path('ingreso/', views.login_view, name='ingreso'),
    path('registro/', views.register_view, name='registro'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('mensajeria/', views.mensajeria_view, name='mensajeria'),
    path('404/', views.handler404_view, name='handler404'),
    path('informacion/', views.informacion_view, name='informacion'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('mis-licitaciones/', views.mis_licitaciones_view, name='mis_licitaciones'),

    path('api/alertas-activas/', obtener_alertas_activas, name='alertas_activas'),
    path('api/mensajeria/', views.listar_crear_mensajes, name='api_mensajeria'),
    path('api/mensajeria/<int:id>/', views.detalle_mensaje, name='api_detalle_mensaje'),
    path('api/alertas-activas/', views.obtener_alertas_activas, name='api_alertas_activas'),
    path('api/enviar-correo-bienvenida/', views.enviar_correo_bienvenida, name='enviar_correo_bienvenida'),
    path('api/enviar-codigo-login/', views.enviar_codigo_login, name='enviar_codigo_login'),
    path('api/enviar-correo-cambio-password/', views.enviar_correo_cambio_password, name='enviar_correo_cambio_password'),
    path('api/validar-codigo-login/', views.validar_codigo_login, name='validar_codigo_login'),
    path('api/registrar-prospecto/', views.registrar_prospecto, name='registrar_prospecto'),
    path('api/verificar-sesion/', views.verificar_sesion_activa, name='verificar_sesion'),
    path('api/obtener-perfil/', views.obtener_perfil_suscriptor, name='obtener_perfil'),
    path('api/actualizar-perfil/', views.actualizar_perfil_suscriptor, name='actualizar_perfil'),
    path('api/actualizar-empresa/', views.actualizar_empresa_suscriptor, name='actualizar_empresa'),
    path('api/actualizar-preferencias/', views.actualizar_preferencias_suscriptor, name='actualizar_preferencias'),

]
