import logging
from datetime import datetime, time, timedelta
from urllib.parse import urlparse
from urllib.parse import parse_qs

from django.db import transaction
from django.http import HttpResponseForbidden, HttpResponseGone, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie

from .licitacion_utils import (
    ESTADOS_LICITACION,
    estado_licitacion,
    hito_completado,
    resolver_suscriptor,
)
from .mercadopublico_service import obtener_datos_externos_licitacion
from .models.procurement import Licitacion
from .models.core import (
    LicitacionDocumento,
    LicitacionPregunta,
    NotificacionLicitacion,
    SeguimientoLicitacion,
)

logger = logging.getLogger(__name__)


def detalle_licitacion_view(request, codigo):
    licitacion = get_object_or_404(
        Licitacion.objects.select_related('lic_codigo_ucom'),
        lic_codigo=codigo,
    )
    suscriptor = resolver_suscriptor(request)
    if suscriptor:
        _sincronizar_seguimientos(suscriptor)
    seguimiento = None
    if suscriptor:
        seguimiento = SeguimientoLicitacion.objects.filter(
            usuario=suscriptor,
            licitacion=licitacion,
            seguimiento_activo=True,
        ).first()

    estado, estado_label = estado_licitacion(licitacion)
    ahora = timezone.now()
    return_to = request.GET.get('return_to', '')
    if not _es_retornos_local(return_to, request):
        return_to = reverse('mis_licitaciones')
    query_return_to = parse_qs(urlparse(return_to).query)
    historial = [
        ('Publicación', licitacion.lic_fecha_public, 'publicada'),
        ('Fecha límite de preguntas', licitacion.lic_fecha_preguntas, 'preguntas'),
        ('Publicación de respuestas', licitacion.lic_fecha_respuestas, 'ofertas'),
        ('Cierre del proceso', licitacion.lic_fecha_cierre, 'cerrada'),
    ]
    hitos = [
        {
            'nombre': nombre,
            'fecha': fecha,
            'completado': hito_completado(fecha, ahora),
            'estado': estado_hito,
        }
        for nombre, fecha, estado_hito in historial
        if fecha
    ]

    # --- Prioridad Base de Datos vs. Mercado Público ---
    # 1. Documentos oficiales: se priorizan los registrados en la BD
    documentos = list(LicitacionDocumento.objects.filter(licitacion=licitacion))
    tiene_documentos_db = bool(documentos)

    # 2. Preguntas y respuestas oficiales: se priorizan las registradas en la BD
    preguntas_db = list(LicitacionPregunta.objects.filter(licitacion=licitacion))
    tiene_preguntas_db = bool(preguntas_db)
    if tiene_preguntas_db:
        preguntas = [
            {
                'numero': idx + 1,
                'pregunta': p.pregunta,
                'fecha_pregunta': p.fecha_pregunta.strftime('%d-%m-%Y %H:%M') if p.fecha_pregunta else '',
                'respuesta': p.respuesta,
                'fecha_respuesta': p.fecha_respuesta.strftime('%d-%m-%Y %H:%M') if p.fecha_respuesta else '',
            }
            for idx, p in enumerate(preguntas_db)
        ]
    else:
        preguntas = []

    # 3. Descripción del proceso: se prioriza la registrada en la BD
    tiene_descripcion_db = bool(
        (licitacion.lic_descripcion and licitacion.lic_descripcion.strip())
        or (licitacion.lic_texto and licitacion.lic_texto.strip())
    )

    # 4. Llamado diferido / condicional a Mercado Público:
    # Solo si la base de datos no contiene algún dato requerido se consulta externamente
    url_adjuntos = None
    url_preguntas = None
    direccion_fallback = None

    necesita_datos_externos = (
        not tiene_descripcion_db
        or not tiene_documentos_db
        or not tiene_preguntas_db
    )

    if necesita_datos_externos:
        datos_externos = obtener_datos_externos_licitacion(
            licitacion.lic_codigo,
            url_licitacion=licitacion.lic_url,
        )

        # Si no había descripción en la BD, usamos la rescatada desde Mercado Público
        if not tiene_descripcion_db:
            desc_externa = (datos_externos.get('descripcion') or '').strip()
            if desc_externa:
                licitacion.lic_descripcion = desc_externa
                try:
                    Licitacion.objects.filter(lic_codigo=licitacion.lic_codigo).update(lic_descripcion=desc_externa)
                except Exception as ex_db:
                    logger.warning('Error guardando descripción externa en BD para %s: %s', licitacion.lic_codigo, ex_db)

        # Si no había documentos en la BD, proveemos el enlace oficial al repositorio de adjuntos
        if not tiene_documentos_db:
            url_adjuntos = datos_externos.get('url_adjuntos')

        # Si no había preguntas en la BD, proveemos las del foro oficial y su enlace
        if not tiene_preguntas_db:
            preguntas = datos_externos.get('preguntas', [])
            url_preguntas = datos_externos.get('url_preguntas')

        # Si la unidad de compra no tiene dirección en BD, usamos el fallback
        if not (licitacion.lic_codigo_ucom and licitacion.lic_codigo_ucom.ucom_direccion):
            direccion_fallback = datos_externos.get('direccion')

    url_externa = _url_http(licitacion.lic_url)
    if not url_externa and licitacion.lic_codigo:
        url_externa = f'https://www.mercadopublico.cl/fichaLicitacion.html?idLicitacion={licitacion.lic_codigo}'

    return render(request, 'smartbids/licitacion_detalle.html', {
        'licitacion': licitacion,
        'url_externa': url_externa,
        'url_adjuntos': url_adjuntos,
        'url_preguntas': url_preguntas,
        'direccion_fallback': direccion_fallback,
        'estado': estado,
        'estado_label': estado_label,
        'seguimiento_activo': seguimiento is not None,
        'suscriptor_activo': suscriptor is not None,
        'documentos': documentos,
        'preguntas': preguntas,
        'hitos': hitos,
        'return_to': return_to,
        'return_solo_seguidas': query_return_to.get('solo_seguidas', [''])[0],
        'return_estado': query_return_to.get('estado', [''])[0],
    })


