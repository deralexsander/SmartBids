"""Dashboard SmartBids: una única tabla de hechos dw.fact_orden_compra.

El grano es fecha/proveedor/comprador/tipo/producto. Por ello, los conteos
cantidad_ordenes_compra NO son aditivos entre productos. La actividad se
presenta mediante cantidad_items y montos (bruto/neto), nunca con COUNT de OC.

Filtro global de período (todas las pestañas):
    gran    = mensual | trimestral | semestral | anual | historico
    periodo = 2026-09 | 2026-T3 | 2026-S2 | 2026 | (vacío en histórico)
"""
import re
from decimal import Decimal
from functools import lru_cache

from django.core.cache import cache
from django.db import connections
from django.db.models import Count, Max, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from smartbids.models import FactOrdenCompra


# ======================================================================
# UTILIDADES
# ======================================================================

def formatear_monto(monto):
    """CLP abreviado; MM significa millones."""
    monto = Decimal(0) if monto is None else Decimal(str(monto))
    if abs(monto) >= 1_000_000:
        return f"${monto / Decimal(1_000_000):,.0f} MM".replace(",", ".")
    if abs(monto) >= 1_000:
        return f"${monto / Decimal(1_000):,.0f} mil".replace(",", ".")
    return f"${monto:,.0f}".replace(",", ".")


_PATRONES_PERIODO = {
    "mensual": re.compile(r"^(\d{4})-(\d{2})$"),
    "trimestral": re.compile(r"^(\d{4})-T([1-4])$"),
    "semestral": re.compile(r"^(\d{4})-S([12])$"),
    "anual": re.compile(r"^(\d{4})$"),
}


def rango_periodo(gran, valor):
    """(anio, mes_ini, mes_fin) del período, o None para histórico.

    Trimestres y semestres son calendario. Lanza ValueError si es inválido.
    """
    if gran == "historico":
        return None
    patron = _PATRONES_PERIODO.get(gran)
    m = patron.match(valor) if patron else None
    if not m:
        raise ValueError("Período inválido")
    anio = int(m.group(1))
    if gran == "mensual":
        mes = int(m.group(2))
        if not 1 <= mes <= 12:
            raise ValueError("Período inválido")
        return anio, mes, mes
    if gran == "trimestral":
        q = int(m.group(2))
        return anio, 3 * q - 2, 3 * q
    if gran == "semestral":
        s = int(m.group(2))
        return anio, 6 * s - 5, 6 * s
    return anio, 1, 12


@lru_cache(maxsize=256)
def _claves_fecha(anio, mes_ini, mes_fin):
    with connections["dw"].cursor() as cursor:
        cursor.execute(
            "SELECT fecha_key FROM dw.dim_fecha "
            "WHERE anio = %s AND mes BETWEEN %s AND %s",
            [anio, mes_ini, mes_fin],
        )
        return tuple(fila[0] for fila in cursor.fetchall())


def periodo_de_request(request):
    """Lista de fecha_key del período pedido; None si es histórico.

    Filtrar la fact por una lista corta de fecha_key (en vez de unirla con
    dim_fecha) permite usar un índice sobre fecha_key. Lanza ValueError.
    """
    rango = rango_periodo(
        request.GET.get("gran", "").strip(),
        request.GET.get("periodo", "").strip(),
    )
    if rango is None:
        return None
    return list(_claves_fecha(*rango))


def _error_periodo():
    return JsonResponse({"error": "Período inválido."}, status=400)


def _modelo_dim(campo):
    """Modelo de la dimensión a la que apunta una FK de la fact."""
    return FactOrdenCompra._meta.get_field(campo).related_model


def _grupos_producto():
    grupos = cache.get("dw_grupos_producto")
    if grupos is None:
        grupos = sorted(
            _modelo_dim("producto_key").objects.using("dw")
            .order_by()
            .exclude(producto_grupo__isnull=True)
            .exclude(producto_grupo="")
            .values_list("producto_grupo", flat=True)
            .distinct(),
            key=str.casefold,
        )
        cache.set("dw_grupos_producto", grupos, 3600)
    return grupos


# ======================================================================
# PÁGINA, PERÍODOS Y KPIs
# ======================================================================

def dashboard_view(request):
    """La página carga vacía y rápida: todo se pide por fetch según el período."""
    return render(request, "smartbids/dashboard.html")


