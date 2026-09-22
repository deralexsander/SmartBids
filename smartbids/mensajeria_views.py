import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models.config import ParametroGlobal
from .models import Mensajeria, Suscriptor

def _usuario_es_administrador(request):
    uid = request.headers.get('X-Firebase-UID')
    if not uid:
        return False

    suscriptor = Suscriptor.objects.select_related('codigo_estado').filter(
        firebase_uid=uid
    ).first()
    nombre_estado = suscriptor.codigo_estado.nombre_estado if suscriptor and suscriptor.codigo_estado else ''
    return nombre_estado.strip().casefold() == 'administrador'


def _respuesta_acceso_denegado():
    return JsonResponse({
        'status': 'error',
        'mensaje': 'Acceso denegado: se requieren permisos de administrador.'
    }, status=403)



@csrf_exempt
def listar_crear_mensajes(request):
    if not _usuario_es_administrador(request):
        return _respuesta_acceso_denegado()

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
    if not _usuario_es_administrador(request):
        return _respuesta_acceso_denegado()

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





@csrf_exempt
def parametro_alerta_perfil(request):
    if request.method == 'GET':
        datos = {
            'porcentaje_minimo': 90,
            'dias_reaparicion': 7
        }
        try:
            parametros = ParametroGlobal.objects.filter(codigo_parametro__in=[1, 2])
            for p in parametros:
                if p.codigo_parametro == 1:
                    datos['porcentaje_minimo'] = p.valor_parametro
                elif p.codigo_parametro == 2:
                    datos['dias_reaparicion'] = p.valor_parametro
            return JsonResponse({'status': 'ok', 'datos': datos})
        except Exception as e:
            print("❌ Error en Postgres al leer config.parametros_globales:", e)
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

    elif request.method in ['POST', 'PATCH', 'PUT']:
        if not _usuario_es_administrador(request):
            return _respuesta_acceso_denegado()

        try:
            body = json.loads(request.body.decode('utf-8'))
            umbral = int(body.get('porcentaje_minimo', 90))
            dias = int(body.get('dias_reaparicion', 7))

            ParametroGlobal.objects.update_or_create(
                codigo_parametro=1,
                defaults={
                    'nombre_parametro': 'porcentaje_minimo_requerido',
                    'valor_parametro': umbral,
                    'descripcion': 'Si el usuario tiene menos de este valor (%), se muestra el aviso'
                }
            )

            ParametroGlobal.objects.update_or_create(
                codigo_parametro=2,
                defaults={
                    'nombre_parametro': 'dias_reaparicion_omitir',
                    'valor_parametro': dias,
                    'descripcion': 'Días de espera antes de volver a consultar al usuario'
                }
            )

            return JsonResponse({'status': 'ok', 'mensaje': 'Ajustes guardados en PostgreSQL.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)
    """
    GET: Lee el porcentaje y los días de espera (para perfil.js y el modal).
    POST / PATCH: Actualiza los valores en PostgreSQL (solo para admin).
    """
    if request.method == 'GET':
        # Valores por defecto de contingencia
        datos = {
            'porcentaje_minimo': 90,
            'dias_reaparicion': 7
        }
        try:
            parametros = ParametroGlobal.objects.filter(codigo_parametro__in=[1, 2])
            for p in parametros:
                if p.codigo_parametro == 1:
                    datos['porcentaje_minimo'] = p.valor_parametro
                elif p.codigo_parametro == 2:
                    datos['dias_reaparicion'] = p.valor_parametro
            return JsonResponse({'status': 'ok', 'datos': datos})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

    elif request.method in ['POST', 'PATCH', 'PUT']:
        if not _usuario_es_administrador(request):
            return _respuesta_acceso_denegado()

        try:
            body = json.loads(request.body.decode('utf-8'))
            umbral = int(body.get('porcentaje_minimo', 90))
            dias = int(body.get('dias_reaparicion', 7))

            if not (0 <= umbral <= 100):
                return JsonResponse({'status': 'error', 'mensaje': 'El porcentaje debe estar entre 0 y 100.'}, status=400)
            if not (1 <= dias <= 99):
                return JsonResponse({'status': 'error', 'mensaje': 'Los días deben estar entre 1 y 99.'}, status=400)

            # Actualiza o crea fila 1 (porcentaje)
            ParametroGlobal.objects.update_or_create(
                codigo_parametro=1,
                defaults={
                    'nombre_parametro': 'porcentaje_minimo_requerido',
                    'valor_parametro': umbral,
                    'descripcion': 'Si el usuario tiene menos de este valor (%), se muestra el aviso'
                }
            )

            # Actualiza o crea fila 2 (días)
            ParametroGlobal.objects.update_or_create(
                codigo_parametro=2,
                defaults={
                    'nombre_parametro': 'dias_reaparicion_omitir',
                    'valor_parametro': dias,
                    'descripcion': 'Días de espera antes de volver a consultar al usuario'
                }
            )

            return JsonResponse({'status': 'ok', 'mensaje': 'Parámetros actualizados correctamente en PostgreSQL.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)