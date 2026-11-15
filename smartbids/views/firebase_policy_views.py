import json
import os
from datetime import datetime, timezone as datetime_timezone

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

from .mensajeria_views import _respuesta_acceso_denegado, _usuario_es_administrador
from smartbids.models import EstadoSuscriptor, Preferencia, Suscriptor
from smartbids.models.config import registrar_auditoria_admin, notificar_accion_entre_administradores, notificar_cambio_rol_suscriptor


GOOGLE_CLOUD_SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
GOOGLE_REQUEST_TIMEOUT_SECONDS = 8


def _firebase_admin_session():
    """
    Obtiene la sesión autorizada.
    Prioriza variables explícitas y, si no existen debido a restricciones de organización,
    utiliza Application Default Credentials (ADC) de la máquina/servidor.
    """
    service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    if service_account_json:
        credentials_info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=GOOGLE_CLOUD_SCOPES
        )
    elif credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=GOOGLE_CLOUD_SCOPES
        )
    else:
        # Fallback para desarrollo/servidor sin archivo de claves:
        # Detecta la sesión activa de gcloud CLI o credenciales del entorno
        credentials, _ = google.auth.default(scopes=GOOGLE_CLOUD_SCOPES)

    return AuthorizedSession(credentials)


def _firebase_config_url():
    project_id = settings.FIREBASE_CONFIG.get('projectId')
    if not project_id:
        raise RuntimeError('No hay projectId de Firebase configurado.')
    return f'https://identitytoolkit.googleapis.com/v2/projects/{project_id}/config'


def _firebase_accounts_url():
    project_id = settings.FIREBASE_CONFIG.get('projectId')
    if not project_id:
        raise RuntimeError('No hay projectId de Firebase configurado.')
    return f'https://identitytoolkit.googleapis.com/v1/projects/{project_id}/accounts'