@require_GET
def dashboard_periodos(request):
    """Meses con datos en la fact (el cliente deriva trimestres, semestres y años)."""
    meses = cache.get("dw_periodos_disponibles")
    if meses is None:
        with connections["dw"].cursor() as cursor:
            cursor.execute("""
                SELECT d.anio, d.mes
                FROM dw.dim_fecha d
                WHERE EXISTS (SELECT 1 FROM dw.fact_orden_compra f
                              WHERE f.fecha_key = d.fecha_key)
                GROUP BY d.anio, d.mes
                ORDER BY d.anio, d.mes
            """)
            meses = [{"anio": a, "mes": m} for a, m in cursor.fetchall()]
        cache.set("dw_periodos_disponibles", meses, 3600)
    return JsonResponse({"meses": meses})


@require_GET
def dashboard_kpis(request):
    """KPIs de la barra superior para el período seleccionado.

    Órdenes de compra solo se informa en histórico: por el grano de la fact
    no se pueden sumar entre productos. En un período se informan ítems.
    """
    try:
        claves = periodo_de_request(request)
    except ValueError:
        return _error_periodo()

    if claves is not None and not claves:
        return JsonResponse({"monto": formatear_monto(0), "items": 0, "ordenes": None,
                             "proveedores": 0, "compradores": 0})

    compras = FactOrdenCompra.objects.using("dw")
    campos = {
        "monto": Sum("monto_bruto"),
        "items": Sum("cantidad_items"),
        "proveedores": Count("proveedor_key_id", distinct=True),
        "compradores": Count("comprador_key_id", distinct=True),
    }
    if claves is None:
        campos["ordenes"] = Max("total_oc_procesadas")  # MAX: se repite por fila
    else:
        compras = compras.filter(fecha_key__in=claves)

    r = compras.aggregate(**campos)
    return JsonResponse({
        "monto": formatear_monto(r["monto"]),
        "items": int(r["items"] or 0),
        "ordenes": int(r["ordenes"] or 0) if claves is None else None,
        "proveedores": r["proveedores"],
        "compradores": r["compradores"],
    })


# ======================================================================
# DEMANDA DE PRODUCTOS
# ======================================================================

@require_GET
def dashboard_desglose(request):
    """Punto de entrada de la pestaña de productos (nombre de ruta sin cambios)."""
    return dashboard_productos_explorador(request)


