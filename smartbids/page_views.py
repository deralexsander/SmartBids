import csv
import json
from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from .licitacion_utils import (
    escribir_fila_csv,
    generar_excel_response,
    generar_excel_multitabla_response,
    resolver_suscriptor,
    obtener_catalogo_tipos_licitacion,
)
from .models.procurement import Licitacion
from .dashboard_views import (
    dashboard_kpis,
    dashboard_desglose,
    dashboard_competencia,
)


def home(request):
    return render(request, 'smartbids/home.html')

def login_view(request):
    return render(request, 'registro/ingreso.html')

def register_view(request):
    return render(request, 'registro/registro.html')

def accion_cuenta_view(request):
    mode = request.GET.get('mode', '')
    oob_code = request.GET.get('oobCode', '')
    return render(request, 'smartbids/accion_cuenta.html', {
        'mode': mode,
        'oob_code': oob_code,
    })

def perfil_view(request):
    tipos_procedimiento = obtener_catalogo_tipos_licitacion()
    return render(request, 'smartbids/perfil.html', {
        'tipos_procedimiento': tipos_procedimiento
    })

def mensajeria_view(request):
    return render(request, 'smartbids/mensajeria.html')

def administracion_general_view(request):
    suscriptor = resolver_suscriptor(request)
    if suscriptor and suscriptor.codigo_estado:
        rol = (suscriptor.codigo_estado.nombre_estado or '').strip().lower()
        es_admin = rol in ('admin', 'administrador') or suscriptor.codigo_estado.codigo_estado == 5
        if not es_admin:
            return redirect('mis_licitaciones')
    return render(request, 'smartbids/administracion_general.html')

def handler404_view(request, exception=None):
    return render(request, 'smartbids/404.html', status=404)

def informacion_view(request):
    return render(request, 'smartbids/informacion.html')

def dashboard_view(request):
    dias = _dias_dashboard(request.GET.get('dias'))
    fecha_inicio = timezone.localdate() - timedelta(days=dias)
    licitaciones = (
        Licitacion.objects.select_related('lic_codigo_ucom')
        .filter(lic_fecha_public__gte=fecha_inicio, lic_fecha_public__lte=timezone.localdate())
        .order_by('-lic_fecha_public')
    )
    return render(request, 'smartbids/dashboard.html', {
        'dias': dias,
        'licitaciones_periodo': licitaciones[:20],
        'total_periodo': licitaciones.count(),
    })


def _dias_dashboard(valor):
    try:
        dias = int(valor)
    except (TypeError, ValueError):
        return 90
    return dias if dias in {30, 90, 365} else 90


