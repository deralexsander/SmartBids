from datetime import date, timedelta
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q

from .models.procurement import Licitacion, LicitacionesProductos
from .models.core import Suscriptor, Preferencia


def mis_licitaciones_view(request):
    total_licitaciones = Licitacion.objects.count()

    # 1. Identificar al suscriptor activo
    uid = (
        request.GET.get('uid')
        or request.COOKIES.get('sb_firebase_uid')
        or request.COOKIES.get('firebase_uid')
        or request.session.get('firebase_uid')
        or request.headers.get('X-Firebase-UID')
    )

    suscriptor = None
    if uid:
        suscriptor = Suscriptor.objects.filter(firebase_uid=str(uid).strip()).first()
    elif request.user.is_authenticated:
        suscriptor = Suscriptor.objects.filter(firebase_uid=request.user.username).first()

    qs_base = Licitacion.objects.select_related('lic_codigo_ucom').all().order_by('-lic_fecha_public')
    preferencias = Preferencia.objects.filter(id_suscriptor=suscriptor).first() if suscriptor else None

    match_perfil = 0

    if preferencias:
        # Normalizar listas
        comunas = [str(c).strip() for c in (preferencias.pref_comunas or []) if str(c).strip()]
        tipos = [str(t).strip() for t in (preferencias.pref_tipo_licitacion or []) if str(t).strip()]
        ucom_ids = [int(u) for u in (preferencias.pref_ucom or []) if str(u).strip().isdigit()]
        palabras = [str(p).strip() for p in (preferencias.pref_palabras_claves or []) if str(p).strip()]
        prods = [str(p).strip() for p in (preferencias.pref_productos or []) if str(p).strip()]

        tiene_filtros = bool(comunas or tipos or ucom_ids or palabras or prods)

        if tiene_filtros:
            # Filtro estricto inicial
            filtros_estrictos = Q()

            if tipos:
                filtros_estrictos &= Q(lic_tipo_licitacion__in=tipos)

            if ucom_ids:
                filtros_estrictos &= Q(lic_codigo_ucom_id__in=ucom_ids)

            if comunas:
                filtros_estrictos &= Q(lic_codigo_ucom__ucom_codigo_comuna__in=comunas)

            if palabras:
                q_pal = Q()
                for w in palabras:
                    q_pal |= Q(lic_nombre__icontains=w) | Q(lic_descripcion__icontains=w)
                filtros_estrictos &= q_pal

            if prods:
                lic_ids_rel = []
                try:
                    lic_ids_rel = list(
                        LicitacionesProductos.objects.filter(
                            codigo_producto__in=prods
                        ).values_list('lic_codigo_id', flat=True)
                    )
                except Exception:
                    pass

                q_prod = Q(lic_codigo__in=lic_ids_rel)
                for prod_cod in prods:
                    q_prod |= Q(lic_codigos_producto__icontains=prod_cod)

                filtros_estrictos &= q_prod

            qs_match = qs_base.filter(filtros_estrictos).distinct()
            total_match = qs_match.count()

            # Respaldo flexible si la combinación estricta resulta en 0
            if total_match == 0:
                filtros_flexibles = Q()

                if prods:
                    lic_ids_rel = []
                    try:
                        lic_ids_rel = list(
                            LicitacionesProductos.objects.filter(
                                codigo_producto__in=prods
                            ).values_list('lic_codigo_id', flat=True)
                        )
                    except Exception:
                        pass
                    q_p = Q(lic_codigo__in=lic_ids_rel)
                    for prod_cod in prods:
                        q_p |= Q(lic_codigos_producto__icontains=prod_cod)
                    filtros_flexibles |= q_p

                if palabras:
                    q_w = Q()
                    for w in palabras:
                        q_w |= Q(lic_nombre__icontains=w) | Q(lic_descripcion__icontains=w)
                    filtros_flexibles |= q_w

                if ucom_ids:
                    filtros_flexibles |= Q(lic_codigo_ucom_id__in=ucom_ids)

                if comunas:
                    filtros_flexibles |= Q(lic_codigo_ucom__ucom_codigo_comuna__in=comunas)

                if tipos:
                    filtros_flexibles |= Q(lic_tipo_licitacion__in=tipos)

                qs = qs_base.filter(filtros_flexibles).distinct()
                match_perfil = qs.count()
            else:
                qs = qs_match
                match_perfil = total_match
        else:
            qs = qs_base
            match_perfil = 0
    else:
        qs = qs_base
        match_perfil = 0

    # Métricas de KPIs
    hoy = date.today()
    plazo_tres_dias = hoy + timedelta(days=3)

    cierre_proximo = qs.filter(
        lic_fecha_cierre__gte=hoy,
        lic_fecha_cierre__lte=plazo_tres_dias
    ).count()

    convenio_marco = qs.filter(lic_tipo_licitacion='CM').count()

    # Paginación
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    licitaciones = paginator.get_page(page_number)

    context = {
        'licitaciones': licitaciones,
        'total_licitaciones': total_licitaciones,
        'match_perfil': match_perfil,
        'cierre_proximo': cierre_proximo,
        'convenio_marco': convenio_marco,
    }

    return render(request, 'smartbids/Mis_licitaciones.html', context)