@require_GET
def dashboard_productos_explorador(request):
    """Explorador de demanda; jerarquía: grupo -> nivel 1 -> producto.

    tipo=opciones   : grupos disponibles.
    tipo=ranking    : top 10 del nivel que corresponde a los filtros y al período.
    tipo=evolucion  : monto neto mensual del segmento (serie completa, sin período).

    Los conteos se refieren a ítems, NO a órdenes de compra únicas.
    """
    modo = request.GET.get("tipo", "ranking")
    if modo == "opciones":
        return JsonResponse({"grupos": _grupos_producto()})

    grupo = request.GET.get("grupo", "").strip()
    nivel1 = request.GET.get("nivel1", "").strip()
    por = request.GET.get("por", "grupo")
    if modo not in ("ranking", "evolucion") or por not in ("grupo", "nivel1", "producto"):
        return JsonResponse({"error": "Consulta inválida"}, status=400)
    # Jerarquía estricta: el servidor determina el nivel que corresponde.
    if nivel1 and not grupo:
        return JsonResponse({"error": "Seleccione primero un grupo"}, status=400)
    if modo == "ranking":
        por = "producto" if nivel1 else ("nivel1" if grupo else "grupo")

    where = []
    params = []
    if grupo:
        where.append("p.producto_grupo = %s")
        params.append(grupo)
    if nivel1:
        where.append("p.producto_nivel1 = %s")
        params.append(nivel1)
    where_p = ("WHERE " + " AND ".join(where)) if where else ""

    # ------------------------------------------------------------------
    # Evolución mensual (bajo demanda; ignora el período, el cliente lo resalta)
    # ------------------------------------------------------------------
    if modo == "evolucion":
        if grupo:
            sql = f"""
                SELECT d.anio, d.mes, SUM(f.monto_neto)
                FROM dw.dim_producto p
                JOIN dw.fact_orden_compra f ON f.producto_key = p.producto_key
                JOIN dw.dim_fecha d ON d.fecha_key = f.fecha_key
                {where_p}
                GROUP BY d.anio, d.mes ORDER BY d.anio, d.mes
            """
        else:
            sql = """
                SELECT d.anio, d.mes, SUM(f.monto_neto)
                FROM dw.fact_orden_compra f
                JOIN dw.dim_fecha d ON d.fecha_key = f.fecha_key
                GROUP BY d.anio, d.mes ORDER BY d.anio, d.mes
            """
        with connections["dw"].cursor() as cursor:
            cursor.execute(sql, params)
            evolucion = [{"periodo": f"{a}-{mes:02d}", "monto": float(monto or 0)}
                         for a, mes, monto in cursor.fetchall()]
        return JsonResponse({"evolucion": evolucion})

    # ------------------------------------------------------------------
    # Ranking del período
    # ------------------------------------------------------------------
    try:
        claves = periodo_de_request(request)
    except ValueError:
        return _error_periodo()
    if claves is not None and not claves:
        return JsonResponse({"por": por, "ranking": [],
                             "monto_segmento": 0, "items_segmento": 0})
    filtrar = claves is not None

    if not grupo:
        # Una sola agregación por grupo sobre los hechos del período.
        fecha_cond = "WHERE f.fecha_key = ANY(%s)" if filtrar else ""
        sql = f"""
            WITH ranking AS (
                SELECT p.producto_grupo AS id,
                       COALESCE(p.producto_grupo, 'Sin informar') AS nombre,
                       SUM(f.monto_neto) AS monto,
                       SUM(f.cantidad_items) AS items
                FROM dw.fact_orden_compra f
                JOIN dw.dim_producto p ON p.producto_key = f.producto_key
                {fecha_cond}
                GROUP BY p.producto_grupo
            )
            SELECT id, nombre, monto, items,
                   SUM(monto) OVER () AS monto_total,
                   SUM(items) OVER () AS items_total
            FROM ranking ORDER BY monto DESC NULLS LAST, id ASC NULLS LAST
            LIMIT 10
        """
        with connections["dw"].cursor() as cursor:
            cursor.execute(sql, [claves] if filtrar else [])
            result = cursor.fetchall()
        monto_total = Decimal(result[0][4]) if result else Decimal(0)
        total_items = int(result[0][5]) if result else 0
        ranking = [{"id": r[0], "nombre": r[1], "monto": float(r[2] or 0),
                    "items": int(r[3] or 0),
                    "participacion": round(float(r[2] / monto_total * 100), 2)
                    if monto_total else 0} for r in result]
        return JsonResponse({"por": por, "ranking": ranking,
                             "monto_segmento": float(monto_total),
                             "items_segmento": total_items})

    # Dentro de un grupo: partir de la dimensión con LATERAL para aprovechar
    # idx_fact_producto, y filtrar los hechos del período por fecha_key.
    fecha_where = "AND f.fecha_key = ANY(%s)" if filtrar else ""
    base = f"""
        SELECT p.producto_key, p.producto_codigo, p.producto_descripcion,
               p.producto_grupo, p.producto_nivel1,
               x.monto_neto, x.cantidad_items
        FROM dw.dim_producto p
        CROSS JOIN LATERAL (
            SELECT SUM(f.monto_neto) AS monto_neto,
                   SUM(f.cantidad_items) AS cantidad_items
            FROM dw.fact_orden_compra f
            WHERE f.producto_key = p.producto_key {fecha_where}
        ) x
        {where_p} AND x.cantidad_items IS NOT NULL
    """
    base_params = ([claves] if filtrar else []) + params

    if por == "producto":
        expr = "producto_codigo, producto_descripcion"
        select = "producto_codigo AS id, producto_descripcion AS nombre"
    else:
        expr = "producto_nivel1"
        select = "producto_nivel1 AS id, COALESCE(producto_nivel1, 'Sin informar') AS nombre"

    query = f"""
        WITH base AS MATERIALIZED ({base}),
        agrupado AS (
            SELECT {select}, SUM(monto_neto) AS monto,
                   SUM(cantidad_items) AS items
            FROM base GROUP BY {expr}
        ), totales AS (
            SELECT COALESCE(SUM(monto), 0) AS monto,
                   COALESCE(SUM(items), 0) AS items FROM agrupado
        )
        SELECT a.id, a.nombre, a.monto, a.items, t.monto, t.items
        FROM agrupado a CROSS JOIN totales t
        ORDER BY a.monto DESC NULLS LAST, a.id ASC NULLS LAST
        LIMIT 10
    """
    with connections["dw"].cursor() as cursor:
        cursor.execute(query, base_params)
        rows = cursor.fetchall()
    monto_total = Decimal(rows[0][4]) if rows else Decimal(0)
    items_total = int(rows[0][5]) if rows else 0
    ranking = []
    for codigo, nombre, monto, items, _, _ in rows:
        monto = monto or Decimal(0)
        ranking.append({"id": codigo, "nombre": nombre or "Sin informar",
                        "monto": float(monto), "items": int(items or 0),
                        "participacion": round(float(monto / monto_total * 100), 2)
                        if monto_total else 0})
    return JsonResponse({"por": por, "ranking": ranking,
                         "monto_segmento": float(monto_total),
                         "items_segmento": items_total})


