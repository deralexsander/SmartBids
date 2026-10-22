from datetime import date, datetime
from decimal import Decimal
import io

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .models.core import Suscriptor
from .models.catalog import Sector, Organismo
from .models.procurement import UnidadCompra

CACHE_KEY_CATALOGO_TIPOS_LICITACION = 'sb_catalogo_tipos_licitacion_v2'

# Categorías oficiales de catalog.categoria_licitacion:
# 1 = Pública, 6 = Obras Públicas - Pública
# 2 = Privada, 7 = Obras Públicas - Privada
CATEGORIAS_PUBLICAS_IDS = [1, 6]
CATEGORIAS_PRIVADAS_IDS = [2, 7]


def _formatear_tramo_utm(nombre_tramo, codigo=None):
    """Normaliza y formatea la descripción del tramo/monto desde catalog.tramo_licitacion."""
    if not nombre_tramo:
        return ''
    txt = nombre_tramo.strip()
    txt = txt.replace('1000', '1.000').replace('2000', '2.000').replace('5000', '5.000')
    if txt and txt[0].islower():
        txt = txt[0].upper() + txt[1:]
    # B2 en licitación privada aplica al tramo superior a 1.000 UTM
    if codigo == 'B2' and '1.000' in txt and 'Mayor' not in txt:
        return 'Mayor a 1.000 UTM'
    return txt


