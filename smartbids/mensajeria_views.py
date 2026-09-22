import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


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
