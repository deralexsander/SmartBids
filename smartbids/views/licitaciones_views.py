import csv
from datetime import date, datetime, timedelta

from django.core.cache import cache
from django.db.models import Count, Q
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from smartbids.models.procurement import Licitacion, LicitacionesProductos
from smartbids.models.core import Preferencia, Suscriptor, SeguimientoLicitacion
from smartbids.utils.licitacion_utils import (
    escribir_fila_csv,
    estado_licitacion,
    estado_qs,
    generar_excel_response,
    resolver_suscriptor,
    obtener_catalogo_tipos_licitacion,
)


def filtrar_licitaciones(request, suscriptor):
    qs = (
        Licitacion.objects
        .select_related('lic_codigo_ucom')
        .all()
        .order_by('-lic_fecha_public')
    )
    preferencias = Preferencia.objects.filter(id_suscriptor=suscriptor).first() if suscriptor else None

    comunas = [str(value).strip() for value in (preferencias.pref_comunas or []) if str(value).strip()] if preferencias else []
    tipos = [str(value).strip() for value in (preferencias.pref_tipo_licitacion or []) if str(value).strip()] if preferencias else []
    ucom_ids = [int(value) for value in (preferencias.pref_ucom or []) if str(value).strip().isdigit()] if preferencias else []
    palabras = [str(value).strip() for value in (preferencias.pref_palabras_claves or []) if str(value).strip()] if preferencias else []
    palabras_norm = [str(value).strip() for value in (preferencias.pref_palabras_claves_norm or []) if str(value).strip()] if preferencias else []
    productos = [str(value).strip() for value in (preferencias.pref_productos or []) if str(value).strip()] if preferencias else []

    tiene_filtros_perfil = bool(comunas or tipos or ucom_ids or palabras or palabras_norm or productos)
    tab = request.GET.get('tab', '').strip().lower()
    solo_seguidas = request.GET.get('solo_seguidas') == '1'
    solo_claves = (tab == 'claves' or request.GET.get('solo_claves') == '1') and not solo_seguidas

    q_contenido = Q()
    if palabras or palabras_norm:
        q_palabras = Q()
        for palabra in palabras:
            q_palabras |= Q(lic_texto__icontains=palabra) | Q(lic_nombre__icontains=palabra) | Q(lic_descripcion__icontains=palabra)
        if palabras_norm:
            q_palabras |= Q(lic_palabras_claves_norm__overlap=palabras_norm)
        q_contenido |= q_palabras

    if productos:
        codigos_completos = [p for p in productos if len(p) >= 8]
        prefijos = [p for p in productos if len(p) < 8]
        q_prod = Q()
        if codigos_completos:
            q_prod |= Q(codigo_producto__in=codigos_completos)
        for pref in prefijos:
            q_prod |= Q(codigo_producto__startswith=pref)
        subq_productos = LicitacionesProductos.objects.filter(q_prod).values('lic_codigo_id')
        q_contenido |= Q(lic_codigo__in=subq_productos)

    # El tipo de procedimiento, comunas y unidades de compra actúan como filtros restrictivos (AND / Intersección)
    condiciones_perfil = []
    if q_contenido:
        condiciones_perfil.append(q_contenido)
    if comunas:
        condiciones_perfil.append(Q(lic_codigo_ucom__ucom_codigo_comuna__in=comunas))
    if ucom_ids:
        condiciones_perfil.append(
            Q(lic_codigo_ucom_id__in=ucom_ids) | Q(lic_codigo_ucom__ucom_codigo_organismo__in=ucom_ids)
        )
    if tipos:
        condiciones_perfil.append(Q(lic_tipo_licitacion__in=tipos))

    if condiciones_perfil:
        q_perfil = condiciones_perfil[0]
        for cond in condiciones_perfil[1:]:
            q_perfil &= cond
    else:
        q_perfil = Q()

    if q_perfil:
        match_perfil = Licitacion.objects.filter(q_perfil).distinct().count()
    else:
        match_perfil = 0

    request._q_perfil = q_perfil

    if solo_seguidas:
        if suscriptor:
            from smartbids.models.core import SeguimientoLicitacion
            codigos_seguidos = SeguimientoLicitacion.objects.filter(
                usuario=suscriptor,
                seguimiento_activo=True,
            ).values_list('licitacion_id', flat=True)
            qs = qs.filter(lic_codigo__in=codigos_seguidos)
        else:
            qs = qs.none()
    elif solo_claves:
        # Pestaña "Con palabras clave": filtrar solo por el perfil configurado
        if q_perfil:
            qs = qs.filter(q_perfil).distinct()
        else:
            qs = qs.none()
    else:
        # Pestaña "Todas": se muestran todas las licitaciones sin el filtro de palabras clave
        pass

    termino = request.GET.get('q', '').strip()
    if termino:
        qs = qs.filter(
            Q(lic_codigo__icontains=termino)
            | Q(lic_nombre__icontains=termino)
            | Q(lic_descripcion__icontains=termino)
        )

    tipo = request.GET.get('tipo', '').strip()
    if tipo:
        qs = qs.filter(lic_tipo_licitacion=tipo)

    estado = request.GET.get('estado', '').strip()
    if estado in {'publicada', 'preguntas', 'ofertas', 'cerrada'}:
        qs = qs.filter(estado_qs(estado))

    return qs, match_perfil


