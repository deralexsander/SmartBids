import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone


from .models import Suscriptor, Mensajeria, Empresa, Preferencia, EstadoSuscriptor


logger = logging.getLogger(__name__)



@csrf_exempt
def obtener_perfil_suscriptor(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')

        if not uid:
            return JsonResponse({'status': 'error', 'mensaje': 'UID requerido.'}, status=400)

        # Usamos select_related para traer en una sola consulta el registro de config.estado_suscriptor
        suscriptor = Suscriptor.objects.select_related('codigo_estado', 'sus_rut_empresa').filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'error', 'mensaje': 'Suscriptor no encontrado.'}, status=404)

        # Leer el nombre directamente del modelo EstadoSuscriptor de PostgreSQL
        nombre_estado_bd = suscriptor.codigo_estado.nombre_estado if suscriptor.codigo_estado else 'Sin Estado'
        id_estado_bd = suscriptor.codigo_estado.codigo_estado if suscriptor.codigo_estado else None

        # Preferencias y Empresa
        pref = getattr(suscriptor, 'preferencia', None)
        emp = suscriptor.sus_rut_empresa

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
                'codigo_estado': id_estado_bd,
                'nombre_estado': nombre_estado_bd,  # <--- LEÍDO DIRECTO DE POSTGRESQL
                'token_sesion': getattr(suscriptor, 'token_sesion', '') or '',
                'fecha_registro': suscriptor.fecha_registro.isoformat() if suscriptor.fecha_registro else None,
                'fecha_actualizacion': suscriptor.fecha_actualizacion.isoformat() if suscriptor.fecha_actualizacion else None,
                'empresa': {
                    'emp_rut': emp.emp_rut if emp else '',
                    'emp_fantasia': emp.emp_nombre_fantasia if emp else '',
                    'emp_razon_social': emp.emp_razon_social if emp else '',
                    'emp_contacto_correo': emp.emp_contacto_correo if emp else '',
                    'emp_iniciales': emp.emp_iniciales if emp else '',
                    'emp_contacto_telefono': emp.emp_contacto_telefono if emp else '',
                    'emp_codigo_comuna': emp.emp_codigo_comuna_id if emp else '',
                    'emp_direccion': emp.emp_direccion if emp else '',
                } if emp else {},
                'preferencias': {
                    'pref_comunas': ', '.join(pref.pref_comunas) if pref and pref.pref_comunas else '',
                    'pref_productos': ', '.join(pref.pref_productos) if pref and pref.pref_productos else '',
                    'pref_tipo_licitacion': ', '.join(pref.pref_tipo_licitacion) if pref and pref.pref_tipo_licitacion else '',
                    'pref_ucom': ', '.join(map(str, pref.pref_ucom)) if pref and pref.pref_ucom else '',
                    'pref_palabras_claves': ', '.join(pref.pref_palabras_claves) if pref and pref.pref_palabras_claves else '',
                } if pref else {}
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)
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
