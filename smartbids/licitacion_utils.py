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