def _url_http(url):
    if not url:
        return ''
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in {'http', 'https'} or not parsed.netloc:
        return ''
    return url.strip()


def _es_retornos_local(url, request):
    return bool(
        url
        and url.startswith('/')
        and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()})
    )


def _es_solicitud_ajax(request):
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )


def _error_seguimiento(request, mensaje, estado):
    if _es_solicitud_ajax(request):
        return JsonResponse({'error': mensaje}, status=estado)
    if estado == 403:
        return HttpResponseForbidden(mensaje)
    if estado == 410:
        return HttpResponseGone(mensaje)
    return JsonResponse({'error': mensaje}, status=estado)


def seguimiento_licitacion_view(request, codigo):
    if request.method != 'POST':
        return JsonResponse({'error': 'Este endpoint requiere POST.'}, status=405)
    suscriptor = resolver_suscriptor(request)
    if not suscriptor:
        return _error_seguimiento(request, 'Debes iniciar sesión para seguir una licitación.', 403)

    licitacion = get_object_or_404(Licitacion, lic_codigo=codigo)
    accion = request.POST.get('accion')
    ahora = timezone.now()
    estado, _ = estado_licitacion(licitacion, ahora)
    if accion not in {'seguir', 'dejar'}:
        return JsonResponse({'error': 'Acción de seguimiento no válida.'}, status=400)
    if (
        accion == 'seguir'
        and estado == 'cerrada'
        and _instante_cierre(licitacion) <= ahora - timedelta(days=30)
    ):
        return _error_seguimiento(
            request,
            'El período de seguimiento de esta licitación ya finalizó.',
            410,
        )

    with transaction.atomic():
        if accion == 'seguir':
            seguimiento, _ = SeguimientoLicitacion.objects.select_for_update().get_or_create(
                usuario=suscriptor,
                licitacion=licitacion,
                defaults={'estado_actual': estado},
            )
            seguimiento.seguimiento_activo = True
            seguimiento.estado_actual = estado
            seguimiento.dejado_de_seguir_en = None
            seguimiento.cerrada_en = _instante_cierre(licitacion) if estado == 'cerrada' else None
            seguimiento.save()
        else:
            seguimiento = SeguimientoLicitacion.objects.select_for_update().filter(
                usuario=suscriptor,
                licitacion=licitacion,
            ).first()
            if seguimiento and seguimiento.seguimiento_activo:
                seguimiento.seguimiento_activo = False
                seguimiento.dejado_de_seguir_en = ahora
                seguimiento.save(update_fields=(
                    'seguimiento_activo',
                    'dejado_de_seguir_en',
                    'actualizado_en',
                ))

    if _es_solicitud_ajax(request):
        return JsonResponse({
            'seguimiento_activo': accion == 'seguir',
            'cantidad_seguidas': SeguimientoLicitacion.objects.filter(
                usuario=suscriptor,
                seguimiento_activo=True,
            ).count(),
        })

    return_to = request.POST.get('return_to', '')
    if _es_retornos_local(return_to, request):
        return redirect(return_to)
    return redirect(reverse('detalle_licitacion', args=(codigo,)))