# ======================================================================
# ANÁLISIS DE COMPETENCIA (y ranking de organismos compradores)
# ======================================================================

DIMENSIONES_COMPETENCIA = {
    "proveedor": ("proveedor_key_id", "proveedor_key__proveedor_nombre"),
    "producto": ("producto_key_id", "producto_key__producto_descripcion"),
    "organismo": ("comprador_key_id", "comprador_key__comprador_organismo_nombre"),
}


def _opciones_competencia():
    """Opciones de filtros leídas desde las dimensiones (no desde la fact)."""
    datos = cache.get("dw_opciones_competencia")
    if datos is None:
        Comprador = _modelo_dim("comprador_key")
        regiones = (
            Comprador.objects.using("dw").order_by()
            .exclude(comprador_region__isnull=True).exclude(comprador_region="")
            .values_list("comprador_region", flat=True).distinct()
        )
        organismos = Comprador.objects.using("dw").order_by().values(
            "pk", "comprador_organismo_nombre")
        datos = {
            "grupos": _grupos_producto(),
            "regiones": sorted(regiones, key=str.casefold),
            "organismos": sorted(
                [{"id": o["pk"], "nombre": o["comprador_organismo_nombre"] or "Sin nombre"}
                 for o in organismos],
                key=lambda o: (o["nombre"].casefold(), o["id"]),
            ),
        }
        cache.set("dw_opciones_competencia", datos, 3600)
    return datos


def _productos_competencia(request):
    """Productos para el selector, desde la dimensión (rápido, sin recorrer la fact)."""
    grupo = request.GET.get("grupo", "").strip()
    busqueda = request.GET.get("q", "").strip()
    # Sin grupo, exigir al menos 2 caracteres. Con grupo se listan directamente.
    if not grupo and len(busqueda) < 2:
        return {"productos": [], "hay_mas": False}

    productos = _modelo_dim("producto_key").objects.using("dw")
    if grupo:
        productos = productos.filter(producto_grupo=grupo)
    if busqueda:
        productos = productos.filter(
            Q(producto_codigo__icontains=busqueda)
            | Q(producto_descripcion__icontains=busqueda)
        )
    limite = 500
    filas = list(
        productos.order_by()
        .values("producto_codigo", "producto_descripcion")
        .distinct()
        .order_by("producto_descripcion", "producto_codigo")[:limite + 1]
    )
    return {
        "productos": [{"codigo": f["producto_codigo"],
                       "descripcion": f["producto_descripcion"] or "Sin descripción"}
                      for f in filas[:limite]],
        "hay_mas": len(filas) > limite,
    }


