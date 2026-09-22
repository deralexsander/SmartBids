import secrets
import json
import logging
import hashlib
from datetime import timedelta
from django.http import JsonResponse
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone


from .models import Suscriptor, Mensajeria, Empresa, Preferencia, EstadoSuscriptor


logger = logging.getLogger(__name__)

CODIGOS_OTP_TEMPORALES = {}
OTP_EXPIRACION_SEGUNDOS = 600
OTP_REENVIO_SEGUNDOS = 60
OTP_MAXIMOS_POR_HORA = 5


def _identificador_cliente(request, email):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
    ip = ip or request.META.get('REMOTE_ADDR', 'unknown')
    identificador = f'{email.strip().lower()}:{ip}'
    return hashlib.sha256(identificador.encode('utf-8')).hexdigest()


def _limite_envio_otp(request, email):
    identificador = _identificador_cliente(request, email)
    clave_ultimo_envio = f'smartbids:otp:last:{identificador}'
    clave_intentos = f'smartbids:otp:hour:{identificador}'

    ultimo_envio = cache.get(clave_ultimo_envio)
    if ultimo_envio:
        segundos = int(timezone.now().timestamp() - ultimo_envio)
        if segundos < OTP_REENVIO_SEGUNDOS:
            return OTP_REENVIO_SEGUNDOS - segundos

    intentos = cache.get(clave_intentos, 0)
    if intentos >= OTP_MAXIMOS_POR_HORA:
        return OTP_REENVIO_SEGUNDOS

    cache.set(clave_ultimo_envio, timezone.now().timestamp(), OTP_REENVIO_SEGUNDOS)
    cache.set(clave_intentos, intentos + 1, 3600)
    return 0


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

        segundos_espera = _limite_envio_otp(request, email_destinatario)
        if segundos_espera:
            return JsonResponse({
                'status': 'error',
                'mensaje': f'Espera {segundos_espera} segundos antes de solicitar otro código.'
            }, status=429, headers={'Retry-After': str(segundos_espera)})

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

        if timezone.now() - registro['creado_el'] > timedelta(seconds=OTP_EXPIRACION_SEGUNDOS):
            CODIGOS_OTP_TEMPORALES.pop(email, None)
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
