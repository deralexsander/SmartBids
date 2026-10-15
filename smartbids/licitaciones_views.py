import csv
from datetime import date, timedelta

from django.db.models import Q
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from .models.procurement import Licitacion, LicitacionesProductos
from .models.core import Preferencia, Suscriptor
from .licitacion_utils import estado_licitacion, estado_qs, escribir_fila_csv, resolver_suscriptor


def filtrar_licitaciones(request, suscriptor):
    qs = Licitacion.objects.select_related('lic_codigo_ucom').all().order_by('-lic_fecha_public')
    preferencias = Preferencia.objects.filter(id_suscriptor=suscriptor).first() if suscriptor else None
    match_perfil = 0

    solo_seguidas = request.GET.get('solo_seguidas') == '1'
    if solo_seguidas:
        if suscriptor:
            from .models.tracking import SeguimientoLicitacion
            codigos_seguidos = SeguimientoLicitacion.objects.filter(
                usuario=suscriptor,
                seguimiento_activo=True,
            ).values_list('licitacion_id', flat=True)
            qs = qs.filter(lic_codigo__in=codigos_seguidos)
        else:
            qs = qs.none()
    elif preferencias:
        comunas = [str(value).strip() for value in (preferencias.pref_comunas or []) if str(value).strip()]
        tipos = [str(value).strip() for value in (preferencias.pref_tipo_licitacion or []) if str(value).strip()]
        ucom_ids = [int(value) for value in (preferencias.pref_ucom or []) if str(value).strip().isdigit()]
        palabras = [str(value).strip() for value in (preferencias.pref_palabras_claves or []) if str(value).strip()]
        productos = [str(value).strip() for value in (preferencias.pref_productos or []) if str(value).strip()]

        if comunas or tipos or ucom_ids or palabras or productos:
            filtros_estrictos = Q()
            if tipos:
                filtros_estrictos &= Q(lic_tipo_licitacion__in=tipos)
            if ucom_ids:
                filtros_estrictos &= Q(lic_codigo_ucom_id__in=ucom_ids)
            if comunas:
                filtros_estrictos &= Q(lic_codigo_ucom__ucom_codigo_comuna__in=comunas)
            if palabras:
                q_palabras = Q()
                for palabra in palabras:
                    q_palabras |= Q(lic_nombre__icontains=palabra) | Q(lic_descripcion__icontains=palabra)
                filtros_estrictos &= q_palabras
            if productos:
                codigos_licitacion = LicitacionesProductos.objects.filter(
                    codigo_producto__in=productos
                ).values_list('lic_codigo_id', flat=True)
                q_productos = Q(lic_codigo__in=codigos_licitacion)
                for producto in productos:
                    q_productos |= Q(lic_codigos_producto__icontains=producto)
                filtros_estrictos &= q_productos

            coincidencias = qs.filter(filtros_estrictos).distinct()
            if coincidencias.exists():
                qs = coincidencias
            else:
                filtros_flexibles = Q()
                if productos:
                    codigos_licitacion = LicitacionesProductos.objects.filter(
                        codigo_producto__in=productos
                    ).values_list('lic_codigo_id', flat=True)
                    q_productos = Q(lic_codigo__in=codigos_licitacion)
                    for producto in productos:
                        q_productos |= Q(lic_codigos_producto__icontains=producto)
                    filtros_flexibles |= q_productos
                if palabras:
                    q_palabras = Q()
                    for palabra in palabras:
                        q_palabras |= Q(lic_nombre__icontains=palabra) | Q(lic_descripcion__icontains=palabra)
                    filtros_flexibles |= q_palabras
                if ucom_ids:
                    filtros_flexibles |= Q(lic_codigo_ucom_id__in=ucom_ids)
                if comunas:
                    filtros_flexibles |= Q(lic_codigo_ucom__ucom_codigo_comuna__in=comunas)
                if tipos:
                    filtros_flexibles |= Q(lic_tipo_licitacion__in=tipos)
                qs = qs.filter(filtros_flexibles).distinct()
            match_perfil = qs.count()

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


def mis_licitaciones_view(request):
    suscriptor = resolver_suscriptor(request)
    if suscriptor:
        from .tracking_views import _sincronizar_seguimientos
        _sincronizar_seguimientos(suscriptor)
    qs, match_perfil = filtrar_licitaciones(request, suscriptor)

    hoy = date.today()
    plazo_tres_dias = hoy + timedelta(days=3)
    cierre_proximo = qs.filter(
        lic_fecha_cierre__gte=hoy,
        lic_fecha_cierre__lte=plazo_tres_dias,
    ).count()
    convenio_marco = qs.filter(lic_tipo_licitacion='CM').count()
    total_licitaciones = Licitacion.objects.count()

    seguidos = set()
    if suscriptor:
        from .models.tracking import SeguimientoLicitacion
        seguidos = set(
            SeguimientoLicitacion.objects.filter(
                usuario=suscriptor,
                seguimiento_activo=True,
            ).values_list('licitacion_id', flat=True)
        )

    tipos = list(
        Licitacion.objects.exclude(lic_tipo_licitacion__isnull=True)
        .exclude(lic_tipo_licitacion='')
        .values_list('lic_tipo_licitacion', flat=True)
        .distinct()
        .order_by('lic_tipo_licitacion')
    )
    paginator = Paginator(qs, 20)
    licitaciones = paginator.get_page(request.GET.get('page'))
    for licitacion in licitaciones:
        licitacion.estado_proceso, licitacion.estado_proceso_label = estado_licitacion(licitacion)
    return render(request, 'smartbids/Mis_licitaciones.html', {
        'licitaciones': licitaciones,
        'total_licitaciones': total_licitaciones,
        'match_perfil': match_perfil,
        'cierre_proximo': cierre_proximo,
        'convenio_marco': convenio_marco,
        'seguidos': seguidos,
        'cantidad_seguidas': len(seguidos),
        'tipos_licitacion': tipos,
        'estados': (
            ('publicada', 'Publicada'),
            ('preguntas', 'Período de preguntas'),
            ('ofertas', 'Recepción de ofertas'),
            ('cerrada', 'Cerrada'),
        ),
        'estado_licitacion': estado_licitacion,
        'suscriptor_activo': suscriptor is not None,
        'solo_seguidas': request.GET.get('solo_seguidas') == '1',
    })


def exportar_licitaciones_view(request):
    suscriptor = resolver_suscriptor(request)
    licitaciones, _ = filtrar_licitaciones(request, suscriptor)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="licitaciones-smartbids.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(('Código', 'Nombre', 'Descripción', 'Estado', 'Tipo', 'Unidad de compra',
                     'Fecha publicación', 'Fecha cierre', 'Presupuesto', 'Moneda', 'Enlace externo'))
    for licitacion in licitaciones:
        escribir_fila_csv(writer, (
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
        ))
    return response
