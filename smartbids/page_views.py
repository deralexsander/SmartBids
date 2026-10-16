import csv
from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from .licitacion_utils import escribir_fila_csv, generar_excel_response, resolver_suscriptor
from .models.procurement import Licitacion


def home(request):
    return render(request, 'smartbids/home.html')

def login_view(request):
    return render(request, 'registro/ingreso.html')

def register_view(request):
    return render(request, 'registro/registro.html')

def perfil_view(request):
    return render(request, 'smartbids/perfil.html')

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
    dias = _dias_dashboard(request.GET.get('dias'))
    fecha_inicio = timezone.localdate() - timedelta(days=dias)
    licitaciones = (
        Licitacion.objects.select_related('lic_codigo_ucom')
        .filter(lic_fecha_public__gte=fecha_inicio, lic_fecha_public__lte=timezone.localdate())
        .order_by('-lic_fecha_public')
    )
    formato = (request.GET.get('formato') or request.GET.get('format') or 'csv').strip().lower()

    encabezados = (
        'Código', 'Nombre', 'Tipo', 'Unidad de compra', 'Fecha publicación',
        'Fecha cierre', 'Presupuesto', 'Moneda', 'Enlace externo'
    )

    def obtener_filas():
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
        return generar_excel_response('dashboard-smartbids.xlsx', encabezados, obtener_filas())

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="dashboard-smartbids.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(encabezados)
    for fila in obtener_filas():
        escribir_fila_csv(writer, fila)
    return response