def obtener_catalogo_tipos_licitacion():
    """
    Retorna los tipos de procedimiento oficiales organizados en dos bloques:
      a) Licitaciones Públicas (5 tramos: L1, LE, LP, LQ, LR) -> Categorías 1 y 6
      b) Licitaciones Privadas (3 tramos: E2, CO, B2) -> Categorías 2 y 7
    Los datos y textos provienen directamente de las tablas maestras de catálogo:
      - catalog.tipo_licitacion (código, glosa, activo y FKs)
      - catalog.categoria_licitacion (Pública [1], Obras Públicas - Pública [6],
        Privada [2], Obras Públicas - Privada [7])
      - catalog.tramo_licitacion (montos oficiales en UTM)
    Excluye tratos directos (cat 3), compras directas (cat 4) y órdenes de compra.
    """
    from django.core.cache import cache
    cached = cache.get(CACHE_KEY_CATALOGO_TIPOS_LICITACION)
    if cached:
        return cached

    codigos_publicos = ['L1', 'LE', 'LP', 'LQ', 'LR']
    codigos_privados = ['E2', 'CO', 'B2']

    tramos_display_fallback = {
        'L1': 'Menor a 100 UTM',
        'LE': '100 a 1.000 UTM',
        'LP': '1.000 a 2.000 UTM',
        'LQ': '2.000 a 5.000 UTM',
        'LR': 'Mayor a 5.000 UTM',
        'E2': 'Menor a 100 UTM',
        'CO': '100 a 1.000 UTM',
        'B2': 'Mayor a 1.000 UTM',
    }

    glosas_display_fallback = {
        'L1': 'Licitación pública inferior a 100 UTM',
        'LE': 'Licitación Pública igual o superior a 100 UTM e inferior a 1.000 UTM',
        'LP': 'Licitación Pública igual o superior a 1.000 UTM e inferior a 2.000 UTM',
        'LQ': 'Licitación Pública igual o superior a 2.000 UTM e inferior a 5.000 UTM',
        'LR': 'Licitación Pública Mayor a 5000 UTM',
        'E2': 'Licitación Privada Inferior a 100 UTM',
        'CO': 'Licitación Privada igual o superior a 100 UTM e inferior a 1000 UTM',
        'B2': 'Licitación Privada igual o superior a 1000 UTM e inferior a 2000 UTM',
    }

    try:
        from .models.catalog import TipoLicitacion
        todos_deseados = codigos_publicos + codigos_privados
        db_qs = TipoLicitacion.objects.select_related(
            'codigo_cat_licitacion', 'codigo_tramo_licitacion'
        ).filter(
            codigo_cat_licitacion_id__in=CATEGORIAS_PUBLICAS_IDS + CATEGORIAS_PRIVADAS_IDS,
            codigo_tipo_licitacion__in=todos_deseados,
        )
        db_tipos = {tl.codigo_tipo_licitacion: tl for tl in db_qs}
    except Exception:
        db_tipos = {}

    publicas = []
    for cod in codigos_publicos:
        obj = db_tipos.get(cod)
        glosa_db = obj.glosa if (obj and obj.glosa) else None
        nombre_tramo_db = (
            obj.codigo_tramo_licitacion.nombre_tramo_licitacion
            if (obj and obj.codigo_tramo_licitacion) else None
        )
        tramo_txt = _formatear_tramo_utm(nombre_tramo_db, cod) or tramos_display_fallback[cod]
        glosa_txt = glosa_db or glosas_display_fallback.get(cod) or f"Licitación Pública {cod} ({tramo_txt})"
        cat_id = obj.codigo_cat_licitacion_id if obj else 1
        cat_nombre = (
            obj.codigo_cat_licitacion.nombre_cat_licitacion
            if (obj and obj.codigo_cat_licitacion) else 'Pública'
        )
        publicas.append({
            'codigo': cod,
            'nombre': cod,
            'tramo': tramo_txt,
            'glosa': glosa_txt,
            'categoria': 'Pública',
            'categoria_id': cat_id,
            'categoria_nombre': cat_nombre,
        })

    privadas = []
    for cod in codigos_privados:
        obj = db_tipos.get(cod)
        glosa_db = obj.glosa if (obj and obj.glosa) else None
        nombre_tramo_db = (
            obj.codigo_tramo_licitacion.nombre_tramo_licitacion
            if (obj and obj.codigo_tramo_licitacion) else None
        )
        tramo_txt = _formatear_tramo_utm(nombre_tramo_db, cod) or tramos_display_fallback[cod]
        glosa_txt = glosa_db or glosas_display_fallback.get(cod) or f"Licitación Privada {cod} ({tramo_txt})"
        cat_id = obj.codigo_cat_licitacion_id if obj else 2
        cat_nombre = (
            obj.codigo_cat_licitacion.nombre_cat_licitacion
            if (obj and obj.codigo_cat_licitacion) else 'Privada'
        )
        privadas.append({
            'codigo': cod,
            'nombre': cod,
            'tramo': tramo_txt,
            'glosa': glosa_txt,
            'categoria': 'Privada',
            'categoria_id': cat_id,
            'categoria_nombre': cat_nombre,
        })

    resultado = {
        'publicas': publicas,
        'privadas': privadas,
        'todos_codigos': codigos_publicos + codigos_privados,
        'categorias_publicas_ids': CATEGORIAS_PUBLICAS_IDS,
        'categorias_privadas_ids': CATEGORIAS_PRIVADAS_IDS,
    }

    try:
        cache.set(CACHE_KEY_CATALOGO_TIPOS_LICITACION, resultado, 86400)
    except Exception:
        pass

    return resultado


CACHE_KEY_CATALOGO_UCOM_ARBOL = 'sb_catalogo_ucom_arbol_v2'