def _calcular_cierre_proximo(lic, hoy, plazo_tres_dias):
    fecha = getattr(lic, 'lic_fecha_cierre', None)
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    if isinstance(fecha, date):
        return hoy <= fecha <= plazo_tres_dias
    return bool(getattr(lic, 'es_cierre_proximo', False))


def mis_licitaciones_view(request):
    suscriptor = resolver_suscriptor(request)
    if suscriptor:
        from .tracking_views import _sincronizar_seguimientos
        _sincronizar_seguimientos(suscriptor)
    qs, match_perfil = filtrar_licitaciones(request, suscriptor)

    hoy = timezone.localdate()
    plazo_tres_dias = hoy + timedelta(days=3)

    stats = qs.aggregate(
        cierre_proximo=Count('lic_codigo', filter=Q(lic_fecha_cierre__gte=hoy, lic_fecha_cierre__lte=plazo_tres_dias)),
        convenio_marco=Count('lic_codigo', filter=Q(lic_tipo_licitacion='CM'))
    )
    cierre_proximo = stats['cierre_proximo'] or 0
    convenio_marco = stats['convenio_marco'] or 0

    total_licitaciones = cache.get_or_set('total_licitaciones_count', Licitacion.objects.count, 3600)

    seguidos = set()
    if suscriptor:
        from smartbids.models.core import SeguimientoLicitacion
        seguidos = set(
            SeguimientoLicitacion.objects.filter(
                usuario=suscriptor,
                seguimiento_activo=True,
            ).values_list('licitacion_id', flat=True)
        )

    tipos = cache.get_or_set(
        'licitacion_tipos_list',
        lambda: list(
            Licitacion.objects.exclude(lic_tipo_licitacion__isnull=True)
            .exclude(lic_tipo_licitacion='')
            .values_list('lic_tipo_licitacion', flat=True)
            .distinct()
            .order_by('lic_tipo_licitacion')
        ),
        86400
    )

    tab = request.GET.get('tab', '').strip().lower()
    solo_seguidas = request.GET.get('solo_seguidas') == '1'
    solo_claves = (tab == 'claves' or request.GET.get('solo_claves') == '1') and not solo_seguidas
    tab_activa = 'seguidas' if solo_seguidas else ('claves' if solo_claves else 'todas')

    pagina_actual = request.GET.get('page', '1')
    es_primera_pagina = str(pagina_actual).strip() in ('1', '', 'None')

    # Separar las licitaciones de Match con Perfil de los Procesos de Compra Disponibles en la vista principal
    q_perfil = getattr(request, '_q_perfil', None)
    licitaciones_perfil = []
    tiene_filtro_manual = bool(request.GET.get('q') or request.GET.get('tipo') or request.GET.get('estado'))
    if q_perfil and match_perfil > 0 and not solo_seguidas and not tiene_filtro_manual:
        try:
            qs_perfil = (
                Licitacion.objects
                .select_related('lic_codigo_ucom')
                .filter(q_perfil)
                .distinct()
                .order_by('-lic_fecha_public')
            )
            # Optimización de rendimiento: cargar en la primera página un bloque de hasta 10 oportunidades
            if es_primera_pagina:
                licitaciones_perfil = list(qs_perfil[:10])
                for lic in licitaciones_perfil:
                    lic.estado_proceso, lic.estado_proceso_label = estado_licitacion(lic)
                    lic.es_cierre_proximo = _calcular_cierre_proximo(lic, hoy, plazo_tres_dias)

            # Excluir de Procesos Disponibles para que queden estrictamente separados
            codigos_perfil = [l.lic_codigo for l in licitaciones_perfil] if es_primera_pagina else list(qs_perfil.values_list('lic_codigo', flat=True)[:10])
            qs = qs.exclude(lic_codigo__in=codigos_perfil)
        except Exception:
            licitaciones_perfil = []

    # Optimización de carga: 10 procesos disponibles por página (reduce la sobrecarga del DOM y tiempo de render)
    paginator = Paginator(qs, 10)
    licitaciones = paginator.get_page(pagina_actual)
    for licitacion in licitaciones:
        licitacion.estado_proceso, licitacion.estado_proceso_label = estado_licitacion(licitacion)
        licitacion.es_cierre_proximo = _calcular_cierre_proximo(licitacion, hoy, plazo_tres_dias)

    export_params = request.GET.copy()
    if 'page' in export_params:
        del export_params['page']
    export_query = f"?{export_params.urlencode()}" if export_params else ""

    preferencias = Preferencia.objects.filter(id_suscriptor=suscriptor).first() if suscriptor else None
    tiene_palabras_perfil = bool(
        preferencias and (
            preferencias.pref_palabras_claves
            or preferencias.pref_productos
            or preferencias.pref_tipo_licitacion
            or preferencias.pref_comunas
            or preferencias.pref_ucom
        )
    ) if suscriptor else False

    return render(request, 'smartbids/Mis_licitaciones.html', {
        'licitaciones': licitaciones,
        'licitaciones_perfil': licitaciones_perfil,
        'total_licitaciones': total_licitaciones,
        'match_perfil': match_perfil,
        'cierre_proximo': cierre_proximo,
        'convenio_marco': convenio_marco,
        'seguidos': seguidos,
        'cantidad_seguidas': len(seguidos),
        'tipos_licitacion': tipos,
        'tipos_procedimiento': obtener_catalogo_tipos_licitacion(),
        'estados': (
            ('publicada', 'Publicada'),
            ('preguntas', 'Período de preguntas'),
            ('ofertas', 'Recepción de ofertas'),
            ('cerrada', 'Cerrada'),
        ),
        'estado_licitacion': estado_licitacion,
        'suscriptor_activo': suscriptor is not None,
        'solo_seguidas': solo_seguidas,
        'solo_claves': solo_claves,
        'tab_activa': tab_activa,
        'tiene_palabras_perfil': tiene_palabras_perfil,
        'export_query': export_query,
    })


