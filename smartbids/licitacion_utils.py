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

CACHE_KEY_CATALOGO_TIPOS_LICITACION = 'sb_catalogo_tipos_licitacion_v1'

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
    # LP en compras públicas abarca el tramo intermedio (1.000 a 5.000 UTM)
    if codigo == 'LP' and '1.000' in txt and '5.000' not in txt:
        return '1.000 a 5.000 UTM'
    # B2 en licitación privada aplica al tramo superior a 1.000 UTM
    if codigo == 'B2' and '1.000' in txt and 'Mayor' not in txt:
        return 'Mayor a 1.000 UTM'
    return txt


def obtener_catalogo_tipos_licitacion():
    """
    Retorna los tipos de procedimiento oficiales organizados en dos bloques:
      a) Licitaciones Públicas (4 tramos: L1, LE, LP, LR) -> Categorías 1 y 6
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

    codigos_publicos = ['L1', 'LE', 'LP', 'LR']
    codigos_privados = ['E2', 'CO', 'B2']

    tramos_display_fallback = {
        'L1': 'Menor a 100 UTM',
        'LE': '100 a 1.000 UTM',
        'LP': '1.000 a 5.000 UTM',
        'LR': 'Mayor a 5.000 UTM',
        'E2': 'Menor a 100 UTM',
        'CO': '100 a 1.000 UTM',
        'B2': 'Mayor a 1.000 UTM',
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
        glosa_txt = glosa_db or f"Licitación Pública {cod} ({tramo_txt})"
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
        glosa_txt = glosa_db or f"Licitación Privada {cod} ({tramo_txt})"
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