def _fecha_firebase(valor):
    if not valor:
        return None
    try:
        return datetime.fromtimestamp(int(valor) / 1000, tz=datetime_timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def _listar_usuarios_firebase(session, url):
    response = session.post(
        f'{url}:query',
        json={'returnUserInfo': True, 'limit': '500', 'sortBy': 'CREATED_AT', 'order': 'DESC'},
        timeout=GOOGLE_REQUEST_TIMEOUT_SECONDS
    )
    data = response.json()
    if not response.ok:
        return response, data

    suscriptores = {
        suscriptor.firebase_uid: suscriptor
        for suscriptor in Suscriptor.objects.select_related('codigo_estado').all()
    }
    usuarios = []
    for user in data.get('userInfo', []):
        uid = user.get('localId', '')
        providers = user.get('providerUserInfo', [])
        suscriptor = suscriptores.get(uid)
        usuarios.append({
            'uid': uid,
            'email': user.get('email', ''),
            'emailVerified': bool(user.get('emailVerified', False)),
            'proveedores': [provider.get('providerId', '') for provider in providers],
            'fecha_creacion': _fecha_firebase(user.get('createdAt')),
            'fecha_acceso': _fecha_firebase(user.get('lastLoginAt')),
            'estado': suscriptor.codigo_estado.nombre_estado if suscriptor and suscriptor.codigo_estado else 'Sin estado',
            'codigo_estado': suscriptor.codigo_estado_id if suscriptor else None,
            'firebase_deshabilitado': bool(user.get('disabled', False)),
        })
    return response, usuarios


_CACHE_POLITICA_PUBLICA = None
_CACHE_POLITICA_TIMESTAMP = 0
_CACHE_POLITICA_TTL_SEGUNDOS = 5


def _extraer_politica_limpia(data):
    if not isinstance(data, dict):
        data = {}

    policy_config = data.get('passwordPolicyConfig', data)
    versions = policy_config.get('passwordPolicyVersions', [])
    options = versions[0].get('customStrengthOptions', {}) if versions else {}
    enforcement = policy_config.get('passwordPolicyEnforcementState', 'OFF')

    min_len = int(options.get('minPasswordLength') or 6)
    max_len = int(options.get('maxPasswordLength') or 4096)

    return {
        'status': 'ok',
        'enforcementState': enforcement,
        'forceUpgradeOnSignin': bool(policy_config.get('forceUpgradeOnSignin', False)),
        'minPasswordLength': min_len,
        'maxPasswordLength': max_len,
        'containsUppercaseCharacter': bool(options.get('containsUppercaseCharacter', False)),
        'containsLowercaseCharacter': bool(options.get('containsLowercaseCharacter', False)),
        'containsNumericCharacter': bool(options.get('containsNumericCharacter', False)),
        'containsNonAlphanumericCharacter': bool(options.get('containsNonAlphanumericCharacter', False)),
    }


def obtener_politica_activa(forzar_recarga=False):
    global _CACHE_POLITICA_PUBLICA, _CACHE_POLITICA_TIMESTAMP
    ahora = datetime.now().timestamp()
    if not forzar_recarga and _CACHE_POLITICA_PUBLICA and (ahora - _CACHE_POLITICA_TIMESTAMP < _CACHE_POLITICA_TTL_SEGUNDOS):
        return _CACHE_POLITICA_PUBLICA

    try:
        session = _firebase_admin_session()
        url = _firebase_config_url()
        response = session.get(url, timeout=GOOGLE_REQUEST_TIMEOUT_SECONDS)
        if response.ok:
            data = response.json()
            limpia = _extraer_politica_limpia(data)
            _CACHE_POLITICA_PUBLICA = limpia
            _CACHE_POLITICA_TIMESTAMP = ahora
            return limpia
    except Exception as e:
        print("[SmartBids] Error consultando política de contraseñas de Firebase:", e)

    if _CACHE_POLITICA_PUBLICA:
        return _CACHE_POLITICA_PUBLICA

    return {
        'status': 'ok',
        'enforcementState': 'ENFORCE',
        'forceUpgradeOnSignin': False,
        'minPasswordLength': 6,
        'maxPasswordLength': 4096,
        'containsUppercaseCharacter': True,
        'containsLowercaseCharacter': True,
        'containsNumericCharacter': True,
        'containsNonAlphanumericCharacter': True,
    }


def actualizar_cache_politica(data_nueva):
    global _CACHE_POLITICA_PUBLICA, _CACHE_POLITICA_TIMESTAMP
    try:
        _CACHE_POLITICA_PUBLICA = _extraer_politica_limpia(data_nueva)
        _CACHE_POLITICA_TIMESTAMP = datetime.now().timestamp()
    except Exception as e:
        print("[SmartBids] Error actualizando caché de política:", e)


def politica_contrasenas_publica(request):
    """
    Endpoint público (GET) que devuelve los requisitos de contraseña activos
    para que la interfaz de registro, perfil y reseteo se adapten dinámicamente.
    """
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    politica = obtener_politica_activa()
    response = JsonResponse(politica)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@csrf_exempt
def politica_contrasenas_firebase(request):
    # Verificación de permisos: solo administradores pueden consultar o modificar
    if not _usuario_es_administrador(request):
        return _respuesta_acceso_denegado()

    try:
        session = _firebase_admin_session()
        url = _firebase_config_url()

        # Obtener la política actual configurada en Identity Platform
        if request.method == 'GET':
            response = session.get(url, timeout=GOOGLE_REQUEST_TIMEOUT_SECONDS)
            if response.ok:
                actualizar_cache_politica(response.json())
            return JsonResponse(response.json(), status=response.status_code, safe=False)

        # Guardar la nueva configuración de contraseñas
        if request.method == 'PATCH':
            data = json.loads(request.body.decode('utf-8'))
            response = session.patch(
                url,
                params={'updateMask': 'passwordPolicyConfig'},
                json={'passwordPolicyConfig': data},
                timeout=GOOGLE_REQUEST_TIMEOUT_SECONDS
            )
            if response.ok:
                actualizar_cache_politica(response.json())
            return JsonResponse(response.json(), status=response.status_code, safe=False)

        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido.'}, status=400)
    except Exception as error:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(error)
        }, status=503)


