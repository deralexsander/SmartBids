"""Dashboard para el DW actual. Consultas de lectura mediante el alias dw."""
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import FactOcCabecera, FactOrdenCompra


def dashboard_view(request):
    cabeceras = FactOcCabecera.objects.using("dw")
    compras = FactOrdenCompra.objects.using("dw")

    # Una fila de cabecera corresponde a una OC única.
    kpis = cabeceras.aggregate(
        monto=Sum("monto_total_clp"),
        ordenes=Count("codigo_oc"),
        proveedores=Count("proveedor_key", distinct=True),
        compradores=Count("comprador_key", distinct=True),
    )
    total_ordenes = kpis["ordenes"]

    # El resumen no permite reconstruir OCs únicas por producto.
    # Ranking por monto neto; se conserva el nombre de producto que usa el template.
    # Primer gráfico: grupos, no productos individuales.
    productos_mas_comprados = list(
        compras.values(grupo=F("producto_key__producto_grupo"))
        .annotate(monto_neto=Sum("monto_neto"), cantidad_items=Sum("cantidad_items"))
        .order_by("-monto_neto", "grupo")[:10]
    )
    for fila in productos_mas_comprados:
        fila["producto_key__producto_nombre"] = fila["grupo"] or "Sin grupo informado"

    competidores_qs = list(
        cabeceras.values("proveedor_key_id", "proveedor_key__proveedor_nombre")
        .annotate(
            cantidad_ordenes=Count("codigo_oc"),
            monto_adjudicado=Sum("monto_total_clp"),
        )
        .order_by("-cantidad_ordenes", "proveedor_key_id")[:5]
    )
    # Evita mezclar proveedores diferentes que tengan un mismo nombre.
    etiquetas = {
        r["proveedor_key_id"]: (
            f'{r["proveedor_key__proveedor_nombre"] or "Sin nombre"} '
            f'[{r["proveedor_key_id"]}]'
        )
        for r in competidores_qs
    }
    proveedores_competencia = []
    competidores = []
    for r in competidores_qs:
        nombre = etiquetas[r["proveedor_key_id"]]
        proveedores_competencia.append({
            "proveedor_key_id": r["proveedor_key_id"],
            "proveedor_key__proveedor_nombre": nombre,
            "cantidad_ordenes": r["cantidad_ordenes"],
        })
        competidores.append({
            "nombre": nombre,
            # Claves históricas del template: representan OCs, no eventos de adjudicación.
            "adjudicaciones": r["cantidad_ordenes"],
            "participacion": round(r["cantidad_ordenes"] / total_ordenes * 100, 2)
                if total_ordenes else 0,
            "monto_adjudicado": formatear_monto(r["monto_adjudicado"]),
        })

    evolucion_qs = (
        cabeceras.filter(proveedor_key_id__in=list(etiquetas))
        .values(
            "fecha_key__anio", "fecha_key__mes",
            "fecha_key__nombre_mes_corto", "proveedor_key_id",
        )
        .annotate(cantidad_ordenes=Count("codigo_oc"))
        .order_by("fecha_key__anio", "fecha_key__mes", "proveedor_key_id")
    )
    periodos = {}
    for r in evolucion_qs:
        anio, mes = r["fecha_key__anio"], r["fecha_key__mes"]
        periodo = f"{anio}-{mes:02d}"
        if periodo not in periodos:
            periodos[periodo] = {
                "periodo": f'{r["fecha_key__nombre_mes_corto"]} {anio}',
                **{nombre: 0 for nombre in etiquetas.values()},
            }
        periodos[periodo][etiquetas[r["proveedor_key_id"]]] = r["cantidad_ordenes"]
    evolucion_competidores = list(periodos.values())

    organismos_compradores = list(
        cabeceras.values("comprador_key_id", "comprador_key__comprador_organismo_nombre")
        .annotate(cantidad_ordenes=Count("codigo_oc"))
        .order_by("-cantidad_ordenes", "comprador_key_id")[:5]
    )

    context = {
        "monto_total_ordenes": formatear_monto(kpis["monto"]),
        "total_ordenes": total_ordenes,
        "proveedores_activos": kpis["proveedores"],
        "compradores_activos": kpis["compradores"],
        "productos_mas_comprados": productos_mas_comprados,
        "proveedores_competencia": proveedores_competencia,
        "competidores": competidores,
        "evolucion_competidores": evolucion_competidores,
        "organismos_compradores": organismos_compradores,
    }
    return render(request, "smartbids/dashboard.html", context)


def formatear_monto(monto):
    """CLP abreviado; MM significa millones en todos los casos."""
    monto = Decimal(0) if monto is None else Decimal(str(monto))
    if abs(monto) >= 1_000_000:
        return f"${monto / Decimal(1_000_000):,.0f} MM".replace(",", ".")
    if abs(monto) >= 1_000:
        return f"${monto / Decimal(1_000):,.0f} mil".replace(",", ".")
    return f"${monto:,.0f}".replace(",", ".")


@require_GET
def dashboard_desglose(request):
    """Desglose por monto neto; mismo alcance que el dashboard: datos cargados."""
    nivel = request.GET.get("nivel", "nivel1")
    if nivel not in {"nivel1", "producto"}:
        return JsonResponse({"error": "Nivel inválido."}, status=400)
    compras = FactOrdenCompra.objects.using("dw")
    if request.GET.get("grupo_nulo") == "1":
        grupo = None
    elif "grupo" in request.GET:
        grupo = request.GET["grupo"]
    else:
        return JsonResponse({"error": "Falta el grupo."}, status=400)
    compras = compras.filter(producto_key__producto_grupo=grupo)
    if nivel == "nivel1":
        filas = list(
            compras.values(valor=F("producto_key__producto_nivel1"))
            .annotate(monto_neto=Sum("monto_neto"))
            .order_by("-monto_neto", "valor")[:10]
        )
        for fila in filas:
            fila["nombre"] = fila["valor"] or "Sin nivel informado"
    else:
        if request.GET.get("nivel1_nulo") == "1":
            nivel1 = None
        elif "nivel1" in request.GET:
            nivel1 = request.GET["nivel1"]
        else:
            return JsonResponse({"error": "Falta el nivel 1."}, status=400)
        filas = list(
            compras.filter(producto_key__producto_nivel1=nivel1)
            .values(
                producto_id=F("producto_key_id"),
                codigo=F("producto_key__producto_codigo"),
                nombre=F("producto_key__producto_descripcion"),
            )
            .annotate(monto_neto=Sum("monto_neto"))
            .order_by("-monto_neto", "producto_id")[:10]
        )
    return JsonResponse({"nivel": nivel, "filas": filas})