def exportar_licitaciones_view(request):
    suscriptor = resolver_suscriptor(request)
    licitaciones, _ = filtrar_licitaciones(request, suscriptor)
    formato = (request.GET.get('formato') or request.GET.get('format') or 'csv').strip().lower()

    encabezados = (
        'Código', 'Nombre', 'Descripción', 'Estado', 'Tipo', 'Unidad de compra',
        'Fecha publicación', 'Fecha cierre', 'Presupuesto', 'Moneda', 'Enlace externo'
    )

    def obtener_filas():
        for licitacion in licitaciones:
            yield (
                licitacion.lic_codigo,
                licitacion.lic_nombre,
                licitacion.lic_descripcion,
                estado_licitacion(licitacion)[1],
                licitacion.lic_tipo_licitacion,
                licitacion.lic_codigo_ucom.ucom_descripcion if licitacion.lic_codigo_ucom else '',
                licitacion.lic_fecha_public,
                licitacion.lic_fecha_cierre,
                licitacion.lic_presupuesto,
                licitacion.lic_moneda,
                licitacion.lic_url,
            )

    if formato in {'excel', 'xlsx'}:
        return generar_excel_response('licitaciones-smartbids.xlsx', encabezados, obtener_filas())

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="licitaciones-smartbids.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(encabezados)
    for fila in obtener_filas():
        escribir_fila_csv(writer, fila)
    return response