def obtener_catalogo_organismos_ucom(sector_codigo=None, q=None):
    """
    Retorna el catálogo jerárquico completo de Entidades Públicas y Unidades de Compra:
      Sector -> Organismo -> Unidades de Compra
    Basado en las tablas maestras:
      - catalog.sector (30 sectores oficiales: Municipio, Hospital, Salud, Seguridad, etc.)
      - catalog.organismo (1.324 organismos del Estado)
      - procurement.unidad_compra (7.411 unidades de compra vinculadas por ucom_codigo_organismo)
    Permite filtrado previo por código de sector y búsqueda textual ágil por nombre de
    organismo, sigla o unidad de compra sin truncar resultados.
    """
    from collections import defaultdict
    from django.core.cache import cache

    cached_data = cache.get(CACHE_KEY_CATALOGO_UCOM_ARBOL)
    if not cached_data:
        from .models.catalog import Sector, Organismo
        from .models.procurement import UnidadCompra

        try:
            sectores_qs = Sector.objects.values('codigo_sector', 'nombre_sector').order_by('nombre_sector')
            sectores_raw = list(sectores_qs)
        except Exception:
            sectores_raw = []

        try:
            organismos_qs = Organismo.objects.values(
                'codigo_organismo', 'org_nombre', 'org_sigla', 'org_codigo_sector_id'
            ).order_by('org_nombre')
            organismos_raw = list(organismos_qs)
        except Exception:
            organismos_raw = []

        try:
            ucoms_qs = UnidadCompra.objects.values(
                'codigo_unidad_compra', 'ucom_descripcion', 'ucom_codigo_organismo'
            ).order_by('ucom_descripcion')
            ucoms_raw = list(ucoms_qs)
        except Exception:
            ucoms_raw = []

        # Agrupar unidades por organismo
        ucoms_por_org = defaultdict(list)
        for u in ucoms_raw:
            org_id = u.get('ucom_codigo_organismo')
            if org_id is not None:
                ucoms_por_org[org_id].append({
                    'codigo_ucom': u['codigo_unidad_compra'],
                    'descripcion': (u.get('ucom_descripcion') or f"Unidad {u['codigo_unidad_compra']}").strip()
                })

        # Mapeo de sectores
        sec_map = {str(s['codigo_sector']).strip(): (s.get('nombre_sector') or '').strip() for s in sectores_raw}
        orgs_por_sec = defaultdict(list)

        for o in organismos_raw:
            org_id = o['codigo_organismo']
            sec_id = str(o.get('org_codigo_sector_id') or '0').strip()
            org_nom = (o.get('org_nombre') or f"Organismo {org_id}").strip()
            org_sigla = (o.get('org_sigla') or '').strip()
            sec_nom = sec_map.get(sec_id) or f"Sector {sec_id}"

            unidades = ucoms_por_org.get(org_id, [])
            if not unidades:
                unidades = [{
                    'codigo_ucom': org_id,
                    'descripcion': f"{org_nom} (Institución / Sede Central)"
                }]

            orgs_por_sec[sec_id].append({
                'codigo_organismo': str(org_id),
                'nombre_organismo': org_nom,
                'sigla': org_sigla,
                'codigo_sector': sec_id,
                'nombre_sector': sec_nom,
                'unidades': unidades
            })

        sectores_arbol = []
        sectores_resumen = []

        for s in sectores_raw:
            sec_id = str(s['codigo_sector']).strip()
            sec_nom = (s.get('nombre_sector') or f"Sector {sec_id}").strip()
            orgs_sec = sorted(orgs_por_sec.get(sec_id, []), key=lambda x: x['nombre_organismo'])
            total_ucoms_sec = sum(len(o['unidades']) for o in orgs_sec)

            sectores_arbol.append({
                'codigo_sector': sec_id,
                'nombre_sector': sec_nom,
                'organismos_count': len(orgs_sec),
                'unidades_count': total_ucoms_sec,
                'organismos': orgs_sec
            })

            sectores_resumen.append({
                'codigo_sector': sec_id,
                'nombre_sector': sec_nom,
                'organismos_count': len(orgs_sec),
                'unidades_count': total_ucoms_sec,
            })

        if '0' in orgs_por_sec and '0' not in sec_map:
            orgs_sec = sorted(orgs_por_sec['0'], key=lambda x: x['nombre_organismo'])
            sectores_arbol.append({
                'codigo_sector': '0',
                'nombre_sector': 'Organismos Públicos Centralizados',
                'organismos_count': len(orgs_sec),
                'unidades_count': sum(len(o['unidades']) for o in orgs_sec),
                'organismos': orgs_sec
            })
            sectores_resumen.append({
                'codigo_sector': '0',
                'nombre_sector': 'Organismos Públicos Centralizados',
                'organismos_count': len(orgs_sec),
                'unidades_count': sum(len(o['unidades']) for o in orgs_sec),
            })

        sectores_arbol = sorted(sectores_arbol, key=lambda x: x['nombre_sector'])
        sectores_resumen = sorted(sectores_resumen, key=lambda x: x['nombre_sector'])

        cached_data = {
            'sectores': sectores_arbol,
            'sectores_lista': sectores_resumen,
            'total_sectores': len(sectores_arbol),
            'total_organismos': len(organismos_raw),
            'total_unidades': len(ucoms_raw),
        }
        try:
            cache.set(CACHE_KEY_CATALOGO_UCOM_ARBOL, cached_data, 86400)
        except Exception:
            pass

    sectores_resultado = cached_data['sectores']
    if sector_codigo:
        sec_str = str(sector_codigo).strip()
        sectores_resultado = [s for s in sectores_resultado if s['codigo_sector'] == sec_str]

    if q:
        q_norm = q.lower().strip()
        sectores_con_match = []
        for sec in sectores_resultado:
            match_sector = q_norm in sec['nombre_sector'].lower()
            orgs_match = []
            for org in sec['organismos']:
                match_org = (
                    q_norm in org['nombre_organismo'].lower()
                    or (org['sigla'] and q_norm in org['sigla'].lower())
                    or q_norm in str(org['codigo_organismo'])
                )
                if match_org or match_sector:
                    orgs_match.append(org)
                else:
                    ucoms_match = [
                        u for u in org['unidades']
                        if q_norm in u['descripcion'].lower() or q_norm in str(u['codigo_ucom'])
                    ]
                    if ucoms_match:
                        org_copy = dict(org)
                        org_copy['unidades'] = ucoms_match
                        orgs_match.append(org_copy)
            if orgs_match:
                sec_copy = dict(sec)
                sec_copy['organismos'] = orgs_match
                sectores_con_match.append(sec_copy)
        sectores_resultado = sectores_con_match

    return {
        'status': 'ok',
        'sectores': sectores_resultado,
        'sectores_lista': cached_data['sectores_lista'],
        'total_sectores': cached_data['total_sectores'],
        'total_organismos': cached_data['total_organismos'],
        'total_unidades': cached_data['total_unidades'],
    }