@csrf_exempt
def usuarios_firebase(request):
    if not _usuario_es_administrador(request):
        return _respuesta_acceso_denegado()

    try:
        session = _firebase_admin_session()
        url = _firebase_accounts_url()

        if request.method == 'GET':
            response, usuarios = _listar_usuarios_firebase(session, url)
            if not response.ok:
                return JsonResponse(usuarios, status=response.status_code, safe=False)
            return JsonResponse({
                'usuarios': usuarios,
                'estados': list(EstadoSuscriptor.objects.values('codigo_estado', 'nombre_estado'))
            })

        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        uid = (data.get('uid') or request.GET.get('uid') or '').strip()
        if not uid:
            return JsonResponse({'status': 'error', 'mensaje': 'UID requerido.'}, status=400)

        # Identificar al administrador ejecutor
        uid_ejecutor = (request.headers.get('X-Firebase-UID') or request.COOKIES.get('sb_firebase_uid') or '').strip()
        suscriptor_ejecutor = Suscriptor.objects.select_related('codigo_estado').filter(firebase_uid=uid_ejecutor).first() if uid_ejecutor else None
        email_ejecutor = (
            request.headers.get('X-Firebase-Email')
            or (suscriptor_ejecutor.sus_nombre_social if suscriptor_ejecutor and '@' in (suscriptor_ejecutor.sus_nombre_social or '') else None)
        )
        if (not email_ejecutor or '@' not in email_ejecutor) and session and url and uid_ejecutor:
            try:
                lookup_ejecutor = session.post(
                    f'{url}:lookup',
                    json={'localId': [uid_ejecutor]},
                    timeout=GOOGLE_REQUEST_TIMEOUT_SECONDS
                )
                if lookup_ejecutor.ok:
                    users_fb = lookup_ejecutor.json().get('users', [])
                    if users_fb and users_fb[0].get('email'):
                        email_ejecutor = users_fb[0]['email']
            except Exception:
                pass
        if not email_ejecutor:
            email_ejecutor = 'smartbids.qa@chileavanza.cl'

        nombre_ejecutor = (
            f"{suscriptor_ejecutor.sus_nombre1} {suscriptor_ejecutor.sus_apellido1 or ''}".strip()
            if suscriptor_ejecutor and suscriptor_ejecutor.sus_nombre1
            else email_ejecutor
        )

        # Regla 1: Bloquear auto-eliminación y auto-remoción de rol administrador
        if uid and uid_ejecutor and uid == uid_ejecutor:
            if request.method == 'DELETE':
                return JsonResponse({
                    'status': 'error',
                    'mensaje': 'Por motivos de seguridad, un administrador no puede eliminar su propia cuenta desde el panel de control.'
                }, status=403)
            if request.method == 'PATCH':
                estado_id = data.get('codigo_estado')
                estado = EstadoSuscriptor.objects.filter(codigo_estado=estado_id).first()
                if estado and estado.nombre_estado.strip().casefold() != 'administrador':
                    return JsonResponse({
                        'status': 'error',
                        'mensaje': 'Por motivos de seguridad, un administrador no puede revocar su propio rol de administrador.'
                    }, status=403)

        suscriptor = Suscriptor.objects.select_related('codigo_estado').filter(firebase_uid=uid).first()
        es_admin_afectado = False
        if suscriptor and suscriptor.codigo_estado:
            es_admin_afectado = (
                suscriptor.codigo_estado.nombre_estado.strip().casefold() == 'administrador'
                or suscriptor.codigo_estado.codigo_estado == 5
            )

        email_afectado = (
            data.get('email')
            or request.GET.get('email')
            or (suscriptor.sus_nombre_social if suscriptor and '@' in (suscriptor.sus_nombre_social or '') else '')
        )
        if (not email_afectado or '@' not in email_afectado) and session and url and uid:
            try:
                lookup_resp = session.post(
                    f'{url}:lookup',
                    json={'localId': [uid]},
                    timeout=GOOGLE_REQUEST_TIMEOUT_SECONDS
                )
                if lookup_resp.ok:
                    users_fb = lookup_resp.json().get('users', [])
                    if users_fb and users_fb[0].get('email'):
                        email_afectado = users_fb[0]['email']
            except Exception as e:
                logger.warning(f"[SmartBids] Error al consultar email en Firebase para UID {uid}: {e}")
        if not email_afectado:
            email_afectado = (suscriptor.sus_nombre_social if suscriptor else '') or 'admin@smartbids.cl'

        nombre_afectado = (
            f"{suscriptor.sus_nombre1} {suscriptor.sus_apellido1 or ''}".strip()
            if suscriptor and suscriptor.sus_nombre1
            else (email_afectado.split('@')[0] if '@' in email_afectado else email_afectado)
        )

        if request.method == 'PATCH':
            estado_id = data.get('codigo_estado')
            estado = EstadoSuscriptor.objects.filter(codigo_estado=estado_id).first()
            if not estado:
                return JsonResponse({'status': 'error', 'mensaje': 'Estado no válido.'}, status=400)
            if not suscriptor:
                return JsonResponse({
                    'status': 'error',
                    'mensaje': 'No se puede cambiar el estado: el usuario no existe en PostgreSQL.'
                }, status=404)

            estado_anterior = suscriptor.codigo_estado
            es_anterior_admin = es_admin_afectado
            es_nuevo_admin = (
                estado.codigo_estado == 5
                or estado.nombre_estado.strip().casefold() == 'administrador'
            )

            # Auditar y notificar si el usuario era admin y cambia a no-admin
            if es_anterior_admin and not es_nuevo_admin:
                registrar_auditoria_admin(
                    ejecutor_uid=uid_ejecutor,
                    ejecutor_email=email_ejecutor,
                    ejecutor_nombre=nombre_ejecutor,
                    afectado_uid=uid,
                    afectado_email=email_afectado,
                    afectado_nombre=nombre_afectado,
                    accion='CAMBIO_ROL',
                    detalle=f"El administrador {email_ejecutor} modificó el rol de {email_afectado} a '{estado.nombre_estado}'.",
                    ip_origen=request.META.get('REMOTE_ADDR')
                )
            elif es_nuevo_admin and not es_anterior_admin:
                registrar_auditoria_admin(
                    ejecutor_uid=uid_ejecutor,
                    ejecutor_email=email_ejecutor,
                    ejecutor_nombre=nombre_ejecutor,
                    afectado_uid=uid,
                    afectado_email=email_afectado,
                    afectado_nombre=nombre_afectado,
                    accion='ASIGNACION_ADMIN',
                    detalle=f"El administrador {email_ejecutor} otorgó el rol de Administrador a {email_afectado}.",
                    ip_origen=request.META.get('REMOTE_ADDR')
                )

            # Notificación formal por correo electrónico según la transición de estado
            notificar_cambio_rol_suscriptor(
                ejecutor_email=email_ejecutor,
                ejecutor_nombre=nombre_ejecutor,
                afectado_email=email_afectado,
                afectado_nombre=nombre_afectado,
                estado_anterior=estado_anterior,
                estado_nuevo=estado
            )

            suscriptor.codigo_estado = estado
            suscriptor.fecha_actualizacion = timezone.now()
            suscriptor.save(update_fields=['codigo_estado', 'fecha_actualizacion'])
            return JsonResponse({'status': 'ok', 'mensaje': 'Estado actualizado correctamente.'})

        if request.method == 'DELETE':
            response = session.post(
                f'{url}:delete',
                json={'localId': uid},
                timeout=GOOGLE_REQUEST_TIMEOUT_SECONDS
            )
            if not response.ok and response.status_code != 404:
                return JsonResponse(response.json(), status=response.status_code, safe=False)

            if es_admin_afectado:
                registrar_auditoria_admin(
                    ejecutor_uid=uid_ejecutor,
                    ejecutor_email=email_ejecutor,
                    ejecutor_nombre=nombre_ejecutor,
                    afectado_uid=uid,
                    afectado_email=email_afectado,
                    afectado_nombre=nombre_afectado,
                    accion='ELIMINACION',
                    detalle=f"El administrador {email_ejecutor} ({nombre_ejecutor}) eliminó la cuenta del administrador {email_afectado}.",
                    ip_origen=request.META.get('REMOTE_ADDR')
                )
                notificar_accion_entre_administradores(
                    ejecutor_email=email_ejecutor,
                    ejecutor_nombre=nombre_ejecutor,
                    afectado_email=email_afectado,
                    accion='Eliminación de cuenta de administrador',
                    detalle=f"Tu cuenta de administrador fue eliminada por el administrador {email_ejecutor} ({nombre_ejecutor})."
                )

            if suscriptor:
                Preferencia.objects.filter(id_suscriptor=suscriptor).delete()
                suscriptor.delete()
            return JsonResponse({'status': 'ok', 'mensaje': 'Usuario eliminado de Firebase y PostgreSQL.'})

        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido.'}, status=400)
    except Exception as error:
        return JsonResponse({'status': 'error', 'mensaje': str(error)}, status=503)