@require_GET
def dashboard_competencia(request):
    """
    Análisis de competencia sobre dw.fact_orden_compra.

    tipo=opciones   : grupos, regiones y organismos para los filtros.
    tipo=productos  : productos del selector (grupo + búsqueda).
    tipo=ranking    : top 10 por proveedor, producto u organismo en el período.
    tipo=evolucion  : serie mensual completa de los 5 primeros del ranking.

    Filtros: grupo, region, organismo, proveedor, producto (código).
    La participación corresponde al monto bruto del segmento filtrado.
    """
    tipo = request.GET.get("tipo", "ranking")
    if tipo == "opciones":
        return JsonResponse(_opciones_competencia())
    if tipo == "productos":
        return JsonResponse(_productos_competencia(request))
    if tipo not in ("ranking", "evolucion"):
        return JsonResponse({"error": "Operación inválida."}, status=400)

    por = request.GET.get("por", "proveedor")
    if por not in DIMENSIONES_COMPETENCIA:
        return JsonResponse({"error": "Agrupación inválida."}, status=400)

    grupo = request.GET.get("grupo", "").strip()
    region = request.GET.get("region", "").strip()
    organismo = request.GET.get("organismo", "").strip()
    proveedor = request.GET.get("proveedor", "").strip()
    producto = request.GET.get("producto", "").strip()
    for valor in (organismo, proveedor):
        if valor and not valor.isdecimal():
            return JsonResponse({"error": "Filtro inválido."}, status=400)

    try:
        claves = periodo_de_request(request)
    except ValueError:
        return _error_periodo()

    # Filtros del segmento (sin período): base para la serie histórica.
    base = FactOrdenCompra.objects.using("dw")
    if grupo:
        base = base.filter(producto_key__producto_grupo=grupo)
    if region:
        base = base.filter(comprador_key__comprador_region=region)
    if organismo:
        base = base.filter(comprador_key_id=int(organismo))
    if proveedor:
        base = base.filter(proveedor_key_id=int(proveedor))
    if producto:
        base = base.filter(producto_key__producto_codigo=producto)

    if claves is not None and not claves:
        vacio = ({"por": por, "series": []} if tipo == "evolucion" else
                 {"por": por, "monto_segmento": 0, "items_segmento": 0, "ranking": []})
        return JsonResponse(vacio)
    compras = base if claves is None else base.filter(fecha_key__in=claves)

    clave, nombre = DIMENSIONES_COMPETENCIA[por]

    # ------------------------------------------------------------------
    # Evolución: los 5 primeros del período, con su serie mensual completa
    # ------------------------------------------------------------------
    if tipo == "evolucion":
        top = list(
            compras.order_by().values(clave, nombre)
            .annotate(monto=Sum("monto_bruto"))
            .order_by("-monto", clave)[:5]
        )
        puntos = {fila[clave]: [] for fila in top}
        if puntos:
            serie_qs = (
                base.filter(**{f"{clave}__in": list(puntos)})
                .order_by()
                .values("fecha_key__anio", "fecha_key__mes", clave)
                .annotate(monto=Sum("monto_bruto"))
                .order_by("fecha_key__anio", "fecha_key__mes")
            )
            for fila in serie_qs:
                puntos[fila[clave]].append({
                    "periodo": f'{fila["fecha_key__anio"]}-{fila["fecha_key__mes"]:02d}',
                    "monto": float(fila["monto"] or 0),
                })
        return JsonResponse({
            "por": por,
            "series": [{"id": fila[clave], "nombre": fila[nombre] or "Sin informar",
                        "puntos": puntos[fila[clave]]} for fila in top],
        })

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------
    # Una sola agregación para ranking y totales del segmento.
    # Compilamos los filtros ORM a SQL parametrizado y aplicamos una ventana
    # al resultado AGRUPADO. La ventana se ejecuta ANTES de LIMIT 10.
    campos = [clave, nombre]
    if por == "producto":
        campos.append("producto_key__producto_codigo")

    agregados = {
        "monto": Sum("monto_bruto"),
        "items": Sum("cantidad_items"),
    }
    if por == "organismo":
        agregados["proveedores"] = Count("proveedor_key_id", distinct=True)
    else:
        agregados["organismos"] = Count("comprador_key_id", distinct=True)

    agrupado_qs = compras.order_by().values(*campos).annotate(**agregados).order_by()
    sql_agrupado, parametros = agrupado_qs.query.get_compiler(using="dw").as_sql()

    # «clave» solo puede proceder de DIMENSIONES_COMPETENCIA (lista fija).
    # Se cita el alias porque Django genera nombres como proveedor_key_id.
    sql = f"""
        SELECT g.*,
               SUM(g.monto) OVER () AS monto_total_segmento,
               SUM(g.items) OVER () AS items_total_segmento
        FROM ({sql_agrupado}) AS g
        ORDER BY g.monto DESC NULLS LAST, g."{clave}" ASC NULLS LAST
        LIMIT 10
    """
    with connections["dw"].cursor() as cursor:
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        filas = [dict(zip(columnas, row)) for row in cursor.fetchall()]

    monto_segmento = (filas[0]["monto_total_segmento"] or Decimal(0)) if filas else Decimal(0)
    items_segmento = int(filas[0]["items_total_segmento"] or 0) if filas else 0

    ranking = []
    for fila in filas:
        monto = fila["monto"] or Decimal(0)
        ranking.append({
            "id": fila[clave],
            "codigo": fila.get("producto_key__producto_codigo"),
            "nombre": fila[nombre] or "Sin informar",
            "monto": float(monto),
            "items": int(fila["items"] or 0),
            "participacion": round(float(monto / monto_segmento * 100), 2) if monto_segmento else 0,
            "organismos": fila.get("organismos", 0),
            "proveedores": fila.get("proveedores", 0),
        })

    return JsonResponse({
        "por": por,
        "monto_segmento": float(monto_segmento),
        "items_segmento": items_segmento,
        "ranking": ranking,
    })