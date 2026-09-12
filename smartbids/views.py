import secrets
import json
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Sum
from django.utils import timezone
from .models import (
    Mensajeria,
    FactItemOrdenCompra,
    FactOrdenCompra,
    Suscriptor,
    Empresa,
    Preferencia,
    Licitacion,
    EstadoSuscriptor
)

logger = logging.getLogger(__name__)

# ==============================================================================
# VISTAS DE PÁGINAS Y NAVEGACIÓN
# ==============================================================================

def home(request):
    return render(request, 'smartbids/home.html')

def login_view(request):
    return render(request, 'registro/ingreso.html')

def register_view(request):
    return render(request, 'registro/registro.html')

def perfil_view(request):
    return render(request, 'smartbids/perfil.html')

def mensajeria_view(request):
    return render(request, 'smartbids/mensajeria.html')

def handler404_view(request, exception=None):
    return render(request, 'smartbids/404.html', status=404)

def informacion_view(request):
    return render(request, 'smartbids/informacion.html')





def mis_licitaciones_view(request):
    licitaciones_list = Licitacion.objects.select_related('lic_codigo_ucom').all().order_by('-lic_fecha_public')
    
    # 2. Total general para las métricas
    total_licitaciones = Licitacion.objects.count()
    
    paginator = Paginator(licitaciones_list, 20)
    page_number = request.GET.get('page')
    licitaciones = paginator.get_page(page_number)

    context = {
        'licitaciones': licitaciones,
        'total_licitaciones': total_licitaciones,
    }
    
    return render(request, 'smartbids/Mis_licitaciones.html', context)

def dashboard_view(request):
    return render(request, 'smartbids/dashboard.html')


# ==============================================================================
# REGISTRO Y AUTENTICACIÓN (POSTGRESQL)
# ==============================================================================

