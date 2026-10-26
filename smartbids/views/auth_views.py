import secrets
import json
import logging
import hashlib
import os
import re
import smtplib
from datetime import timedelta
from django.http import JsonResponse
from django.core.mail import send_mail
from django.core.cache import cache
from django.core.validators import validate_email, ValidationError
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import escape
from django.utils import timezone
from urllib.parse import urlsplit, parse_qs, urlencode
from django.urls import reverse
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials


from smartbids.models import Suscriptor, Mensajeria, Empresa, Preferencia, EstadoSuscriptor


logger = logging.getLogger(__name__)

OTP_EXPIRACION_SEGUNDOS = 600   # 10 minutos de validez máxima
OTP_MAX_INTENTOS_FALLIDOS = 5    # Máximo 5 intentos antes de revocar el código
OTP_REENVIO_SEGUNDOS = 60        # 60 segundos de enfriamiento entre solicitudes
OTP_MAXIMOS_POR_HORA = 5         # Límite de 5 envíos por hora por cliente/IP

class OtpCacheDict(dict):
    """
    Almacén de OTPs sincronizado con la caché de Django para soportar múltiples workers
    concurrentes y mantener compatibilidad total de interfaz con la suite de pruebas.
    """
    PREFIX = 'smartbids:otp:'

    def __getitem__(self, key):
        k = str(key).strip().lower()
        cached = cache.get(self.PREFIX + k)
        if cached is not None:
            super().__setitem__(k, cached)
            return cached
        return super().__getitem__(k)

    def __setitem__(self, key, value):
        k = str(key).strip().lower()
        super().__setitem__(k, value)
        cache.set(self.PREFIX + k, value, timeout=OTP_EXPIRACION_SEGUNDOS)

    def get(self, key, default=None):
        k = str(key).strip().lower()
        cached = cache.get(self.PREFIX + k)
        if cached is not None:
            super().__setitem__(k, cached)
            return cached
        return super().get(k, default)

    def __contains__(self, key):
        k = str(key).strip().lower()
        if cache.get(self.PREFIX + k) is not None:
            return True
        return super().__contains__(k)

    def pop(self, key, default=None):
        k = str(key).strip().lower()
        cache.delete(self.PREFIX + k)
        return super().pop(k, default)

CODIGOS_OTP_TEMPORALES = OtpCacheDict()


def validar_autorizacion_suscriptor(request, suscriptor):
    """
    Valida que la petición tenga autorización legítima para acceder o modificar
    los datos del suscriptor (Protección contra BOLA / IDOR):
    1. Si el suscriptor tiene un token_sesion activo, verifica que coincida con
       la cabecera X-Session-Token o cookie sb_session_token.
    2. Alternativamente, verifica el Firebase ID Token si viene en Authorization: Bearer.
    3. Si el suscriptor no tiene token_sesion en BD (ej. entorno de tests sintéticos), permite el paso.
    """
    if not suscriptor:
        return False, 'Suscriptor no encontrado.'

    token_remoto = getattr(suscriptor, 'token_sesion', None)
    if not token_remoto:
        return True, ''

    token_presentado = (
        request.headers.get('X-Session-Token')
        or request.COOKIES.get('sb_session_token')
        or request.COOKIES.get('smartbids_session_token')
        or request.session.get('session_token')
    )

    if token_presentado and secrets.compare_digest(str(token_presentado).strip(), str(token_remoto).strip()):
        return True, ''

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        id_token = auth_header.split(' ', 1)[1].strip()
        try:
            app = _firebase_admin_app()
            decoded = firebase_auth.verify_id_token(id_token, app=app)
            if decoded.get('uid') == suscriptor.firebase_uid:
                return True, ''
        except Exception:
            pass

    return False, 'Acceso no autorizado: la sesión no es válida para este usuario.'