def _sincronizar_seguimientos(suscriptor):
    """
    Sincroniza los estados de las licitaciones seguidas por el usuario.
    Se eliminó el borrado automático para preservar el historial.
    """
    ahora = timezone.now()
    with transaction.atomic():
        # Obtenemos solo los seguimientos activos para actualizar su estado
        seguimientos = (
            SeguimientoLicitacion.objects.select_for_update()
            .filter(usuario=suscriptor, seguimiento_activo=True)
            .select_related('licitacion')
        )
        
        notificaciones_a_crear = []
        
        for seguimiento in seguimientos:
            estado_nuevo, _ = estado_licitacion(seguimiento.licitacion, ahora)
            cambios = []
            
            # 1. Detectar cambio de estado y preparar notificación
            if estado_nuevo != seguimiento.estado_actual:
                estado_anterior = seguimiento.estado_actual
                notificaciones_a_crear.append(NotificacionLicitacion(
                    usuario=suscriptor,
                    licitacion=seguimiento.licitacion,
                    seguimiento=seguimiento,
                    estado_anterior=estado_anterior,
                    estado_nuevo=estado_nuevo,
                    mensaje=(
                        f"{seguimiento.licitacion.lic_nombre or seguimiento.licitacion.lic_codigo}: "
                        f"{ESTADOS_LICITACION[estado_anterior]} → {ESTADOS_LICITACION[estado_nuevo]}."
                    ),
                ))
                seguimiento.estado_actual = estado_nuevo
                cambios.append('estado_actual')
            
            # 2. Gestionar fecha de cierre si aplica
            if estado_nuevo == 'cerrada' and seguimiento.cerrada_en is None:
                seguimiento.cerrada_en = _instante_cierre(seguimiento.licitacion)
                cambios.append('cerrada_en')
            elif estado_nuevo != 'cerrada' and seguimiento.cerrada_en is not None:
                seguimiento.cerrada_en = None
                cambios.append('cerrada_en')
            
            # 3. Guardar solo si hubo cambios reales
            if cambios:
                seguimiento.save(update_fields=(*cambios, 'actualizado_en'))
        
        # Inserción masiva de notificaciones (más eficiente)
        if notificaciones_a_crear:
            NotificacionLicitacion.objects.bulk_create(notificaciones_a_crear)


def _instante_cierre(licitacion):
    if not licitacion.lic_fecha_cierre:
        return timezone.now()
    hora_cierre = licitacion.lic_hora_cierre or time.min
    fecha_hora = datetime.combine(licitacion.lic_fecha_cierre, hora_cierre)
    return timezone.make_aware(fecha_hora, timezone.get_current_timezone())


@ensure_csrf_cookie
def notificaciones_licitacion_view(request):
    if request.method not in ('GET', 'POST'):
        return JsonResponse({'error': 'Método no permitido.'}, status=405)
    suscriptor = resolver_suscriptor(request)
    if not suscriptor:
        return JsonResponse({'notifications': [], 'count': 0})

    _sincronizar_seguimientos(suscriptor)
    no_leidas = NotificacionLicitacion.objects.filter(usuario=suscriptor, leida=False)
    if request.method == 'POST':
        no_leidas.update(leida=True)
        return JsonResponse({'count': 0})

    items = no_leidas.select_related('licitacion')[:10]
    return JsonResponse({
        'count': no_leidas.count(),
        'notifications': [
            {
                'id': item.pk,
                'message': item.mensaje,
                'created_at': timezone.localtime(item.creado_en).strftime('%d-%m-%Y %H:%M'),
                'url': reverse('detalle_licitacion', args=(item.licitacion_id,)),
            }
            for item in items
        ],
    })