@csrf_exempt
def registrar_prospecto(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')

        if not uid:
            return JsonResponse({'status': 'error', 'mensaje': 'El UID es obligatorio.'}, status=400)

        # Evitar duplicados por UID de Firebase
        if Suscriptor.objects.filter(firebase_uid=uid).exists():
            return JsonResponse({'status': 'ok', 'mensaje': 'El suscriptor ya existe.'})

        ahora = timezone.now()

        # Obtener o asignar la instancia de EstadoSuscriptor (ejemplo: ID 2 = Habilitado)
        estado_instancia = EstadoSuscriptor.objects.filter(codigo_estado=2).first()

        Suscriptor.objects.create(
            firebase_uid=uid,
            fecha_registro=ahora,
            fecha_actualizacion=ahora,
            codigo_estado=estado_instancia, # <--- Usar la instancia asignada
            sus_nombre1='',
            sus_apellido1=''
        )

        return JsonResponse({'status': 'ok', 'mensaje': 'Suscriptor habilitado registrado con éxito.'}, status=201)

    except Exception as e:
        logger.error(f"[SmartBids] Error al registrar prospecto: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)
# ==============================================================================
# AUTENTICACIÓN 2FA Y TOKEN DE SESIÓN ÚNICA
# ==============================================================================

CODIGOS_OTP_TEMPORALES = {}

@csrf_exempt
def enviar_codigo_login(request):
    """Genera y envía el código OTP de 6 dígitos al correo vía SMTP."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        email_destinatario = data.get('email')

        if not email_destinatario:
            return JsonResponse({'status': 'error', 'mensaje': 'El correo electrónico es requerido.'}, status=400)

        # Generar código criptográfico de 6 dígitos
        codigo_seguridad = f"{secrets.randbelow(900000) + 100000}"
        CODIGOS_OTP_TEMPORALES[email_destinatario] = {
            'codigo': codigo_seguridad,
            'creado_el': timezone.now()
        }

        asunto = f'🔐 Tu código de acceso SmartBids: {codigo_seguridad}'
        mensaje_plano = f'Tu código de verificación para SmartBids es: {codigo_seguridad}\n\nExpira en 10 minutos.'

        html_mensaje = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f8f7; margin: 0; padding: 20px; color: #2d3748; }}
                .card {{ max-width: 560px; background: #ffffff; margin: 0 auto; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #e2ece9; }}
                .header {{ background: linear-gradient(135deg, #11634e 0%, #0b3831 100%); padding: 35px 30px; text-align: center; color: #ffffff; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; }}
                .header p {{ color: #b1d2ca; margin: 8px 0 0 0; font-size: 14px; }}
                .body {{ padding: 30px; text-align: center; }}
                .code-box {{ background: #eef7f4; border: 2px dashed #1ec498; border-radius: 12px; padding: 18px 10px; margin: 25px auto; max-width: 280px; }}
                .code {{ font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #11634e; font-family: 'Consolas', monospace; }}
                .alert-box {{ background: #fffaf0; border: 1px solid #feebc8; border-radius: 8px; padding: 12px 14px; margin: 20px 0; font-size: 13px; color: #c05621; text-align: left; }}
                .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #a0aec0; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <h1>Código de Autenticación 🔐</h1>
                    <p>Verificación de seguridad en dos pasos</p>
                </div>
                <div class="body">
                    <p style="font-size: 15px; color: #4a5568; line-height: 1.5; margin: 0;">
                        Has solicitado ingresar a tu cuenta de <strong>SmartBids</strong> ({email_destinatario}). Utiliza el siguiente código para completar tu acceso:
                    </p>
                    <div class="code-box">
                        <span class="code">{codigo_seguridad}</span>
                    </div>
                    <div class="alert-box">
                        ⚠️ <strong>Importante:</strong> Este código expira en 10 minutos y no debe compartirse con nadie.
                    </div>
                    <p style="font-size: 14px; color: #718096; margin-top: 25px; text-align: left;">
                        Saludos cordiales,<br>
                        <strong style="color: #11634e;">El equipo de Seguridad de SmartBids</strong>
                    </p>
                </div>
                <div class="footer">
                    © SmartBids — Transformando el acceso al mercado público
                </div>
            </div>
        </body>
        </html>
        """

        send_mail(
            subject=asunto,
            message=mensaje_plano,
            html_message=html_mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_destinatario],
            fail_silently=False,
        )

        return JsonResponse({'status': 'ok', 'mensaje': 'Código enviado exitosamente.'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido.'}, status=400)
    except Exception as e:
        logger.error(f"[SmartBids] Error al enviar código de login: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error en el servidor: {str(e)}'}, status=500)


@csrf_exempt
def validar_codigo_login(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        email = data.get('email')
        uid = data.get('uid')
        codigo = data.get('codigo')
        session_token = data.get('session_token')

        # 1. Validar OTP en memoria
        registro = CODIGOS_OTP_TEMPORALES.get(email)
        if not registro or registro['codigo'] != str(codigo):
            return JsonResponse({'status': 'error', 'mensaje': 'Código incorrecto o expirado.'}, status=400)

        CODIGOS_OTP_TEMPORALES.pop(email, None)

        # 2. Guardar token en PostgreSQL (crear si no existe por algún fallo previo)
        ahora = timezone.now()
        estado_instancia = EstadoSuscriptor.objects.filter(codigo_estado=2).first()

        suscriptor, created = Suscriptor.objects.get_or_create(
            firebase_uid=uid,
            defaults={
                'fecha_registro': ahora,
                'fecha_actualizacion': ahora,
                'codigo_estado': estado_instancia,
                'sus_nombre1': '',
                'sus_apellido1': ''
            }
        )
        
        suscriptor.token_sesion = session_token
        suscriptor.fecha_actualizacion = ahora
        suscriptor.save(update_fields=['token_sesion', 'fecha_actualizacion'])

        return JsonResponse({'status': 'ok', 'mensaje': 'Token y sesión guardados correctamente en PostgreSQL.'})

    except Exception as e:
        logger.error(f"[SmartBids] Error al validar código: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

@csrf_exempt
def verificar_sesion_activa(request):
    """Compara si el token del navegador coincide con el token_sesion activo en PostgreSQL."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')
        token_local = data.get('token')

        suscriptor = Suscriptor.objects.filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'ok', 'valido': False, 'motivo': 'Usuario no encontrado'})

        # Valida que el token remoto exista y sea idéntico al local
        token_remoto = getattr(suscriptor, 'token_sesion', None)
        es_valido = bool(token_remoto and token_remoto == token_local)

        return JsonResponse({'status': 'ok', 'valido': es_valido})

    except Exception as e:
        logger.error(f"[SmartBids] Error al verificar sesión: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)




# views.py

@csrf_exempt
def obtener_perfil_suscriptor(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')

        if not uid:
            return JsonResponse({'status': 'error', 'mensaje': 'El UID es requerido.'}, status=400)

        suscriptor = Suscriptor.objects.filter(firebase_uid=uid).first()

        # Si el suscriptor aún no existe en PostgreSQL, se responde de forma segura sin romper el frontend (evita 404/500)
        if not suscriptor:
            return JsonResponse({
                'status': 'ok',
                'datos': None,
                'mensaje': 'Suscriptor no encontrado en la base de datos local.'
            })

        # Datos de empresa si existe
        empresa_data = {}
        if getattr(suscriptor, 'sus_rut_empresa', None):
            emp = suscriptor.sus_rut_empresa
            empresa_data = {
                'emp_rut': emp.emp_rut,
                'emp_razon_social': emp.emp_razon_social,
                'emp_nombre_fantasia': emp.emp_nombre_fantasia,
                'emp_iniciales': emp.emp_iniciales,
                'emp_contacto_correo': emp.emp_contacto_correo,
                'emp_direccion': emp.emp_direccion or '',
                'emp_codigo_comuna': emp.emp_codigo_comuna or '',
                'emp_contacto_telefono': emp.emp_contacto_telefono or '',
            }

        # Datos de preferencias si existen
        pref = Preferencia.objects.filter(id_suscriptor=suscriptor).first()
        pref_data = {
            'pref_comunas': pref.pref_comunas or '' if pref else '',
            'pref_productos': pref.pref_productos or '' if pref else '',
            'pref_tipo_licitacion': pref.pref_tipo_licitacion or '' if pref else '',
            'pref_ucom': pref.pref_ucom or '' if pref else '',
            'pref_palabras_claves': pref.pref_palabras_claves or '' if pref else '',
        }

        # Extraer el valor primitive/ID de codigo_estado para no romper JsonResponse
        cod_estado_val = suscriptor.codigo_estado_id if suscriptor.codigo_estado_id else None

        return JsonResponse({
            'status': 'ok',
            'datos': {
                'id_suscriptor': suscriptor.id_suscriptor,
                'firebase_uid': suscriptor.firebase_uid,
                'sus_nombre1': suscriptor.sus_nombre1 or '',
                'sus_nombre2': suscriptor.sus_nombre2 or '',
                'sus_apellido1': suscriptor.sus_apellido1 or '',
                'sus_apellido2': suscriptor.sus_apellido2 or '',
                'sus_nombre_social': suscriptor.sus_nombre_social or '',
                'sus_iniciales': suscriptor.sus_iniciales or '',
                'codigo_estado': cod_estado_val,  # <--- CORREGIDO (envía el ID/valor primitivo)
                'token_sesion': getattr(suscriptor, 'token_sesion', '') or '',
                'fecha_registro': suscriptor.fecha_registro.isoformat() if suscriptor.fecha_registro else None,
                'fecha_actualizacion': suscriptor.fecha_actualizacion.isoformat() if suscriptor.fecha_actualizacion else None,
                'empresa': empresa_data,
                'preferencias': pref_data,
            }
        })
    except Exception as e:
        logger.error(f"[SmartBids] Error en obtener_perfil_suscriptor: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

@csrf_exempt
def actualizar_empresa_suscriptor(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')
        suscriptor = Suscriptor.objects.filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'error', 'mensaje': 'Suscriptor no encontrado.'}, status=404)

        rut = data.get('emp_rut', '').strip()
        empresa, _ = Empresa.objects.update_or_create(
            emp_rut=rut,
            defaults={
                'emp_razon_social': data.get('emp_razon_social', '').strip(),
                'emp_nombre_fantasia': data.get('emp_nombre_fantasia', '').strip(),
                'emp_iniciales': data.get('emp_iniciales', '').strip(),
                'emp_contacto_correo': data.get('emp_contacto_correo', '').strip(),
                'emp_direccion': data.get('emp_direccion', '').strip(),
                'emp_codigo_comuna': data.get('emp_codigo_comuna', '').strip(),
                'emp_contacto_telefono': data.get('emp_contacto_telefono', '').strip(),
            }
        )

        suscriptor.sus_rut_empresa = empresa
        suscriptor.save(update_fields=['sus_rut_empresa'])
        return JsonResponse({'status': 'ok', 'mensaje': 'Empresa guardada y vinculada.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@csrf_exempt
def actualizar_preferencias_suscriptor(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')
        suscriptor = Suscriptor.objects.filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'error', 'mensaje': 'Suscriptor no encontrado.'}, status=404)

        Preferencia.objects.update_or_create(
            id_suscriptor=suscriptor,
            defaults={
                'pref_comunas': data.get('pref_comunas', ''),
                'pref_productos': data.get('pref_productos', ''),
                'pref_tipo_licitacion': data.get('pref_tipo_licitacion', ''),
                'pref_ucom': data.get('pref_ucom', ''),
                'pref_palabras_claves': data.get('pref_palabras_claves', ''),
            }
        )
        return JsonResponse({'status': 'ok', 'mensaje': 'Preferencias de licitación actualizadas.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')

        suscriptor = Suscriptor.objects.filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'error', 'mensaje': 'Suscriptor no encontrado.'}, status=404)

        suscriptor.sus_nombre1 = data.get('pnombre', suscriptor.sus_nombre1)
        suscriptor.sus_nombre2 = data.get('snombre', suscriptor.sus_nombre2)
        suscriptor.sus_apellido1 = data.get('appaterno', suscriptor.sus_apellido1)
        suscriptor.sus_apellido2 = data.get('apmaterno', suscriptor.sus_apellido2)
        suscriptor.fecha_actualizacion = timezone.now()
        suscriptor.save(update_fields=['sus_nombre1', 'sus_nombre2', 'sus_apellido1', 'sus_apellido2', 'fecha_actualizacion'])

        return JsonResponse({'status': 'ok', 'mensaje': 'Datos actualizados con éxito en PostgreSQL.'})
    except Exception as e:
        logger.error(f"[SmartBids] Error al actualizar perfil: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@csrf_exempt
def actualizar_perfil_suscriptor(request):
    """Actualiza los datos personales del suscriptor en la tabla core.suscriptor."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')

        suscriptor = Suscriptor.objects.filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'error', 'mensaje': 'Suscriptor no encontrado.'}, status=404)

        # Asignar los campos correspondientes a core.suscriptor
        suscriptor.sus_nombre1 = data.get('sus_nombre1', suscriptor.sus_nombre1).strip()
        suscriptor.sus_nombre2 = data.get('sus_nombre2', suscriptor.sus_nombre2).strip()
        suscriptor.sus_apellido1 = data.get('sus_apellido1', suscriptor.sus_apellido1).strip()
        suscriptor.sus_apellido2 = data.get('sus_apellido2', suscriptor.sus_apellido2).strip()
        suscriptor.sus_nombre_social = data.get('sus_nombre_social', suscriptor.sus_nombre_social).strip()

        # Calcular o actualizar iniciales si vienen vacías
        iniciales = data.get('sus_iniciales', '').strip()
        if not iniciales and suscriptor.sus_nombre1 and suscriptor.sus_apellido1:
            iniciales = (suscriptor.sus_nombre1[0] + suscriptor.sus_apellido1[0]).upper()
        suscriptor.sus_iniciales = iniciales[:5]

        suscriptor.fecha_actualizacion = timezone.now()
        suscriptor.save(update_fields=[
            'sus_nombre1', 'sus_nombre2', 'sus_apellido1', 'sus_apellido2',
            'sus_nombre_social', 'sus_iniciales', 'fecha_actualizacion'
        ])

        return JsonResponse({'status': 'ok', 'mensaje': 'Datos del suscriptor actualizados con éxito en PostgreSQL.'})
    except Exception as e:
        logger.error(f"[SmartBids] Error al actualizar perfil: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

# ==============================================================================
# CORREOS INFORMATIVOS (BIENVENIDA Y CAMBIO DE CONTRASEÑA)
# ==============================================================================

@csrf_exempt
def enviar_correo_bienvenida(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        email_destinatario = data.get('email')

        if not email_destinatario:
            return JsonResponse({'status': 'error', 'mensaje': 'El correo electrónico es requerido.'}, status=400)

        asunto = '🚀 ¡Bienvenido a SmartBids! Comienza a ganar licitaciones'
        mensaje_plano = (
            f'¡Hola!\n\n'
            f'Te damos la bienvenida a SmartBids. Tu cuenta ({email_destinatario}) '
            f'ha sido registrada exitosamente. Por favor verifica tu correo para comenzar.'
        )

        html_mensaje = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f8f7; margin: 0; padding: 20px; color: #2d3748; }}
                .card {{ max-width: 560px; background: #ffffff; margin: 0 auto; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #e2ece9; }}
                .header {{ background: linear-gradient(135deg, #11634e 0%, #0b3831 100%); padding: 35px 30px; text-align: center; color: #ffffff; }}
                .header h1 {{ margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }}
                .header p {{ color: #b1d2ca; margin: 8px 0 0 0; font-size: 15px; }}
                .body {{ padding: 30px; }}
                .user-badge {{ background: #eef7f4; border-left: 4px solid #1ec498; padding: 12px 16px; border-radius: 4px; margin: 20px 0; font-size: 14px; color: #11634e; font-weight: 600; }}
                .features {{ background: #fdfefe; border: 1px dashed #b1d2ca; border-radius: 10px; padding: 18px 20px; margin: 25px 0; }}
                .features ul {{ margin: 0; padding-left: 18px; }}
                .features li {{ margin-bottom: 8px; font-size: 14px; color: #4a5568; }}
                .alert-box {{ background: #fffaf0; border: 1px solid #feebc8; border-radius: 8px; padding: 14px; margin: 20px 0; font-size: 13px; color: #c05621; }}
                .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #a0aec0; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <h1>¡Bienvenido a SmartBids! 🚀</h1>
                    <p>Inteligencia y datos para tus licitaciones</p>
                </div>
                <div class="body">
                    <p style="font-size: 16px; line-height: 1.6;">
                        ¡Hola! Estamos felices de darte la bienvenida a nuestra plataforma de analítica y monitoreo de compras públicas.
                    </p>
                    <div class="user-badge">
                        👤 Cuenta registrada: <span>{email_destinatario}</span>
                    </div>
                    <div class="features">
                        <strong style="color: #11634e; display: block; margin-bottom: 8px;">¿Qué puedes hacer en SmartBids?</strong>
                        <ul>
                            <li>🎯 <strong>Monitorear</strong> oportunidades de negocio en Mercado Público en tiempo real.</li>
                            <li>🤖 <strong>Predecir</strong> probabilidades de adjudicación mediante Machine Learning.</li>
                            <li>⚡ <strong>Optimizar</strong> tus ofertas y tomar decisiones basadas en datos.</li>
                        </ul>
                    </div>
                    <div class="alert-box">
                        🔔 <strong>Paso indispensable:</strong> Recuerda hacer clic en el enlace de activación que enviamos a tu correo para habilitar tu acceso completo.
                    </div>
                    <p style="font-size: 14px; color: #718096; margin-top: 25px;">
                        Saludos cordiales,<br>
                        <strong style="color: #11634e;">El equipo de SmartBids</strong>
                    </p>
                </div>
                <div class="footer">
                    © SmartBids — Transformando el acceso al mercado público
                </div>
            </div>
        </body>
        </html>
        """

        send_mail(
            subject=asunto,
            message=mensaje_plano,
            html_message=html_mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_destinatario],
            fail_silently=False,
        )

        return JsonResponse({'status': 'ok', 'mensaje': 'Correo de bienvenida enviado exitosamente.'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'Cuerpo de la petición JSON inválido.'}, status=400)
    except Exception as e:
        logger.error(f"[SmartBids] Error al enviar correo de bienvenida: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error en el servidor: {str(e)}'}, status=500)


@csrf_exempt
def enviar_correo_cambio_password(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        email_destinatario = data.get('email')

        if not email_destinatario:
            return JsonResponse({'status': 'error', 'mensaje': 'El correo es requerido.'}, status=400)

        asunto = '🔒 Tu contraseña en SmartBids ha sido modificada'
        mensaje_plano = (
            f"Hola,\n\n"
            f"Te informamos que la contraseña de tu cuenta ({email_destinatario}) ha sido actualizada exitosamente.\n\n"
            f"Por razones de seguridad, tu sesión ha sido cerrada en todos los dispositivos.\n\n"
            f"Saludos cordiales,\n"
            f"El equipo de Seguridad de SmartBids"
        )

        send_mail(
            subject=asunto,
            message=mensaje_plano,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_destinatario],
            fail_silently=False,
        )

        return JsonResponse({'status': 'ok', 'mensaje': 'Correo de notificación enviado.'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido.'}, status=400)
    except Exception as e:
        logger.error(f"[SmartBids] Error al enviar notificación de cambio de contraseña: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error en el servidor: {str(e)}'}, status=500)
    
    
    
    #=================================
    ## VISTAS DE DASHBOARD
    #=================================
    
    


def dashboard_view(request):
    
    # KPIs principales del dashboard

    monto_total_ordenes = (
        FactOrdenCompra.objects
        .using('dw')
        .aggregate(
            total=Sum('orden_monto_total_clp')
        )['total']
    )
    monto_total_ordenes = formatear_monto(monto_total_ordenes)

    total_ordenes = (
        FactOrdenCompra.objects
        .using('dw')
        .values('orden_codigo')
        .distinct()
        .count()
    )

    proveedores_activos = (
        FactOrdenCompra.objects
        .using('dw')
        .values('proveedor_key')
        .distinct()
        .count()
    )

    compradores_activos = (
        FactOrdenCompra.objects
        .using('dw')
        .values('comprador_key')
        .distinct()
        .count()
    )
    
    # 1. Productos más comprados
    productos_mas_comprados = (
        FactItemOrdenCompra.objects
        .using('dw')
        .values('producto_key__producto_nombre')
        .annotate(
            cantidad_ordenes=Count(
                'orden_codigo',
                distinct=True
            )
        )
        .order_by('-cantidad_ordenes')[:10]
    )

    # 2. Competencia (proveedores)
    proveedores_competencia = (
        FactOrdenCompra.objects
        .using('dw')
        .values(
            'proveedor_key__proveedor_nombre'
        )
        .annotate(
            cantidad_ordenes=Count(
                'orden_codigo',
                distinct=True
            )
        )
        .order_by('-cantidad_ordenes')[:5]
    )
    
    # Ranking de principales competidores
    competidores_qs = (
        FactOrdenCompra.objects
        .using('dw')
        .values(
            'proveedor_key__proveedor_nombre'
        )
        .annotate(
            adjudicaciones=Count(
                'orden_codigo',
                distinct=True
            ),
            monto_adjudicado=Sum(
                'orden_monto_total_clp'
            )
        )
        .order_by('-adjudicaciones')[:5]
    )
    
    total_adjudicaciones = (
        FactOrdenCompra.objects
        .using('dw')
        .values('orden_codigo')
        .distinct()
        .count()
    )
    
    competidores = []

    for competidor in competidores_qs:
        adjudicaciones = competidor['adjudicaciones']

        participacion = (
            (adjudicaciones / total_adjudicaciones) * 100
            if total_adjudicaciones > 0
            else 0
        )

        competidores.append({
            'nombre': competidor['proveedor_key__proveedor_nombre'],
            'adjudicaciones': adjudicaciones,
            'participacion': round(participacion, 2),
            'monto_adjudicado': formatear_monto(competidor['monto_adjudicado'] or 0),
        })
        
    top_competidores = [
        proveedor['proveedor_key__proveedor_nombre']
        for proveedor in proveedores_competencia
    ]
    
    evolucion_competidores_qs = (
        FactOrdenCompra.objects
        .using('dw')
        .filter(
            proveedor_key__proveedor_nombre__in=top_competidores
        )
        .values(
            'fecha_creacion_key__anio',
            'fecha_creacion_key__mes',
            'fecha_creacion_key__nombre_mes_corto',
            'proveedor_key__proveedor_nombre'
        )
        .annotate(
            cantidad_ordenes=Count(
                'orden_codigo',
                distinct=True
            )
        )
        .order_by(
            'fecha_creacion_key__anio',
            'fecha_creacion_key__mes'
        )
    )
        
    evolucion_competidores_data = {}

    for fila in evolucion_competidores_qs:

        anio = fila['fecha_creacion_key__anio']
        mes = fila['fecha_creacion_key__mes']
        nombre_mes = fila['fecha_creacion_key__nombre_mes_corto']
        proveedor = fila['proveedor_key__proveedor_nombre']
        cantidad = fila['cantidad_ordenes']

        periodo = f"{anio}-{mes:02d}"

        if periodo not in evolucion_competidores_data:
            evolucion_competidores_data[periodo] = {
                'periodo': f"{nombre_mes} {anio}",
            }

        evolucion_competidores_data[periodo][proveedor] = cantidad
        
        evolucion_competidores = list(
            evolucion_competidores_data.values()
        )
        
    # 3. Organismos Compradores
    organismos_compradores = (
        FactOrdenCompra.objects
        .using('dw')
        .values(
            'comprador_key__comprador_organismo_nombre'
        )
        .annotate(
            cantidad_ordenes=Count(
                'orden_codigo',
                distinct=True
            )
        )
        .order_by('-cantidad_ordenes')[:5]  
    )

    context = {
        'monto_total_ordenes': monto_total_ordenes,
        'total_ordenes': total_ordenes,
        'proveedores_activos': proveedores_activos,
        'compradores_activos': compradores_activos,
        'productos_mas_comprados': productos_mas_comprados,
        'proveedores_competencia': proveedores_competencia,
        'competidores': competidores,
        'evolucion_competidores': evolucion_competidores,
        'organismos_compradores': organismos_compradores,
    }

    return render(
        request,
        'smartbids/dashboard.html',
        context
    )

# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def formatear_monto(monto):
    if monto is None:
        return '$0'

    monto = float(monto)

    if monto >= 1_000_000_000:
        valor = monto / 1_000_000
        return f"${valor:,.0f} MM".replace(",", ".")

    if monto >= 1_000_000:
        valor = monto / 1_000_000
        return f"${valor:,.0f} M".replace(",", ".")

    if monto >= 1_000:
        valor = monto / 1_000
        return f"${valor:,.0f} mil".replace(",", ".")

    return f"${monto:,.0f}".replace(",", ".")

# ==============================================================================
# MENSAJERÍA Y ALERTAS ADMIN (POSTGRESQL)
# ==============================================================================

@csrf_exempt
def listar_crear_mensajes(request):
    if request.method == 'GET':
        mensajes = Mensajeria.objects.all().order_by('-creado_el')
        data = [
            {
                'id': m.id,
                'asunto': m.asunto,
                'cuerpo': m.cuerpo,
                'estado': m.estado,
                'tipoAlerta': m.tipo_alerta,
            }
            for m in mensajes
        ]
        return JsonResponse(data, safe=False)

    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
            nuevo = Mensajeria.objects.create(
                asunto=body.get('asunto', '').strip(),
                cuerpo=body.get('cuerpo', '').strip(),
                estado=body.get('estado', 'activo'),
                tipo_alerta=body.get('tipoAlerta', 'alerta')
            )
            return JsonResponse({'status': 'ok', 'id': nuevo.id}, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)


@csrf_exempt
def detalle_mensaje(request, id):
    mensaje_obj = get_object_or_404(Mensajeria, id=id)

    if request.method in ['PUT', 'POST']:
        try:
            body = json.loads(request.body.decode('utf-8'))
            mensaje_obj.asunto = body.get('asunto', mensaje_obj.asunto).strip()
            mensaje_obj.cuerpo = body.get('cuerpo', mensaje_obj.cuerpo).strip()
            mensaje_obj.estado = body.get('estado', mensaje_obj.estado)
            mensaje_obj.tipo_alerta = body.get('tipoAlerta', mensaje_obj.tipo_alerta)
            mensaje_obj.save()
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)

    if request.method == 'DELETE':
        mensaje_obj.delete()
        return JsonResponse({'status': 'ok'})

    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)


def obtener_alertas_activas(request):
    alertas = Mensajeria.objects.filter(estado='activo').order_by('-creado_el')
    data = [
        {
            'id': alerta.id,
            'asunto': alerta.asunto,
            'cuerpo': alerta.cuerpo,
            'tipoAlerta': alerta.tipo_alerta,
            'estado': alerta.estado,
        }
        for alerta in alertas
    ]
    return JsonResponse(data, safe=False)