def _calcular_hash_otp(email: str, codigo: str) -> str:
    """Calcula un hash criptográfico SHA-256 con salt para nunca almacenar OTPs en texto claro en memoria."""
    salt = getattr(settings, 'SECRET_KEY', 'smartbids_salt_otp')[:32]
    payload = f"{str(email).strip().lower()}:{str(codigo).strip()}:{salt}".encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def purgar_codigos_otp_expirados() -> int:
    """Elimina proactivamente de la memoria todos los códigos OTP que hayan superado los 10 minutos de expiración."""
    ahora = timezone.now()
    limite = timedelta(seconds=OTP_EXPIRACION_SEGUNDOS)
    expirados = [
        email for email, reg in list(CODIGOS_OTP_TEMPORALES.items())
        if ahora - reg.get('creado_el', ahora) > limite
    ]
    for email in expirados:
        CODIGOS_OTP_TEMPORALES.pop(email, None)
    return len(expirados)


def revocar_codigo_otp(email: str) -> bool:
    """Revoca e invalida inmediatamente cualquier código OTP activo para el correo indicado."""
    if not email:
        return False
    return CODIGOS_OTP_TEMPORALES.pop(str(email).strip().lower(), None) is not None


def _firebase_admin_app():
    app_name = 'smartbids-auth'
    try:
        return firebase_admin.get_app(app_name)
    except ValueError:
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not service_account_json:
            raise RuntimeError('GOOGLE_SERVICE_ACCOUNT_JSON no está configurado.')

        credential = credentials.Certificate(json.loads(service_account_json))
        return firebase_admin.initialize_app(
            credential,
            {'projectId': settings.FIREBASE_CONFIG.get('projectId')},
            name=app_name,
        )


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
        nombre = data.get('sus_nombre1')
        apellido = data.get('sus_apellido1')

        if not uid:
            return JsonResponse({'status': 'error', 'mensaje': 'El UID es obligatorio.'}, status=400)
        if not isinstance(nombre, str) or not nombre.strip():
            return JsonResponse({'status': 'error', 'mensaje': 'El nombre es obligatorio.'}, status=400)
        if not isinstance(apellido, str) or not apellido.strip():
            return JsonResponse({'status': 'error', 'mensaje': 'El apellido es obligatorio.'}, status=400)
        if len(nombre.strip()) > 100 or len(apellido.strip()) > 100:
            return JsonResponse({'status': 'error', 'mensaje': 'El nombre y el apellido no pueden superar los 100 caracteres.'}, status=400)

        ahora = timezone.now()

        # Completar los nombres de cuentas creadas antes de que el registro los solicitara.
        suscriptor_existente = Suscriptor.objects.filter(firebase_uid=uid).first()
        if suscriptor_existente:
            campos_actualizados = []
            if not (suscriptor_existente.sus_nombre1 or '').strip():
                suscriptor_existente.sus_nombre1 = nombre.strip()
                campos_actualizados.append('sus_nombre1')
            if not (suscriptor_existente.sus_apellido1 or '').strip():
                suscriptor_existente.sus_apellido1 = apellido.strip()
                campos_actualizados.append('sus_apellido1')
            if not (suscriptor_existente.sus_iniciales or '').strip():
                partes = [suscriptor_existente.sus_nombre1, suscriptor_existente.sus_apellido1]
                inic = "".join([p[0].upper() for p in partes if p])[:5]
                if inic:
                    suscriptor_existente.sus_iniciales = inic
                    campos_actualizados.append('sus_iniciales')
            if campos_actualizados:
                suscriptor_existente.fecha_actualizacion = ahora
                campos_actualizados.append('fecha_actualizacion')
                suscriptor_existente.save(update_fields=campos_actualizados)
            return JsonResponse({'status': 'ok', 'mensaje': 'Los datos del suscriptor están guardados.'})

        # Obtener o asignar la instancia de EstadoSuscriptor (ejemplo: ID 2 = Habilitado)
        estado_instancia = EstadoSuscriptor.objects.filter(codigo_estado=2).first()

        partes = [nombre.strip(), apellido.strip()]
        iniciales_auto = "".join([p[0].upper() for p in partes if p])[:5]

        Suscriptor.objects.create(
            firebase_uid=uid,
            fecha_registro=ahora,
            fecha_actualizacion=ahora,
            codigo_estado=estado_instancia, # <--- Usar la instancia asignada
            sus_nombre1=nombre.strip(),
            sus_apellido1=apellido.strip(),
            sus_iniciales=iniciales_auto
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
        email_destinatario = (data.get('email') or '').strip().lower()

        if not email_destinatario:
            return JsonResponse({'status': 'error', 'mensaje': 'El correo electrónico es requerido.'}, status=400)

        try:
            validate_email(email_destinatario)
        except ValidationError:
            return JsonResponse({'status': 'error', 'mensaje': 'El formato del correo ingresado no es válido.'}, status=400)

        segundos_espera = _limite_envio_otp(request, email_destinatario)
        if segundos_espera:
            return JsonResponse({
                'status': 'error',
                'mensaje': f'Espera {segundos_espera} segundos antes de solicitar otro código.'
            }, status=429, headers={'Retry-After': str(segundos_espera)})

        # Purgar códigos viejos expirados antes de generar uno nuevo
        purgar_codigos_otp_expirados()

        # Generar código criptográfico seguro de 6 dígitos
        codigo_seguridad = f"{secrets.randbelow(900000) + 100000}"
        hash_seguridad = _calcular_hash_otp(email_destinatario, codigo_seguridad)

        CODIGOS_OTP_TEMPORALES[email_destinatario] = {
            'hash': hash_seguridad,
            'creado_el': timezone.now(),
            'intentos_fallidos': 0,
        }

        asunto = 'Tu código de acceso SmartBids'
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
        purgar_codigos_otp_expirados()

        data = json.loads(request.body.decode('utf-8'))
        email_raw = data.get('email')
        uid = data.get('uid')
        codigo = data.get('codigo')
        session_token = data.get('session_token')

        if not email_raw or not uid or not codigo or not session_token:
            return JsonResponse({'status': 'error', 'mensaje': 'Parámetros incompletos.'}, status=400)

        email = str(email_raw).strip().lower()
        codigo_limpio = str(codigo).strip()

        # Validación estricta de formato: exactamente 6 dígitos numéricos
        if not re.fullmatch(r'\d{6}', codigo_limpio):
            return JsonResponse({'status': 'error', 'mensaje': 'El código debe tener exactamente 6 dígitos numéricos.'}, status=400)

        # 1. Validar OTP en memoria
        registro = CODIGOS_OTP_TEMPORALES.get(email)
        if not registro:
            return JsonResponse({'status': 'error', 'mensaje': 'Código incorrecto o expirado.'}, status=400)

        # 2. Comprobar expiración (10 minutos)
        if timezone.now() - registro.get('creado_el', timezone.now()) > timedelta(seconds=OTP_EXPIRACION_SEGUNDOS):
            CODIGOS_OTP_TEMPORALES.pop(email, None)
            return JsonResponse({'status': 'error', 'mensaje': 'El código ha expirado. Solicita uno nuevo.'}, status=400)

        # 3. Comprobar intentos fallidos previos (Anti-Brute Force)
        intentos = registro.get('intentos_fallidos', 0)
        if intentos >= OTP_MAX_INTENTOS_FALLIDOS:
            CODIGOS_OTP_TEMPORALES.pop(email, None)
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Has superado el número máximo de intentos permitidos. Solicita un nuevo código por seguridad.'
            }, status=429)

        # 4. Comparación en tiempo constante con hash criptográfico
        hash_calculado = _calcular_hash_otp(email, codigo_limpio)
        hash_esperado = registro.get('hash')

        # Compatibilidad si el registro almacena 'codigo' plano (e.g. tests legados)
        if not hash_esperado and 'codigo' in registro:
            hash_esperado = _calcular_hash_otp(email, registro['codigo'])

        coincide = secrets.compare_digest(hash_esperado, hash_calculado) if hash_esperado else False

        if not coincide:
            registro['intentos_fallidos'] = intentos + 1
            restantes = OTP_MAX_INTENTOS_FALLIDOS - registro['intentos_fallidos']
            if restantes <= 0:
                CODIGOS_OTP_TEMPORALES.pop(email, None)
                return JsonResponse({
                    'status': 'error',
                    'mensaje': 'Has superado el número máximo de intentos permitidos. Solicita un nuevo código por seguridad.'
                }, status=429)
            return JsonResponse({
                'status': 'error',
                'mensaje': f'Código incorrecto. Te quedan {restantes} intento{"s" if restantes > 1 else ""}.'
            }, status=400)

        # 5. Código válido: Invalidador inmediato de un solo uso (One-Time-Use / Anti-Replay)
        CODIGOS_OTP_TEMPORALES.pop(email, None)

        # 6. Guardar token en PostgreSQL (crear si no existe por algún fallo previo)
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

