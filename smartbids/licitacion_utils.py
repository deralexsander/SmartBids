from datetime import datetime

from django.db.models import Q
from django.utils import timezone

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