def exportar_dashboard_view(request):
    formato = (request.GET.get('formato') or request.GET.get('format') or 'xlsx').strip().lower()
    periodo_str = request.GET.get('periodo', '').strip() or request.GET.get('gran', 'historico')

    # Si se pide exportación legacy de licitaciones (parámetro 'dias' sin 'gran')
    if 'dias' in request.GET and 'gran' not in request.GET and 'periodo' not in request.GET:
        dias = _dias_dashboard(request.GET.get('dias'))
        fecha_inicio = timezone.localdate() - timedelta(days=dias)
        licitaciones = (
            Licitacion.objects.select_related('lic_codigo_ucom')
            .filter(lic_fecha_public__gte=fecha_inicio, lic_fecha_public__lte=timezone.localdate())
            .order_by('-lic_fecha_public')
        )
        encabezados = (
            'Código', 'Nombre', 'Tipo', 'Unidad de compra', 'Fecha publicación',
            'Fecha cierre', 'Presupuesto', 'Moneda', 'Enlace externo'
        )
        def obtener_filas_legacy():
            for licitacion in licitaciones:
                yield (
                    licitacion.lic_codigo,
                    licitacion.lic_nombre,
                    licitacion.lic_tipo_licitacion,
                    licitacion.lic_codigo_ucom.ucom_descripcion if licitacion.lic_codigo_ucom else '',
                    licitacion.lic_fecha_public,
                    licitacion.lic_fecha_cierre,
                    licitacion.lic_presupuesto,
                    licitacion.lic_moneda,
                    licitacion.lic_url,
                )
        if formato in {'excel', 'xlsx'}:
            return generar_excel_response('dashboard-licitaciones.xlsx', encabezados, obtener_filas_legacy())
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="dashboard-licitaciones.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(encabezados)
        for fila in obtener_filas_legacy():
            escribir_fila_csv(writer, fila)
        return response

    # Exportación oficial de las Tablas del Dashboard Analítico
    try:
        resp_kpi = dashboard_kpis(request)
        data_kpi = json.loads(resp_kpi.content) if resp_kpi.status_code == 200 else {}
    except Exception:
        data_kpi = {}

    try:
        req_prod = request.GET.copy()
        req_prod['tipo'] = 'ranking'
        req_prod_obj = type(request)(request.environ)
        req_prod_obj.GET = req_prod
        resp_prod = dashboard_desglose(req_prod_obj)
        data_prod = json.loads(resp_prod.content) if resp_prod.status_code == 200 else {}
    except Exception:
        data_prod = {}

    try:
        req_comp = request.GET.copy()
        req_comp['tipo'] = 'ranking'
        req_comp['por'] = 'proveedor'
        req_comp_obj = type(request)(request.environ)
        req_comp_obj.GET = req_comp
        resp_comp = dashboard_competencia(req_comp_obj)
        data_comp = json.loads(resp_comp.content) if resp_comp.status_code == 200 else {}
    except Exception:
        data_comp = {}

    try:
        req_compr = request.GET.copy()
        req_compr['tipo'] = 'ranking'
        req_compr['por'] = 'organismo'
        req_compr_obj = type(request)(request.environ)
        req_compr_obj.GET = req_compr
        resp_compr = dashboard_competencia(req_compr_obj)
        data_compr = json.loads(resp_compr.content) if resp_compr.status_code == 200 else {}
    except Exception:
        data_compr = {}

    filas_kpis = [
        ['Período analizado', data_kpi.get('etiqueta', periodo_str), 'Filtro temporal activo'],
        ['Monto total OCs (CLP)', f"${float(data_kpi.get('monto_total', 0) or 0):,.0f}", 'Monto total transado'],
        ['Ítems procesados', f"{int(data_kpi.get('lineas_total', 0) or 0):,}", 'Líneas de órdenes de compra'],
        ['Proveedores con OCs', f"{int(data_kpi.get('proveedores_unicos', 0) or 0):,}", 'Empresas adjudicadas'],
        ['Compradores con OCs', f"{int(data_kpi.get('compradores_unicos', 0) or 0):,}", 'Organismos públicos compradores'],
    ]

    filas_prod = []
    for idx, r in enumerate(data_prod.get('ranking', []), start=1):
        filas_prod.append([
            idx,
            r.get('nombre', 'Sin informar'),
            float(r.get('monto', 0) or 0),
            f"{r.get('participacion', 0)}%",
            int(r.get('items', 0) or 0)
        ])

    filas_comp = []
    for idx, r in enumerate(data_comp.get('ranking', []), start=1):
        filas_comp.append([
            idx,
            r.get('nombre', 'Sin informar'),
            float(r.get('monto', 0) or 0),
            f"{r.get('participacion', 0)}%",
            int(r.get('items', 0) or 0)
        ])

    filas_compr = []
    for idx, r in enumerate(data_compr.get('ranking', []), start=1):
        filas_compr.append([
            idx,
            r.get('nombre', 'Sin informar'),
            float(r.get('monto', 0) or 0),
            f"{r.get('participacion', 0)}%",
            r.get('proveedores', '--'),
            int(r.get('items', 0) or 0)
        ])

    tablas = {
        'Resumen KPIs': {
            'encabezados': ['Indicador', 'Valor', 'Detalle'],
            'filas': filas_kpis,
        },
        'Demanda Productos': {
            'encabezados': ['Posición', 'Producto / Grupo', 'Monto Neto (CLP)', 'Participación', 'Ítems Comprados'],
            'filas': filas_prod,
        },
        'Competencia Proveedores': {
            'encabezados': ['Posición', 'Proveedor', 'Monto Bruto (CLP)', 'Participación', 'Ítems'],
            'filas': filas_comp,
        },
        'Organismos Compradores': {
            'encabezados': ['Posición', 'Organismo Comprador', 'Monto Bruto (CLP)', 'Participación', 'Proveedores', 'Ítems'],
            'filas': filas_compr,
        },
    }

    if formato in {'excel', 'xlsx'}:
        return generar_excel_multitabla_response(f'dashboard-tablas-{periodo_str}.xlsx', tablas)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="dashboard-tablas-{periodo_str}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)

    for nombre_tabla, contenido in tablas.items():
        writer.writerow([f"=== {nombre_tabla.upper()} ==="])
        writer.writerow(contenido['encabezados'])
        for f in contenido['filas']:
            writer.writerow(f)
        writer.writerow([])
    return response