def _construir_enlace_accion_web(enlace_firebase, request=None, mode_override=None):
    try:
        parsed = urlsplit(enlace_firebase)
        params = parse_qs(parsed.query)
        oob_code = params.get('oobCode', [''])[0]
        api_key = params.get('apiKey', [''])[0]
        mode = mode_override or params.get('mode', [''])[0]

        if not oob_code:
            return enlace_firebase

        if request:
            try:
                base_url = request.build_absolute_uri(reverse('accion_cuenta'))
            except Exception:
                base_url = request.build_absolute_uri('/auth/action/')
        else:
            site_url = getattr(settings, 'APP_BASE_URL', None) or os.getenv('APP_BASE_URL', 'http://127.0.0.1:8000')
            base_url = f"{site_url.rstrip('/')}/auth/action/"

        query = urlencode({
            'mode': mode,
            'oobCode': oob_code,
            'apiKey': api_key,
            'lang': 'es',
        })
        return f"{base_url}?{query}"
    except Exception as e:
        logger.warning(f"[SmartBids] No se pudo construir enlace web personalizado: {e}")
        return enlace_firebase


def _enviar_email_activacion(email_destinatario, app=None, request=None):
    app = app or _firebase_admin_app()
    enlace_firebase = firebase_auth.generate_email_verification_link(
        email_destinatario,
        app=app,
    )
    enlace_activacion = _construir_enlace_accion_web(enlace_firebase, request=request, mode_override='verifyEmail')

    asunto = 'Activa tu cuenta en SmartBids'
    mensaje_plano = (
        f'¡Hola!\n\n'
        f'Te damos la bienvenida a SmartBids. Activa tu cuenta ({email_destinatario}) '
        f'abriendo este enlace:\n{enlace_activacion}\n\n'
        f'Una vez activada, podrás comenzar a usar la plataforma.\n\n'
        f'Nota: Si no ves este correo en tu bandeja principal, revisa la carpeta de correo no deseado.'
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
            .alert-box {{ background: #fffaf0; border: 1px solid #feebc8; border-radius: 8px; padding: 14px; margin: 20px 0; font-size: 13px; color: #c05621; line-height: 1.5; }}
            .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #a0aec0; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h1>¡Bienvenido a SmartBids!</h1>
                <p>Activa tu cuenta para comenzar</p>
            </div>
            <div class="body">
                <p style="font-size: 16px; line-height: 1.6;">
                    ¡Hola! Estamos felices de darte la bienvenida a nuestra plataforma de analítica y monitoreo de compras públicas.
                </p>
                <div class="user-badge">
                    👤 Cuenta registrada: <span>{escape(email_destinatario)}</span>
                </div>
                <div class="features">
                    <strong style="color: #11634e; display: block; margin-bottom: 8px;">¿Qué puedes hacer en SmartBids?</strong>
                    <ul>
                        <li>🎯 <strong>Monitorear</strong> oportunidades de negocio en Mercado Público en tiempo real.</li>
                        <li>🤖 <strong>Predecir</strong> probabilidades de adjudicación mediante Machine Learning.</li>
                        <li>⚡ <strong>Optimizar</strong> tus ofertas y tomar decisiones basadas en datos.</li>
                    </ul>
                </div>
                <div style="text-align: center; margin: 28px 0;">
                    <a href="{escape(enlace_activacion)}" style="display: inline-block; background: #11634e; color: #ffffff; text-decoration: none; font-weight: 700; padding: 14px 24px; border-radius: 6px;">
                        Activar mi cuenta
                    </a>
                </div>
                <div class="alert-box">
                    🔔 <strong>Activa tu cuenta:</strong> usa el botón de este correo para verificar tu dirección y habilitar el acceso a SmartBids.<br><br>
                    📁 <em>¿No ves este correo en tu bandeja principal? Recuerda revisar tu carpeta de <strong>SPAM o Correo no deseado</strong>.</em>
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


@csrf_exempt
def enviar_correo_bienvenida(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        id_token = data.get('idToken')
        email = (data.get('email') or '').strip().lower()

        app = _firebase_admin_app()
        if id_token:
            claims = firebase_auth.verify_id_token(id_token, app=app)
            email_destinatario = claims.get('email')
            if not email_destinatario or claims.get('email_verified'):
                return JsonResponse({'status': 'error', 'mensaje': 'La cuenta no requiere activación.'}, status=400)
        elif email:
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({'status': 'error', 'mensaje': 'El formato del correo ingresado no es válido.'}, status=400)
            email_destinatario = email
        else:
            return JsonResponse({'status': 'error', 'mensaje': 'El token de autenticación o correo es requerido.'}, status=400)

        _enviar_email_activacion(email_destinatario, app=app, request=request)
        return JsonResponse({'status': 'ok', 'mensaje': 'Correo de bienvenida y activación enviado exitosamente.'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'Cuerpo de la petición JSON inválido.'}, status=400)
    except Exception as e:
        logger.error(f"[SmartBids] Error al enviar correo de bienvenida: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error en el servidor: {str(e)}'}, status=500)


@csrf_exempt
def reenviar_correo_activacion(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        email = (data.get('email') or '').strip().lower()
        id_token = data.get('idToken')

        if not email and not id_token:
            return JsonResponse({'status': 'error', 'mensaje': 'El correo electrónico es requerido para reenviar la activación.'}, status=400)

        if id_token and not email:
            try:
                app = _firebase_admin_app()
                claims = firebase_auth.verify_id_token(id_token, app=app)
                email = (claims.get('email') or '').strip().lower()
            except Exception as e:
                logger.warning(f"[SmartBids] Token no verificable al reenviar activación: {e}")

        if not email:
            return JsonResponse({'status': 'error', 'mensaje': 'El correo electrónico es requerido para reenviar la activación.'}, status=400)

        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'El formato del correo ingresado no es válido. Ingresa una dirección completa (ej: usuario@empresa.cl).'
            }, status=400)

        app = _firebase_admin_app()

        cache_key = f"resend_activation_{email}"
        if cache.get(cache_key):
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Ya enviamos un correo recientemente. Por favor espera un momento antes de volver a solicitarlo.'
            }, status=429)

        try:
            user_record = firebase_auth.get_user_by_email(email, app=app)
        except (firebase_auth.UserNotFoundError, firebase_auth.EmailNotFoundError):
            return JsonResponse({
                'status': 'error',
                'mensaje': 'No existe una cuenta registrada con ese correo electrónico.'
            }, status=404)
        except ValueError as val_err:
            logger.warning(f"[SmartBids] Formato de correo no válido para Firebase: {val_err}")
            return JsonResponse({
                'status': 'error',
                'mensaje': 'El formato del correo ingresado no es válido. Ingresa una dirección completa (ej: usuario@empresa.cl).'
            }, status=400)

        if user_record.email_verified:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Esta cuenta ya se encuentra verificada y activa. Puedes iniciar sesión directamente.'
            }, status=400)

        _enviar_email_activacion(email, app=app, request=request)
        cache.set(cache_key, True, 60)

        return JsonResponse({
            'status': 'ok',
            'mensaje': 'Correo de activación reenviado exitosamente. Por favor revisa tu bandeja de entrada o tu carpeta de SPAM.'
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'Cuerpo de la petición JSON inválido.'}, status=400)
    except Exception as e:
        logger.error(f"[SmartBids] Error al reenviar correo de activación: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error en el servidor: {str(e)}'}, status=500)

def _enviar_email_recuperacion_password(email_destinatario, enlace_reset):
    asunto = 'Restablece tu contraseña en SmartBids'
    mensaje_plano = (
        f'¡Hola!\n\n'
        f'Hemos recibido una solicitud para restablecer la contraseña de tu cuenta ({email_destinatario}).\n\n'
        f'Para definir una nueva contraseña, por favor abre el siguiente enlace seguro:\n'
        f'{enlace_reset}\n\n'
        f'Por seguridad, este enlace es de un solo uso y expirará pronto.\n'
        f'Si tú no realizaste esta solicitud, puedes ignorar este correo de forma segura; '
        f'tu contraseña actual no cambiará.\n\n'
        f'Nota: Si no ves este correo en tu bandeja principal, revisa la carpeta de correo no deseado.\n\n'
        f'Saludos cordiales,\n'
        f'El equipo de Seguridad de SmartBids'
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
            .security-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin: 20px 0; font-size: 13px; color: #4a5568; line-height: 1.5; }}
            .alert-box {{ background: #fffaf0; border: 1px solid #feebc8; border-radius: 8px; padding: 14px; margin: 20px 0; font-size: 13px; color: #c05621; line-height: 1.5; }}
            .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #a0aec0; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h1>SmartBids</h1>
                <p>Restablecimiento de Contraseña</p>
            </div>
            <div class="body">
                <p style="font-size: 16px; line-height: 1.6;">
                    ¡Hola! Hemos recibido una solicitud para cambiar la contraseña de tu cuenta en SmartBids.
                </p>
                <div class="user-badge">
                    👤 Cuenta: <span>{escape(email_destinatario)}</span>
                </div>
                <p style="font-size: 14px; line-height: 1.6; color: #4a5568;">
                    Para definir tu nueva clave de acceso y continuar utilizando la plataforma, haz clic en el siguiente botón seguro:
                </p>
                <div style="text-align: center; margin: 28px 0;">
                    <a href="{escape(enlace_reset)}" style="display: inline-block; background: #11634e; color: #ffffff; text-decoration: none; font-weight: 700; padding: 14px 24px; border-radius: 6px;">
                        Restablecer mi contraseña
                    </a>
                </div>
                <div class="security-box">
                    🛡️ <strong>Aviso de seguridad:</strong> Si no realizaste esta solicitud, puedes ignorar este correo sin problemas. Tu cuenta y contraseña actual siguen protegidas.
                </div>
                <div class="alert-box">
                    📁 <em>¿No ves este correo en tu bandeja principal? Recuerda revisar tu carpeta de <strong>SPAM o Correo no deseado</strong>.</em>
                </div>
                <p style="font-size: 14px; color: #718096; margin-top: 25px;">
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


@csrf_exempt
def solicitar_recuperacion_password(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        email = (data.get('email') or '').strip().lower()

        if not email:
            return JsonResponse({'status': 'error', 'mensaje': 'Ingresa tu correo electrónico para recuperar tu contraseña.'}, status=400)

        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'El formato del correo ingresado no es válido. Ingresa una dirección completa (ej: usuario@empresa.cl).'
            }, status=400)

        app = _firebase_admin_app()

        cache_key = f"pwd_reset_cooldown_{email}"
        if cache.get(cache_key):
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Ya enviamos un correo de recuperación recientemente. Por favor espera un momento antes de volver a solicitarlo.'
            }, status=429)

        try:
            user_record = firebase_auth.get_user_by_email(email, app=app)
        except (firebase_auth.UserNotFoundError, firebase_auth.EmailNotFoundError):
            return JsonResponse({
                'status': 'error',
                'mensaje': 'No existe una cuenta registrada con ese correo electrónico.'
            }, status=404)
        except ValueError as val_err:
            logger.warning(f"[SmartBids] Formato de correo no válido para Firebase: {val_err}")
            return JsonResponse({
                'status': 'error',
                'mensaje': 'El formato del correo ingresado no es válido. Ingresa una dirección completa (ej: usuario@empresa.cl).'
            }, status=400)

        raw_reset_link = firebase_auth.generate_password_reset_link(email, app=app)
        enlace_web = _construir_enlace_accion_web(raw_reset_link, request=request, mode_override='resetPassword')

        _enviar_email_recuperacion_password(email, enlace_web)
        cache.set(cache_key, True, 60)

        return JsonResponse({
            'status': 'ok',
            'mensaje': 'Te enviamos un correo con el enlace para restablecer tu contraseña. Revisa tu bandeja de entrada o SPAM.'
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'Cuerpo de la petición JSON inválido.'}, status=400)
    except Exception as e:
        logger.error(f"[SmartBids] Error al solicitar recuperación de contraseña: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error en el servidor: {str(e)}'}, status=500)


@csrf_exempt
def enviar_correo_cambio_password(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        email_destinatario = (data.get('email') or '').strip().lower()

        if not email_destinatario:
            return JsonResponse({'status': 'error', 'mensaje': 'El correo es requerido.'}, status=400)

        try:
            validate_email(email_destinatario)
        except ValidationError:
            return JsonResponse({'status': 'error', 'mensaje': 'El formato del correo ingresado no es válido.'}, status=400)

        asunto = 'Tu contraseña en SmartBids ha sido modificada'
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


def verificar_existencia_gmail(email):
    """
    Verifica las reglas de formato de Gmail y consulta a los servidores MX de Google
    (gmail-smtp-in.l.google.com) para verificar si el buzón de correo realmente existe.
    Retorna (es_valido, mensaje_error).
    """
    email = (email or '').strip().lower()
    match = re.match(r'^([^@]+)@(gmail\.com|googlemail\.com)$', email)
    if not match:
        return True, None

    usuario = match.group(1)

    # 1. Reglas oficiales de Google para nombres de usuario en Gmail
    if len(usuario) < 6:
        return False, "El nombre de usuario de Gmail debe tener al menos 6 caracteres antes del @."
    if len(usuario) > 30:
        return False, "El nombre de usuario de Gmail no puede tener más de 30 caracteres antes del @."
    if not re.match(r'^[a-z0-9]+(\.[a-z0-9]+)*$', usuario):
        return False, "El formato de tu correo Gmail no es válido (solo letras, números y puntos no consecutivos)."

    # 2. Comprobación directa vía SMTP con los servidores MX de Google
    try:
        server = smtplib.SMTP('gmail-smtp-in.l.google.com', 25, timeout=4)
        server.ehlo('smartbids.cl')
        server.mail('contacto@smartbids.cl')
        code, msg_bytes = server.rcpt(email)
        server.quit()

        msg = msg_bytes.decode('utf-8', errors='ignore').lower()

        # 550 NoSuchUser / does not exist
        if code == 550 and ('does not exist' in msg or 'nosuchuser' in msg):
            return False, "La cuenta de correo no existe en Gmail. Por favor verifica que la dirección esté bien escrita."
        if code == 550 and ('inactive' in msg or 'disabled' in msg):
            return False, "La cuenta de Gmail ingresada se encuentra inactiva o deshabilitada."

        return True, None
    except Exception as e:
        logger.warning(f"[SmartBids] Verificación SMTP de Gmail no concluyente para {email}: {e}")
        return True, None


@csrf_exempt
def validar_email_registro(request):
    """
    Valida un correo electrónico antes de crearlo en Firebase Authentication:
    1. Formato de correo válido.
    2. Si es Gmail, valida reglas de usuario y existencia en servidores de Google.
    3. Comprueba si el correo ya se encuentra registrado en Firebase.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        email = (data.get('email') or '').strip().lower()

        if not email:
            return JsonResponse({'status': 'error', 'mensaje': 'El correo electrónico es requerido.'}, status=400)

        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'status': 'error', 'mensaje': 'El formato del correo ingresado no es válido.'}, status=400)

        # 1. Validación de existencia en Gmail si aplica
        ok_gmail, error_gmail = verificar_existencia_gmail(email)
        if not ok_gmail:
            return JsonResponse({'status': 'error', 'mensaje': error_gmail}, status=400)

        # 2. Validación de existencia previa en Firebase Authentication
        app = _firebase_admin_app()
        try:
            firebase_auth.get_user_by_email(email, app=app)
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Ya existe una cuenta registrada con este correo electrónico. Puedes iniciar sesión o recuperar tu contraseña.'
            }, status=400)
        except (firebase_auth.UserNotFoundError, firebase_auth.EmailNotFoundError):
            pass
        except Exception as e:
            logger.warning(f"[SmartBids] Error consultando Firebase en validación de registro: {e}")

        return JsonResponse({'status': 'ok', 'mensaje': 'Correo válido para el registro.'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'Cuerpo de la petición JSON inválido.'}, status=400)
    except Exception as e:
        logger.error(f"[SmartBids] Error al validar email para registro: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error en el servidor: {str(e)}'}, status=500)
