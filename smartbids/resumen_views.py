import calendar
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db import connections
from django.db.models import Count, Max, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from .dashboard_views import formatear_monto
from .licitacion_utils import estado_licitacion, resolver_suscriptor
from .models import FactOrdenCompra
from .models.core import Preferencia
from .models.procurement import Licitacion, LicitacionesProductos
from .models.tracking import NotificacionLicitacion, SeguimientoLicitacion
from .tracking_views import _sincronizar_seguimientos


DIAS_SEMANA_ES = [
    'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'
]
MESES_ES = [
    '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]


def _formatear_fecha_es(fecha):
    dia_semana = DIAS_SEMANA_ES[fecha.weekday()]
    mes = MESES_ES[fecha.month]
    return f"{dia_semana}, {fecha.day} de {mes} de {fecha.year}"


def resumen_dia_view(request):
    suscriptor = resolver_suscriptor(request)
    if suscriptor:
        _sincronizar_seguimientos(suscriptor)

    hoy = timezone.localdate()
    ahora = timezone.now()
    fecha_formateada = _formatear_fecha_es(hoy)

    # 1. Nombre de usuario
    nombre_usuario = 'Suscriptor'
    if suscriptor:
        if suscriptor.sus_nombre1:
            nombre_usuario = f"{suscriptor.sus_nombre1} {suscriptor.sus_apellido1 or ''}".strip()
        elif suscriptor.sus_nombre_social:
            nombre_usuario = suscriptor.sus_nombre_social

    # 2. Preferencias del suscriptor y filtros de match
    preferencias = Preferencia.objects.filter(id_suscriptor=suscriptor).first() if suscriptor else None
    palabras = preferencias.pref_palabras_claves if preferencias and preferencias.pref_palabras_claves else []
    productos = preferencias.pref_productos if preferencias and preferencias.pref_productos else []
    tipos = [str(t).strip() for t in (preferencias.pref_tipo_licitacion or []) if str(t).strip()] if preferencias else []
    comunas = [str(c).strip() for c in (preferencias.pref_comunas or []) if str(c).strip()] if preferencias else []
    ucom_ids = [int(u) for u in (preferencias.pref_ucom or []) if str(u).strip().isdigit()] if preferencias else []
    tiene_palabras_perfil = bool(palabras or productos or tipos or comunas or ucom_ids)

    q_contenido = Q()
    if palabras:
        q_palabras = Q()
        for palabra in palabras:
            q_palabras |= (
                Q(lic_texto__icontains=palabra)
                | Q(lic_nombre__icontains=palabra)
                | Q(lic_descripcion__icontains=palabra)
            )
        q_contenido |= q_palabras

    if productos:
        codigos_completos = [p for p in productos if len(p) >= 8]
        prefijos = [p for p in productos if len(p) < 8]
        q_prod = Q()
        if codigos_completos:
            q_prod |= Q(codigo_producto__in=codigos_completos)
        for pref in prefijos:
            q_prod |= Q(codigo_producto__startswith=pref)
        subq_prod = LicitacionesProductos.objects.filter(q_prod).values('lic_codigo_id')
        q_contenido |= Q(lic_codigo__in=subq_prod)

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

    # Coincidencias de perfil
    if q_perfil:
        total_coincidencias = Licitacion.objects.filter(q_perfil).distinct().count()
    else:
        total_coincidencias = 0

    # Licitaciones seguidas
    seguidos_ids = set()
    total_seguidas = 0
    licitaciones_seguidas_preview = []
    if suscriptor:
        seguimientos_qs = SeguimientoLicitacion.objects.filter(
            usuario=suscriptor,
            seguimiento_activo=True,
        ).select_related('licitacion', 'licitacion__lic_codigo_ucom')
        total_seguidas = seguimientos_qs.count()
        seguidos_ids = set(seguimientos_qs.values_list('licitacion_id', flat=True))
        for seg in seguimientos_qs[:4]:
            lic = seg.licitacion
            lic.estado_proceso, lic.estado_proceso_label = estado_licitacion(lic, ahora)
            licitaciones_seguidas_preview.append(lic)

    # Cierres próximos: prioridad a licitaciones de tu perfil o seguidas; si no hay, activos del mercado
    plazo_tres_dias = hoy + timedelta(days=3)
    q_cierre_usuario = Q()
    if q_perfil:
        q_cierre_usuario |= q_perfil
    if seguidos_ids:
        q_cierre_usuario |= Q(lic_codigo__in=seguidos_ids)

    cierre_es_general = False
    if q_cierre_usuario:
        cierre_proximo_qs = (
            Licitacion.objects.filter(q_cierre_usuario)
            .filter(lic_fecha_cierre__gte=hoy, lic_fecha_cierre__lte=plazo_tres_dias)
            .select_related('lic_codigo_ucom')
            .order_by('lic_fecha_cierre')
            .distinct()
        )
        total_cierre_proximo = cierre_proximo_qs.count()
    else:
        cierre_proximo_qs = Licitacion.objects.none()
        total_cierre_proximo = 0

    # Si el usuario no tiene licitaciones propias con cierre en 72h, mostramos oportunidades activas del mercado
    if total_cierre_proximo == 0:
        cierre_proximo_qs = (
            Licitacion.objects
            .filter(lic_fecha_cierre__gte=hoy, lic_fecha_cierre__lte=plazo_tres_dias)
            .select_related('lic_codigo_ucom')
            .order_by('lic_fecha_cierre')
            .distinct()
        )
        total_cierre_proximo = cierre_proximo_qs.count()
        cierre_es_general = True

    licitaciones_urgentes = list(cierre_proximo_qs[:4])
    for lic in licitaciones_urgentes:
        lic.estado_proceso, lic.estado_proceso_label = estado_licitacion(lic, ahora)
        lic.es_cierre_proximo = True

    # Oportunidades del día: solo las que hacen match con el perfil (al igual que en Mis Licitaciones)
    if q_perfil:
        destacadas_qs = (
            Licitacion.objects.filter(q_perfil)
            .select_related('lic_codigo_ucom')
            .order_by('-lic_fecha_public')
            .distinct()[:6]
        )
    else:
        destacadas_qs = Licitacion.objects.none()

    licitaciones_destacadas = list(destacadas_qs)
    for lic in licitaciones_destacadas:
        lic.estado_proceso, lic.estado_proceso_label = estado_licitacion(lic, ahora)

    # 3. Métricas y Destacados del Dashboard DW
    def _obtener_dashboard_kpis_resumen():
        try:
            compras = FactOrdenCompra.objects.using("dw")
            r = compras.aggregate(
                monto=Sum("monto_bruto"),
                items=Sum("cantidad_items"),
                proveedores=Count("proveedor_key_id", distinct=True),
                compradores=Count("comprador_key_id", distinct=True),
                ordenes=Max("total_oc_procesadas"),
            )
            return {
                'monto_fmt': formatear_monto(r['monto']),
                'items_count': int(r['items'] or 0),
                'proveedores_count': int(r['proveedores'] or 0),
                'compradores_count': int(r['compradores'] or 0),
                'ordenes_count': int(r['ordenes'] or 0),
            }
        except Exception:
            return {
                'monto_fmt': '$0',
                'items_count': 0,
                'proveedores_count': 0,
                'compradores_count': 0,
                'ordenes_count': 0,
            }

    dashboard_metricas = cache.get_or_set('resumen_dia_dw_kpis', _obtener_dashboard_kpis_resumen, 1800)

    # Top producto y comprador para destacar
    def _obtener_dashboard_top_destacados():
        top_prod = None
        top_comprador = None
        try:
            with connections["dw"].cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(p.producto_grupo, 'Sin informar') AS nombre,
                           SUM(f.monto_neto) AS monto
                    FROM dw.fact_orden_compra f
                    JOIN dw.dim_producto p ON p.producto_key = f.producto_key
                    GROUP BY p.producto_grupo
                    ORDER BY monto DESC NULLS LAST
                    LIMIT 1
                """)
                row_prod = cursor.fetchone()
                if row_prod:
                    top_prod = {'nombre': row_prod[0], 'monto_fmt': formatear_monto(row_prod[1])}

                cursor.execute("""
                    SELECT COALESCE(c.organismo_nombre, 'Sin informar') AS nombre,
                           SUM(f.monto_bruto) AS monto
                    FROM dw.fact_orden_compra f
                    JOIN dw.dim_comprador c ON c.comprador_key = f.comprador_key
                    GROUP BY c.organismo_nombre
                    ORDER BY monto DESC NULLS LAST
                    LIMIT 1
                """)
                row_compr = cursor.fetchone()
                if row_compr:
                    top_comprador = {'nombre': row_compr[0], 'monto_fmt': formatear_monto(row_compr[1])}
        except Exception:
            pass
        return {'top_producto': top_prod, 'top_comprador': top_comprador}

    destacados_mercado = cache.get_or_set('resumen_dia_dw_destacados', _obtener_dashboard_top_destacados, 1800)

    # 4. Notificaciones y Alertas
    notificaciones_recientes = []
    total_no_leidas = 0
    if suscriptor:
        notif_qs = NotificacionLicitacion.objects.filter(
            usuario=suscriptor
        ).select_related('licitacion').order_by('-creado_en')
        total_no_leidas = notif_qs.filter(leida=False).count()
        notificaciones_recientes = list(notif_qs[:5])

    context = {
        'nombre_usuario': nombre_usuario,
        'fecha_hoy': fecha_formateada,
        'suscriptor': suscriptor,
        'tiene_palabras_perfil': tiene_palabras_perfil,
        'total_coincidencias': total_coincidencias,
        'total_seguidas': total_seguidas,
        'total_cierre_proximo': total_cierre_proximo,
        'cierre_es_general': cierre_es_general,
        'seguidos_ids': seguidos_ids,
        'licitaciones_destacadas': licitaciones_destacadas,
        'licitaciones_seguidas_preview': licitaciones_seguidas_preview,
        'licitaciones_urgentes': licitaciones_urgentes,
        'dashboard_metricas': dashboard_metricas,
        'top_producto': destacados_mercado.get('top_producto'),
        'top_comprador': destacados_mercado.get('top_comprador'),
        'notificaciones_recientes': notificaciones_recientes,
        'total_no_leidas': total_no_leidas,
    }

    return render(request, 'smartbids/resumen_dia.html', context)