ESTADOS_LICITACION = {
    'publicada': 'Publicada',
    'preguntas': 'Período de preguntas',
    'ofertas': 'Recepción de ofertas',
    'cerrada': 'Cerrada',
}


def resolver_suscriptor(request):
    uid = (
        request.GET.get('uid')
        or request.COOKIES.get('sb_firebase_uid')
        or request.COOKIES.get('firebase_uid')
        or request.session.get('firebase_uid')
        or request.headers.get('X-Firebase-UID')
    )
    if uid:
        return Suscriptor.objects.filter(firebase_uid=str(uid).strip()).first()
    if request.user.is_authenticated:
        return Suscriptor.objects.filter(firebase_uid=request.user.username).first()
    return None


def estado_licitacion(licitacion, ahora=None):
    ahora = ahora or timezone.now()
    hoy = timezone.localdate(ahora)
    fecha_respuestas = licitacion.lic_fecha_respuestas
    fecha_preguntas = licitacion.lic_fecha_preguntas
    if fecha_respuestas and timezone.is_naive(fecha_respuestas):
        fecha_respuestas = timezone.make_aware(fecha_respuestas, timezone.get_current_timezone())
    if fecha_preguntas and timezone.is_naive(fecha_preguntas):
        fecha_preguntas = timezone.make_aware(fecha_preguntas, timezone.get_current_timezone())
    if licitacion.lic_fecha_cierre and licitacion.lic_fecha_cierre < hoy:
        estado = 'cerrada'
    elif fecha_respuestas and fecha_respuestas <= ahora:
        estado = 'ofertas'
    elif fecha_preguntas and fecha_preguntas <= ahora:
        estado = 'preguntas'
    else:
        estado = 'publicada'
    return estado, ESTADOS_LICITACION[estado]


