"""Dashboard SmartBids: una única tabla de hechos dw.fact_orden_compra.

El grano es fecha/proveedor/comprador/tipo/producto. Por ello, los conteos
cantidad_ordenes_compra NO son aditivos entre productos. La actividad por
proveedor/organismo se presenta mediante cantidad_items y monto_bruto.
"""
from decimal import Decimal

from django.db.models import Count, F, Max, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import FactOrdenCompra


def formatear_monto(monto):
    """CLP abreviado; MM significa millones."""
    monto = Decimal(0) if monto is None else Decimal(str(monto))
    if abs(monto) >= 1_000_000:
        return f"${monto / Decimal(1_000_000):,.0f} MM".replace(",", ".")
    if abs(monto) >= 1_000:
        return f"${monto / Decimal(1_000):,.0f} mil".replace(",", ".")
    return f"${monto:,.0f}".replace(",", ".")


def dashboard_view(request):
    compras = FactOrdenCompra.objects.using("dw")

    # MAX, nunca SUM: ambos KPI globales se repiten por cada fila de la fact.
    kpis = compras.aggregate(
        monto=Max("monto_total_procesado_clp"),
        ordenes=Max("total_oc_procesadas"),
        proveedores=Count("proveedor_key_id", distinct=True),
        compradores=Count("comprador_key_id", distinct=True),
    )
    total_ordenes = kpis["ordenes"] or 0

    # Ranking y drill-down por monto neto (consistente entre ambos gráficos).
    productos_mas_comprados = list(
        compras.values(grupo=F("producto_key__producto_grupo"))
        .annotate(monto_neto=Sum("monto_neto"), cantidad_items=Sum("cantidad_items"))
        .order_by("-monto_neto", "grupo")[:10]
    )
    for fila in productos_mas_comprados:
        fila["producto_key__producto_nombre"] = fila["grupo"] or "Sin grupo informado"

    # Se usa monto y cantidad de ítems: NO COUNT DISTINCT de OC (no hay codigo_oc
    # en la fact agregada), ni SUM(cantidad_ordenes_compra) entre productos.
    competidores_qs = list(
        compras.values("proveedor_key_id", "proveedor_key__proveedor_nombre")
        .annotate(
            cantidad_items=Sum("cantidad_items"),
            monto_compras=Sum("monto_bruto"),
        )
        .order_by("-monto_compras", "proveedor_key_id")[:5]
    )
    etiquetas = {
        r["proveedor_key_id"]: (
            f'{r["proveedor_key__proveedor_nombre"] or "Sin nombre"} '
            f'[{r["proveedor_key_id"]}]'
        )
        for r in competidores_qs
    }
    monto_global = kpis["monto"] or Decimal(0)
    proveedores_competencia = []
    competidores = []
    for r in competidores_qs:
        nombre = etiquetas[r["proveedor_key_id"]]
        proveedores_competencia.append({
            "proveedor_key_id": r["proveedor_key_id"],
            "proveedor_key__proveedor_nombre": nombre,
            "cantidad_items": r["cantidad_items"],
            "monto_compras": r["monto_compras"],
        })
        competidores.append({
            "nombre": nombre,
            "cantidad_items": r["cantidad_items"],
            "participacion": round(float(r["monto_compras"] / monto_global * 100), 2)
                if monto_global else 0,
            "monto_compras": formatear_monto(r["monto_compras"]),
        })

    # Evolución monetaria (CLP), NO cantidad de OC únicas.
    evolucion_qs = (
        compras.filter(proveedor_key_id__in=list(etiquetas))
        .values("fecha_key__anio", "fecha_key__mes",
                "fecha_key__nombre_mes_corto", "proveedor_key_id")
        .annotate(monto_compras=Sum("monto_bruto"))
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
        # Chart.js y json_script aceptan float, no Decimal puro.
        periodos[periodo][etiquetas[r["proveedor_key_id"]]] = float(r["monto_compras"])
    evolucion_competidores = list(periodos.values())

    organismos_compradores = list(
        compras.values("comprador_key_id", "comprador_key__comprador_organismo_nombre")
        .annotate(cantidad_items=Sum("cantidad_items"), monto_compras=Sum("monto_bruto"))
        .order_by("-monto_compras", "comprador_key_id")[:5]
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


@require_GET
def dashboard_desglose(request):
    """Drill-down grupo → nivel 1 → producto, por monto neto de ítems."""
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

    # JsonResponse no serializa Decimal de forma universalmente consistente para gráficos.
    for fila in filas:
        if fila["monto_neto"] is not None:
            fila["monto_neto"] = float(fila["monto_neto"])
    return JsonResponse({"nivel": nivel, "filas": filas})


@require_GET
def dashboard_competencia(request):
    """
    Análisis de competencia sobre dw.fact_orden_compra.

    Operaciones:
      - tipo=opciones: grupos, regiones y organismos disponibles.
      - tipo=productos: productos filtrados por grupo y búsqueda.
      - tipo=ranking: ranking por proveedor, producto u organismo.

    La participación corresponde al monto del segmento filtrado.
    """

    tipo = request.GET.get("tipo", "ranking")
    compras = FactOrdenCompra.objects.using("dw")

    # ---------------------------------------------------------
    # 1. OPCIONES GENERALES PARA LOS FILTROS
    # ---------------------------------------------------------

    if tipo == "opciones":
        grupos = list(
            compras.order_by()
            .values_list(
                "producto_key__producto_grupo",
                flat=True,
            )
            .distinct()
        )

        regiones = list(
            compras.order_by()
            .values_list(
                "comprador_key__comprador_region",
                flat=True,
            )
            .distinct()
        )

        organismos = list(
            compras.order_by()
            .values(
                "comprador_key_id",
                "comprador_key__comprador_organismo_nombre",
            )
            .distinct()
        )

        return JsonResponse({
            "grupos": sorted(
                [g for g in grupos if g],
                key=str.casefold,
            ),
            "regiones": sorted(
                [r for r in regiones if r],
                key=str.casefold,
            ),
            "organismos": sorted(
                [
                    {
                        "id": o["comprador_key_id"],
                        "nombre": (
                            o["comprador_key__comprador_organismo_nombre"]
                            or "Sin nombre"
                        ),
                    }
                    for o in organismos
                ],
                key=lambda o: (o["nombre"].casefold(), o["id"]),
            ),
        })

    # ---------------------------------------------------------
    # 2. FILTROS COMPARTIDOS
    # ---------------------------------------------------------

    grupo = request.GET.get("grupo", "").strip()
    region = request.GET.get("region", "").strip()
    organismo = request.GET.get("organismo", "").strip()
    producto = request.GET.get("producto", "").strip()

    if grupo:
        compras = compras.filter(
            producto_key__producto_grupo=grupo
        )

    if region:
        compras = compras.filter(
            comprador_key__comprador_region=region
        )

    if organismo:
        if not organismo.isdecimal():
            return JsonResponse(
                {"error": "Organismo inválido."},
                status=400,
            )

        compras = compras.filter(
            comprador_key_id=int(organismo)
        )

    # ---------------------------------------------------------
    # 3. PRODUCTOS DEPENDIENTES DEL GRUPO
    # ---------------------------------------------------------

    if tipo == "productos":
        busqueda = request.GET.get("q", "").strip()

        # Sin grupo, exigir al menos 2 caracteres.
        # Con grupo, se pueden listar sus productos directamente.
        if not grupo and len(busqueda) < 2:
            return JsonResponse({
                "productos": [],
                "hay_mas": False,
            })

        if busqueda:
            compras = compras.filter(
                Q(
                    producto_key__producto_codigo__icontains=busqueda
                )
                |
                Q(
                    producto_key__producto_descripcion__icontains=busqueda
                )
            )

        limite = 500

        productos_qs = (
            compras.order_by()
            .values(
                "producto_key__producto_codigo",
                "producto_key__producto_descripcion",
            )
            .distinct()
            .order_by(
                "producto_key__producto_descripcion",
                "producto_key__producto_codigo",
            )
        )

        filas = list(productos_qs[:limite + 1])

        productos = [
            {
                "codigo": fila["producto_key__producto_codigo"],
                "descripcion": (
                    fila["producto_key__producto_descripcion"]
                    or "Sin descripción"
                ),
            }
            for fila in filas[:limite]
        ]

        return JsonResponse({
            "productos": productos,
            "hay_mas": len(filas) > limite,
        })

    # ---------------------------------------------------------
    # 4. RANKING DE COMPETENCIA
    # ---------------------------------------------------------

    if tipo != "ranking":
        return JsonResponse(
            {"error": "Operación inválida."},
            status=400,
        )

    # Producto seleccionado mediante su código.
    if producto:
        compras = compras.filter(
            producto_key__producto_codigo=producto
        )

    por = request.GET.get("por", "proveedor")

    dimensiones = {
        "proveedor": (
            "proveedor_key_id",
            "proveedor_key__proveedor_nombre",
        ),
        "producto": (
            "producto_key_id",
            "producto_key__producto_descripcion",
        ),
        "organismo": (
            "comprador_key_id",
            "comprador_key__comprador_organismo_nombre",
        ),
    }

    if por not in dimensiones:
        return JsonResponse(
            {"error": "Agrupación inválida."},
            status=400,
        )

    # Total del segmento filtrado: denominador de participación.
    monto_segmento = (
        compras.aggregate(
            total=Sum("monto_bruto")
        )["total"]
        or Decimal(0)
    )

    clave, nombre = dimensiones[por]

    ranking_qs = (
        compras.order_by()
        .values(clave, nombre)
        .annotate(
            monto=Sum("monto_bruto"),
            organismos=Count(
                "comprador_key_id",
                distinct=True,
            ),
            proveedores=Count(
                "proveedor_key_id",
                distinct=True,
            ),
        )
        .order_by("-monto", clave)[:10]
    )

    ranking = []

    for fila in ranking_qs:
        monto = fila["monto"] or Decimal(0)

        participacion = (
            round(float(monto / monto_segmento * 100), 2)
            if monto_segmento
            else 0
        )

        ranking.append({
            "id": fila[clave],
            "nombre": fila[nombre] or "Sin informar",
            "monto": float(monto),
            "participacion": participacion,
            "organismos": fila["organismos"],
            "proveedores": fila["proveedores"],
        })

    # ---------------------------------------------------------
    # 5. EVOLUCIÓN MENSUAL DE LOS PRINCIPALES PROVEEDORES
    # ---------------------------------------------------------

    evolucion = []

    if por == "proveedor" and ranking:
        proveedores_top = [
            fila["id"]
            for fila in ranking[:5]
        ]

        evolucion_qs = (
            compras.filter(
                proveedor_key_id__in=proveedores_top
            )
            .order_by()
            .values(
                "fecha_key__anio",
                "fecha_key__mes",
                "proveedor_key_id",
            )
            .annotate(
                monto=Sum("monto_bruto")
            )
            .order_by(
                "fecha_key__anio",
                "fecha_key__mes",
                "proveedor_key_id",
            )
        )

        evolucion = [
            {
                "periodo": (
                    f'{fila["fecha_key__anio"]}-'
                    f'{fila["fecha_key__mes"]:02d}'
                ),
                "id": fila["proveedor_key_id"],
                "monto": float(fila["monto"]),
            }
            for fila in evolucion_qs
        ]

    # ---------------------------------------------------------
    # 6. RESPUESTA PARA CHART.JS
    # ---------------------------------------------------------

    return JsonResponse({
        "por": por,
        "monto_segmento": float(monto_segmento),
        "ranking": ranking,
        "evolucion": evolucion,
    })
