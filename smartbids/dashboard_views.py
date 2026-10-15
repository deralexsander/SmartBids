from django.shortcuts import render
from django.db.models import Count, Sum

from .models import FactItemOrdenCompra, FactOrdenCompra

def dashboard_view(request):
    
    # KPIs principales del dashboard

    monto_total_ordenes = (
        FactOrdenCompra.objects
        .using('dw')
        .aggregate(
            total=Sum('orden_monto_total_clp')
        )['total']
    )
    monto_total_ordenes = formatear_monto(monto_total_ordenes)

    total_ordenes = (
        FactOrdenCompra.objects
        .using('dw')
        .values('orden_codigo')
        .distinct()
        .count()
    )

    proveedores_activos = (
        FactOrdenCompra.objects
        .using('dw')
        .values('proveedor_key')
        .distinct()
        .count()
    )

    compradores_activos = (
        FactOrdenCompra.objects
        .using('dw')
        .values('comprador_key')
        .distinct()
        .count()
    )
    
    # 1. Productos m├ís comprados
    productos_mas_comprados = (
        FactItemOrdenCompra.objects
        .using('dw')
        .values('producto_key__producto_nombre')
        .annotate(
            cantidad_ordenes=Count(
                'orden_codigo',
                distinct=True
            )
        )
        .order_by('-cantidad_ordenes')[:10]
    )

    # 2. Competencia (proveedores)
    proveedores_competencia = (
        FactOrdenCompra.objects
        .using('dw')
        .values(
            'proveedor_key__proveedor_nombre'
        )
        .annotate(
            cantidad_ordenes=Count(
                'orden_codigo',
                distinct=True
            )
        )
        .order_by('-cantidad_ordenes')[:5]
    )
    
    # Ranking de principales competidores
    competidores_qs = (
        FactOrdenCompra.objects
        .using('dw')
        .values(
            'proveedor_key__proveedor_nombre'
        )
        .annotate(
            adjudicaciones=Count(
                'orden_codigo',
                distinct=True
            ),
            monto_adjudicado=Sum(
                'orden_monto_total_clp'
            )
        )
        .order_by('-adjudicaciones')[:5]
    )
    
    total_adjudicaciones = (
        FactOrdenCompra.objects
        .using('dw')
        .values('orden_codigo')
        .distinct()
        .count()
    )
    
    competidores = []

    for competidor in competidores_qs:
        adjudicaciones = competidor['adjudicaciones']

        participacion = (
            (adjudicaciones / total_adjudicaciones) * 100
            if total_adjudicaciones > 0
            else 0
        )

        competidores.append({
            'nombre': competidor['proveedor_key__proveedor_nombre'],
            'adjudicaciones': adjudicaciones,
            'participacion': round(participacion, 2),
            'monto_adjudicado': formatear_monto(competidor['monto_adjudicado'] or 0),
        })
        
    top_competidores = [
        proveedor['proveedor_key__proveedor_nombre']
        for proveedor in proveedores_competencia
    ]
    
    evolucion_competidores_qs = (
        FactOrdenCompra.objects
        .using('dw')
        .filter(
            proveedor_key__proveedor_nombre__in=top_competidores
        )
        .values(
            'fecha_creacion_key__anio',
            'fecha_creacion_key__mes',
            'fecha_creacion_key__nombre_mes_corto',
            'proveedor_key__proveedor_nombre'
        )
        .annotate(
            cantidad_ordenes=Count(
                'orden_codigo',
                distinct=True
            )
        )
        .order_by(
            'fecha_creacion_key__anio',
            'fecha_creacion_key__mes'
        )
    )
        
    evolucion_competidores_data = {}

    for fila in evolucion_competidores_qs:

        anio = fila['fecha_creacion_key__anio']
        mes = fila['fecha_creacion_key__mes']
        nombre_mes = fila['fecha_creacion_key__nombre_mes_corto']
        proveedor = fila['proveedor_key__proveedor_nombre']
        cantidad = fila['cantidad_ordenes']

        periodo = f"{anio}-{mes:02d}"

        if periodo not in evolucion_competidores_data:
            evolucion_competidores_data[periodo] = {
                'periodo': f"{nombre_mes} {anio}",
            }

        evolucion_competidores_data[periodo][proveedor] = cantidad
        
        evolucion_competidores = list(
            evolucion_competidores_data.values()
        )
        
    # 3. Organismos Compradores
    organismos_compradores = (
        FactOrdenCompra.objects
        .using('dw')
        .values(
            'comprador_key__comprador_organismo_nombre'
        )
        .annotate(
            cantidad_ordenes=Count(
                'orden_codigo',
                distinct=True
            )
        )
        .order_by('-cantidad_ordenes')[:5]  
    )

    context = {
        'monto_total_ordenes': monto_total_ordenes,
        'total_ordenes': total_ordenes,
        'proveedores_activos': proveedores_activos,
        'compradores_activos': compradores_activos,
        'productos_mas_comprados': productos_mas_comprados,
        'proveedores_competencia': proveedores_competencia,
        'competidores': competidores,
        'evolucion_competidores': evolucion_competidores,
        'organismos_compradores': organismos_compradores,
    }

    return render(
        request,
        'smartbids/dashboard.html',
        context
    )

# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def formatear_monto(monto):
    if monto is None:
        return '$0'

    monto = float(monto)

    if monto >= 1_000_000_000:
        valor = monto / 1_000_000
        return f"${valor:,.0f} MM".replace(",", ".")

    if monto >= 1_000_000:
        valor = monto / 1_000_000
        return f"${valor:,.0f} M".replace(",", ".")

    if monto >= 1_000:
        valor = monto / 1_000
        return f"${valor:,.0f} mil".replace(",", ".")

    return f"${monto:,.0f}".replace(",", ".")