def hito_completado(fecha, ahora=None):
    if not fecha:
        return False
    ahora = ahora or timezone.now()
    if isinstance(fecha, datetime):
        if timezone.is_naive(fecha):
            fecha = timezone.make_aware(fecha, timezone.get_current_timezone())
        return fecha <= ahora
    return fecha <= timezone.localdate(ahora)


def estado_qs(estado, ahora=None):
    ahora = ahora or timezone.now()
    hoy = timezone.localdate(ahora)
    no_cerrada = Q(lic_fecha_cierre__gte=hoy) | Q(lic_fecha_cierre__isnull=True)
    cerrada = Q(lic_fecha_cierre__lt=hoy)

    if estado == 'cerrada':
        return cerrada
    if estado == 'ofertas':
        return no_cerrada & Q(lic_fecha_respuestas__lte=ahora)
    if estado == 'preguntas':
        return (
            no_cerrada
            & Q(lic_fecha_preguntas__lte=ahora)
            & (Q(lic_fecha_respuestas__gt=ahora) | Q(lic_fecha_respuestas__isnull=True))
        )
    return (
        no_cerrada
        & (Q(lic_fecha_preguntas__gt=ahora) | Q(lic_fecha_preguntas__isnull=True))
    )


def escribir_fila_csv(writer, values):
    safe_values = []
    for value in values:
        text = '' if value is None else str(value)
        if text.lstrip().startswith(('=', '+', '-', '@')):
            text = "'" + text
        safe_values.append(text)
    writer.writerow(safe_values)


def sanitizar_valor_excel(value):
    if value is None:
        return ''
    if isinstance(value, (int, float, Decimal)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    text = str(value)
    if text.lstrip().startswith(('=', '+', '-', '@')):
        text = "'" + text
    return text


def generar_excel_response(filename, headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte"

    header_fill = PatternFill(start_color="11634E", end_color="11634E", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    ws.append(list(headers))
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border

    ws.row_dimensions[1].height = 28

    for row_idx, row in enumerate(rows, start=2):
        sanitized_row = [sanitizar_valor_excel(val) for val in row]
        ws.append(sanitized_row)
        for col_idx in range(1, len(row) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 60)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def generar_excel_multitabla_response(filename, tablas_dict):
    """
    Genera un archivo Excel con múltiples hojas formateadas a partir de un diccionario:
    {
        'Nombre Hoja': {
            'encabezados': ['Col1', 'Col2', ...],
            'filas': [[val1, val2, ...], ...]
        }
    }
    """
    wb = openpyxl.Workbook()
    default_sheet = wb.active

    header_fill = PatternFill(start_color="11634E", end_color="11634E", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    first = True
    for sheet_title, data in tablas_dict.items():
        clean_title = str(sheet_title).replace(':', '').replace('/', '-').replace('?', '')[:31]
        if first:
            ws = default_sheet
            ws.title = clean_title
            first = False
        else:
            ws = wb.create_sheet(title=clean_title)

        headers = data.get('encabezados', [])
        rows = data.get('filas', [])

        if headers:
            ws.append(list(headers))
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
                cell.border = thin_border
            ws.row_dimensions[1].height = 28

        for row_idx, row in enumerate(rows, start=2 if headers else 1):
            sanitized_row = [sanitizar_valor_excel(val) for val in row]
            ws.append(sanitized_row)
            for col_idx in range(1, len(row) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 60)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
