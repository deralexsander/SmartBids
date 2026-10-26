import json
import logging
import re
import difflib
import unicodedata
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import DataError, DatabaseError
from django.db.models import Q, Value
from django.db.models.functions import Replace, Upper

from django.core.cache import cache
from smartbids.models import Suscriptor, Empresa, Preferencia, EstadoSuscriptor
from smartbids.models.catalog import Comuna, Organismo, Producto, Region, Provincia, Sector, Proveedor, GrupoProducto, Nivel1Producto
from smartbids.models.procurement import UnidadCompra
from .auth_views import validar_autorizacion_suscriptor

logger = logging.getLogger(__name__)


def _normalizar_rut(rut):
    return re.sub(r'[^0-9K]', '', str(rut or '').upper())


def _formatear_rut(rut):
    normalizado = _normalizar_rut(rut)
    if len(normalizado) not in (8, 9) or not normalizado[:-1].isdigit():
        return ''
    cuerpo = normalizado[:-1]
    verificador = normalizado[-1]
    suma = 0
    factor = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resultado = 11 - (suma % 11)
    verificador_esperado = '0' if resultado == 11 else 'K' if resultado == 10 else str(resultado)
    if verificador != verificador_esperado:
        return ''

    cuerpo_formateado = re.sub(r'\B(?=(\d{3})+(?!\d))', '.', cuerpo)
    return f'{cuerpo_formateado}-{verificador}'


def _buscar_empresa_por_rut(rut):
    rut_normalizado = _normalizar_rut(rut)
    rut_db_normalizado = Replace(
        Replace(
            Replace(Upper('emp_rut'), Value('.'), Value('')),
            Value('-'), Value('')
        ),
        Value(' '), Value('')
    )
    return Empresa.objects.annotate(
        rut_normalizado=rut_db_normalizado
    ).filter(rut_normalizado__iexact=rut_normalizado).first()


def _normalizar_codigo_comuna(valor):
    """
    Normaliza el valor recibido para la comuna a su código oficial de 5 dígitos.
    Maneja formatos como:
      - '13101'
      - '13101 - Santiago'
      - 'Santiago (13101)'
      - 'Santiago' (búsqueda por nombre)
    Garantiza que nunca exceda 5 caracteres para evitar DataError en PostgreSQL.
    """
    if not valor:
        return ''
    val = str(valor).strip()
    match = re.search(r'\b(\d{5})\b', val)
    if match:
        codigo = match.group(1)
        if Comuna.objects.filter(codigo_comuna=codigo).exists():
            return codigo
    if len(val) == 5 and Comuna.objects.filter(codigo_comuna=val).exists():
        return val
    comuna_obj = Comuna.objects.filter(nombre_comuna__iexact=val).first()
    if comuna_obj:
        return comuna_obj.codigo_comuna
    comuna_flex = Comuna.objects.filter(nombre_comuna__icontains=val).first()
    if comuna_flex:
        return comuna_flex.codigo_comuna
    return val[:5]

ORDEN_GEOGRAFICO_CHILE = {
    '15': 1, 'XV': 1,
    '01': 2, '1': 2, 'I': 2,
    '02': 3, '2': 3, 'II': 3,
    '03': 4, '3': 4, 'III': 4,
    '04': 5, '4': 5, 'IV': 5,
    '05': 6, '5': 6, 'V': 6,
    '13': 7, 'RM': 7,
    '06': 8, '6': 8, 'VI': 8,
    '07': 9, '7': 9, 'VII': 9,
    '16': 10, 'XVI': 10,
    '08': 11, '8': 11, 'VIII': 11,
    '09': 12, '9': 12, 'IX': 12,
    '14': 13, 'XIV': 13,
    '10': 14, '10': 14, 'X': 14,
    '11': 15, 'XI': 15,
    '12': 16, 'XII': 16,
}

CACHE_KEY_PRODUCTOS_ARBOL = 'catalogos_productos_arbol_v2'



def normalizar_cadena_simple(texto: str) -> str:
    if not texto:
        return ''
    norm = unicodedata.normalize('NFD', str(texto))
    sin_tildes = ''.join(c for c in norm if unicodedata.category(c) != 'Mn')
    limpio = re.sub(r'[^a-zA-Z0-9\s]', ' ', sin_tildes)
    return ' '.join(limpio.lower().split())


@csrf_exempt
def catalogos_preferencias(request):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    tipo = request.GET.get('tipo', '').strip()
    query = request.GET.get('q', '').strip()
    comuna_empresa = request.GET.get('comuna_empresa', '').strip()

    try:
        limite = min(int(request.GET.get('limit', 40) or 40), 100)
    except ValueError:
        limite = 40

    if tipo == 'sugerir_palabra':
        palabra_raw = query.strip()
        palabra_limpia = normalizar_cadena_simple(palabra_raw)

        if len(palabra_limpia) < 3:
            return JsonResponse({'status': 'ok', 'sugerencia': None})

        prefijo = palabra_limpia[:3]
        descripciones = Producto.objects.filter(
            descripcion__icontains=prefijo
        ).values_list('descripcion', flat=True)[:150]

        vocabulario = set()
        for d in descripciones:
            if not d:
                continue
            d_norm = normalizar_cadena_simple(d)
            for w in re.findall(r'[a-z0-9]{3,}', d_norm):
                vocabulario.add(w)

        if palabra_limpia in vocabulario:
            return JsonResponse({'status': 'ok', 'sugerencia': None, 'exacto': True})

        coincidencias = difflib.get_close_matches(palabra_limpia, list(vocabulario), n=1, cutoff=0.72)
        sugerencia = coincidencias[0] if coincidencias else None

        return JsonResponse({'status': 'ok', 'sugerencia': sugerencia})

    if tipo == 'tipos_licitacion':
        from smartbids.utils.licitacion_utils import obtener_catalogo_tipos_licitacion
        return JsonResponse({
            'status': 'ok',
            'datos': obtener_catalogo_tipos_licitacion()
        })

    if tipo == 'territorio':
        regiones_query = list(Region.objects.values('codigo_region', 'nombre_region'))
        provincias = list(
            Provincia.objects.values('codigo_provincia', 'nombre_provincia', 'codigo_region_id')
            .order_by('nombre_provincia')
        )
        comunas = list(
            Comuna.objects.values('codigo_comuna', 'nombre_comuna', 'codigo_provincia_id')
            .order_by('nombre_comuna')
        )

        region_prioritaria = None
        if comuna_empresa:
            comuna_obj = Comuna.objects.select_related('codigo_provincia').filter(codigo_comuna=comuna_empresa).first()
            if comuna_obj and comuna_obj.codigo_provincia:
                region_prioritaria = str(comuna_obj.codigo_provincia.codigo_region_id).strip()

        def ordenar_regiones(r):
            cod_str = str(r['codigo_region']).strip()
            es_matriz = 0 if (region_prioritaria and cod_str == region_prioritaria) else 1
            pos_geo = ORDEN_GEOGRAFICO_CHILE.get(cod_str, 99)
            return (es_matriz, pos_geo, r['nombre_region'])

        regiones_ordenadas = sorted(regiones_query, key=ordenar_regiones)

        return JsonResponse({
            'status': 'ok',
            'region_prioritaria': region_prioritaria,
            'regiones': regiones_ordenadas,
            'provincias': provincias,
            'comunas': comunas
        })

    if tipo == 'productos_arbol':
        try:
            q_filtro = request.GET.get('q', '').strip()

            if not q_filtro:
                cached_data = cache.get(CACHE_KEY_PRODUCTOS_ARBOL)
                if cached_data:
                    return JsonResponse(cached_data)

            # Consultar grupos y niveles desde el catálogo en base de datos
            grupos_qs = GrupoProducto.objects.all().order_by('codigo_grupo_producto')
            grupos_map = {}
            for g in grupos_qs:
                cod_grp = str(g.codigo_grupo_producto).strip()
                grupos_map[cod_grp] = {
                    'codigo_grupo': cod_grp,
                    'nombre_grupo': g.nombre_grupo_producto.strip(),
                    'niveles': {}
                }

            niveles_qs = Nivel1Producto.objects.all().order_by('codigo_nivel1')
            niveles_map = {}
            for n in niveles_qs:
                cod_n1 = str(n.codigo_nivel1).strip()
                cod_grp = str(n.codigo_grupo_producto_id or '').strip()
                n_info = {
                    'codigo_nivel1': cod_n1,
                    'descripcion': (n.descripcion or f"Nivel {cod_n1}").strip(),
                    'codigo_grupo': cod_grp,
                    'productos': []
                }
                niveles_map[cod_n1] = n_info
                if cod_grp in grupos_map:
                    grupos_map[cod_grp]['niveles'][cod_n1] = n_info
                else:
                    # Agrupar en grupo de reserva si existiera
                    grp_fallback = '21' if '21' in grupos_map else (list(grupos_map.keys())[0] if grupos_map else '00')
                    if grp_fallback in grupos_map:
                        grupos_map[grp_fallback]['niveles'][cod_n1] = n_info

            query_base = Producto.objects.exclude(descripcion__isnull=True).exclude(descripcion__exact='')

            if q_filtro:
                query_base = query_base.filter(
                    Q(descripcion__icontains=q_filtro) |
                    Q(codigo_producto__icontains=q_filtro) |
                    Q(glosa_nivel2__icontains=q_filtro) |
                    Q(glosa_nivel3__icontains=q_filtro) |
                    Q(glosa_nivel4__icontains=q_filtro)
                )[:400]
            else:
                query_base = query_base.order_by('codigo_producto')

            campos_prod = [
                'codigo_producto', 'descripcion', 'nivel1_id',
                'nivel2', 'nivel3', 'nivel4',
                'glosa_nivel2', 'glosa_nivel3', 'glosa_nivel4'
            ]
            prods = list(query_base.values(*campos_prod))

            for p in prods:
                cod = str(p['codigo_producto']).strip()
                desc_raw = str(p['descripcion'] or '').replace('\r', ' ').replace('\n', ' ')
                desc = re.sub(r'\s+', ' ', desc_raw).strip()

                n1 = str(p.get('nivel1_id') or '').strip()
                n2 = str(p.get('nivel2') or '').strip()
                n3 = str(p.get('nivel3') or '').strip()
                n4 = str(p.get('nivel4') or '').strip()

                # Descomponer código soportando primer bloque de 3 dígitos (Obras Civiles MOP)
                # o 2 dígitos (ONU estándar) si viniera sin FK
                if not n1:
                    if len(cod) >= 9:
                        n1 = cod[:3]
                        n2 = cod[3:5]
                        n3 = cod[5:7]
                        n4 = cod[7:9]
                    else:
                        n1 = cod[:2]
                        n2 = cod[2:4]
                        n3 = cod[4:6]
                        n4 = cod[6:8]

                cod_fmt = f"{n1}-{n2}-{n3}-{n4}" if (n1 and n2 and n3 and n4) else cod

                if not desc:
                    desc = p.get('glosa_nivel4') or p.get('glosa_nivel3') or f"Producto {cod_fmt}"

                prod_item = {
                    'codigo_producto': cod,
                    'codigo_formateado': cod_fmt,
                    'descripcion': desc,
                    'nivel1': n1,
                    'nivel2': n2,
                    'nivel3': n3,
                    'nivel4': n4,
                    'glosa_nivel2': (p.get('glosa_nivel2') or '').strip(),
                    'glosa_nivel3': (p.get('glosa_nivel3') or '').strip(),
                    'glosa_nivel4': (p.get('glosa_nivel4') or '').strip(),
                }

                if n1 in niveles_map:
                    niveles_map[n1]['productos'].append(prod_item)
                else:
                    # En caso de nivel no registrado explícitamente en catálogo
                    grp_key = '12' if n1 in ('101', '102', '103', '104') else '21'
                    if grp_key not in grupos_map and grupos_map:
                        grp_key = list(grupos_map.keys())[0]
                    if grp_key in grupos_map:
                        if n1 not in grupos_map[grp_key]['niveles']:
                            grupos_map[grp_key]['niveles'][n1] = {
                                'codigo_nivel1': n1,
                                'descripcion': f"Nivel {n1}",
                                'codigo_grupo': grp_key,
                                'productos': []
                            }
                        grupos_map[grp_key]['niveles'][n1]['productos'].append(prod_item)

            grupos_list = []
            for grp_data in sorted(grupos_map.values(), key=lambda g: g['codigo_grupo']):
                niveles_del_grupo = []
                for niv_data in sorted(grp_data['niveles'].values(), key=lambda n: n['codigo_nivel1']):
                    if niv_data['productos']:
                        niveles_del_grupo.append({
                            'codigo_nivel1': niv_data['codigo_nivel1'],
                            'descripcion': niv_data['descripcion'],
                            'productos': niv_data['productos']
                        })

                if niveles_del_grupo:
                    grupos_list.append({
                        'codigo_grupo': grp_data['codigo_grupo'],
                        'nombre_grupo': grp_data['nombre_grupo'],
                        'niveles': niveles_del_grupo
                    })

            # Formato de retrocompatibilidad plana para componentes anteriores
            rubros_compat = []
            for g in grupos_list:
                for niv in g['niveles']:
                    rubros_compat.append({
                        'codigo_rubro': niv['codigo_nivel1'],
                        'nombre_rubro': f"{niv['codigo_nivel1']} – {niv['descripcion']}",
                        'codigo_grupo': g['codigo_grupo'],
                        'nombre_grupo': g['nombre_grupo'],
                        'productos': niv['productos']
                    })

            resp_data = {
                'status': 'ok',
                'grupos': grupos_list,
                'rubros': rubros_compat
            }

            if not q_filtro:
                cache.set(CACHE_KEY_PRODUCTOS_ARBOL, resp_data, 86400)

            return JsonResponse(resp_data)
        except Exception as e:
            logger.error(f"[SmartBids] Error al generar árbol de productos: {str(e)}")
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

    if tipo == 'ucom_arbol':
        try:
            from smartbids.utils.licitacion_utils import obtener_catalogo_organismos_ucom
            sector_filtro = request.GET.get('sector', '').strip()
            q_filtro = request.GET.get('q', '').strip()
            data_ucom = obtener_catalogo_organismos_ucom(sector_codigo=sector_filtro or None, q=q_filtro or None)
            return JsonResponse(data_ucom)
        except Exception as e:
            logger.error(f"[SmartBids] Error al generar árbol de unidades de compra: {str(e)}")
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

        except Exception as e:
            logger.error(f"[SmartBids] Error al generar árbol de unidades de compra: {str(e)}")
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

    return JsonResponse({'resultados': []})


@csrf_exempt
def obtener_perfil_suscriptor(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')

        if not uid:
            return JsonResponse({'status': 'error', 'mensaje': 'No se recibió el UID del suscriptor.'}, status=400)

        suscriptor = Suscriptor.objects.select_related('codigo_estado', 'sus_rut_empresa').filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'error', 'mensaje': f'Suscriptor no encontrado para el UID: {uid}'}, status=404)

        autorizado, motivo = validar_autorizacion_suscriptor(request, suscriptor)
        if not autorizado:
            return JsonResponse({'status': 'error', 'mensaje': motivo}, status=403)

        pref = Preferencia.objects.filter(id_suscriptor=suscriptor).first()
        emp = suscriptor.sus_rut_empresa

        # ---------------------------------------------------------
        # DETERMINAR SI ES CUENTA DUEÑA (ADMINISTRADOR) O ASOCIADA
        # ---------------------------------------------------------
        es_dueno = True
        correo_dueno = ''
        if emp and emp.emp_rut:
            primer_suscriptor = Suscriptor.objects.filter(sus_rut_empresa=emp).order_by('fecha_registro').first()
            if primer_suscriptor:
                if primer_suscriptor.id_suscriptor != suscriptor.id_suscriptor:
                    es_dueno = False
                    correo_dueno = emp.emp_contacto_correo
                else:
                    es_dueno = True
                    correo_dueno = emp.emp_contacto_correo

        def to_list(val):
            if isinstance(val, list):
                return [str(x).strip() for x in val if str(x).strip()]
            if isinstance(val, str) and val.strip():
                return [x.strip() for x in val.split(',') if x.strip()]
            return []

        raw_comunas = to_list(pref.pref_comunas) if pref else []
        mapa_comunas = {
            str(c['codigo_comuna']).strip(): c['nombre_comuna']
            for c in Comuna.objects.filter(codigo_comuna__in=raw_comunas).values('codigo_comuna', 'nombre_comuna')
        }
        comunas_detalle = [{'code': cod, 'label': mapa_comunas.get(cod, cod)} for cod in raw_comunas]

        raw_prods = to_list(pref.pref_productos) if pref else []
        mapa_prods = {}
        if raw_prods:
            prods_db = Producto.objects.filter(codigo_producto__in=raw_prods).values(
                'codigo_producto', 'descripcion', 'nivel1_id', 'nivel2', 'nivel3', 'nivel4',
                'glosa_nivel4', 'glosa_nivel3'
            )
            for p in prods_db:
                cod = str(p['codigo_producto']).strip()
                desc = (p.get('descripcion') or '').strip()
                n1 = str(p.get('nivel1_id') or '').strip()
                n2 = str(p.get('nivel2') or '').strip()
                n3 = str(p.get('nivel3') or '').strip()
                n4 = str(p.get('nivel4') or '').strip()
                if not n1:
                    n1 = cod[:3] if len(cod) >= 9 else cod[:2]
                    n2 = cod[3:5] if len(cod) >= 9 else cod[2:4]
                    n3 = cod[5:7] if len(cod) >= 9 else cod[4:6]
                    n4 = cod[7:9] if len(cod) >= 9 else cod[6:8]
                cod_fmt = f"{n1}-{n2}-{n3}-{n4}" if (n1 and n2 and n3 and n4) else cod
                desc_final = desc or p.get('glosa_nivel4') or p.get('glosa_nivel3') or f"Producto {cod_fmt}"
                mapa_prods[cod] = {
                    'descripcion': desc_final,
                    'formateado': cod_fmt
                }

        productos_detalle = []
        for cod in raw_prods:
            cod_str = str(cod).strip()
            info = mapa_prods.get(cod_str)
            if info:
                label = f"{info['descripcion']} ({info['formateado']})"
            else:
                if len(cod_str) == 9:
                    fmt = f"{cod_str[:3]}-{cod_str[3:5]}-{cod_str[5:7]}-{cod_str[7:9]}"
                elif len(cod_str) == 8:
                    fmt = f"{cod_str[:2]}-{cod_str[2:4]}-{cod_str[4:6]}-{cod_str[6:8]}"
                else:
                    fmt = cod_str
                label = f"Producto {fmt}" if fmt != cod_str else cod_str
            productos_detalle.append({'code': cod_str, 'label': label})

        raw_ucom = to_list(pref.pref_ucom) if pref else []
        ucom_ids = [int(x) for x in raw_ucom if str(x).isdigit()]
        mapa_ucom = {
            str(u['codigo_unidad_compra']): u['ucom_descripcion']
            for u in UnidadCompra.objects.filter(codigo_unidad_compra__in=ucom_ids).values('codigo_unidad_compra', 'ucom_descripcion')
        }
        faltantes = [cod for cod in ucom_ids if str(cod) not in mapa_ucom]
        if faltantes:
            for org in Organismo.objects.filter(codigo_organismo__in=faltantes).values('codigo_organismo', 'org_nombre'):
                mapa_ucom[str(org['codigo_organismo'])] = org['org_nombre']
        ucom_detalle = [{'code': str(cod), 'label': mapa_ucom.get(str(cod), f"Unidad {cod}")} for cod in raw_ucom]

        nom_comuna_emp = ''
        cod_comuna_emp = ''
        if emp and emp.emp_codigo_comuna:
            cod_comuna_emp = getattr(emp, 'emp_codigo_comuna_id', getattr(emp, 'emp_codigo_comuna', '')) or ''
            comuna_obj = Comuna.objects.filter(codigo_comuna=cod_comuna_emp).first()
            if comuna_obj:
                nom_comuna_emp = comuna_obj.nombre_comuna

        # Sincronizar iniciales si existen nombres pero falta la columna sus_iniciales
        inic = (suscriptor.sus_iniciales or '').strip()
        if not inic and (suscriptor.sus_nombre1 or suscriptor.sus_apellido1):
            partes = [suscriptor.sus_nombre1, suscriptor.sus_nombre2, suscriptor.sus_apellido1, suscriptor.sus_apellido2]
            inic = "".join([p[0].upper() for p in partes if p])[:5]
            if inic:
                suscriptor.sus_iniciales = inic
                suscriptor.save(update_fields=['sus_iniciales'])

        return JsonResponse({
            'status': 'ok',
            'datos': {
                'id_suscriptor': suscriptor.id_suscriptor,
                'firebase_uid': suscriptor.firebase_uid,
                'sus_nombre1': suscriptor.sus_nombre1 or '',
                'sus_nombre2': suscriptor.sus_nombre2 or '',
                'sus_apellido1': suscriptor.sus_apellido1 or '',
                'sus_apellido2': suscriptor.sus_apellido2 or '',
                'sus_nombre_social': suscriptor.sus_nombre_social or '',
                'sus_iniciales': suscriptor.sus_iniciales or inic or '',
                'codigo_estado': suscriptor.codigo_estado_id if suscriptor.codigo_estado else None,
                'nombre_estado': suscriptor.codigo_estado.nombre_estado if suscriptor.codigo_estado else 'Activo',
                'token_sesion': getattr(suscriptor, 'token_sesion', '') or '',
                'fecha_registro': suscriptor.fecha_registro.isoformat() if suscriptor.fecha_registro else None,
                'fecha_actualizacion': suscriptor.fecha_actualizacion.isoformat() if suscriptor.fecha_actualizacion else None,
                'asociacion': {
                    'es_dueno': es_dueno,
                    'correo_dueno': correo_dueno
                },
                'empresa': {
                    'emp_rut': emp.emp_rut if emp else '',
                    'emp_fantasia': emp.emp_nombre_fantasia if emp else '',
                    'emp_razon_social': emp.emp_razon_social if emp else '',
                    'emp_contacto_nombre': getattr(emp, 'emp_contacto_nombre', '') if emp else '',
                    'emp_contacto_correo': emp.emp_contacto_correo if emp else '',
                    'emp_iniciales': emp.emp_iniciales if emp else '',
                    'emp_contacto_telefono': emp.emp_contacto_telefono if emp else '',
                    'emp_codigo_comuna': cod_comuna_emp,
                    'emp_nombre_comuna': nom_comuna_emp,
                    'emp_direccion': emp.emp_direccion if emp else '',
                } if emp else {},
                'preferencias': {
                    'comunas_detalle': comunas_detalle,
                    'productos_detalle': productos_detalle,
                    'ucom_detalle': ucom_detalle,
                    'pref_tipo_licitacion': to_list(pref.pref_tipo_licitacion) if pref else [],
                    'pref_palabras_claves': to_list(pref.pref_palabras_claves) if pref else [],
                } if pref else {}
            }
        })
    except Exception as e:
        logger.error(f"[SmartBids] Error al obtener perfil: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error en el servidor: {str(e)}'}, status=500)


@csrf_exempt
def actualizar_preferencias_suscriptor(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')

        if not uid:
            return JsonResponse({'status': 'error', 'mensaje': 'No se recibió el identificador de sesión (UID).'}, status=400)

        suscriptor = Suscriptor.objects.filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'error', 'mensaje': 'Suscriptor no encontrado.'}, status=404)

        autorizado, motivo = validar_autorizacion_suscriptor(request, suscriptor)
        if not autorizado:
            return JsonResponse({'status': 'error', 'mensaje': motivo}, status=403)

        pref, _ = Preferencia.objects.get_or_create(id_suscriptor=suscriptor)

        if 'pref_comunas' in data:
            pref.pref_comunas = [str(c).strip()[:5] for c in data.get('pref_comunas', []) if str(c).strip()]

        if 'pref_productos' in data:
            pref.pref_productos = [str(p).strip()[:20] for p in data.get('pref_productos', []) if str(p).strip()]

        if 'pref_tipo_licitacion' in data:
            pref.pref_tipo_licitacion = [str(t).strip()[:2] for t in data.get('pref_tipo_licitacion', []) if str(t).strip()]

        if 'pref_ucom' in data:
            ucom = []
            for u in data.get('pref_ucom', []):
                try:
                    ucom.append(int(u))
                except (ValueError, TypeError):
                    continue
            pref.pref_ucom = ucom

        palabras_limpias = None
        if 'pref_palabras_claves' in data:
            palabras_recibidas = data.get('pref_palabras_claves', [])
            if isinstance(palabras_recibidas, str):
                palabras_recibidas = palabras_recibidas.split(',')

            palabras_limpias = []
            palabras_set = set()
            for w in palabras_recibidas:
                token = normalizar_cadena_simple(str(w))
                if token and len(token) > 1:
                    for item in token.split():
                        item = item[:50].strip()
                        if len(item) > 1 and item not in palabras_set:
                            palabras_set.add(item)
                            palabras_limpias.append(item)
            pref.pref_palabras_claves = palabras_limpias

        pref.save()

        suscriptor.fecha_actualizacion = timezone.now()
        suscriptor.save(update_fields=['fecha_actualizacion'])

        response_payload = {
            'status': 'ok',
            'mensaje': 'Preferencias guardadas con éxito.'
        }
        if palabras_limpias is not None:
            response_payload['palabras_sanitizadas'] = palabras_limpias

        return JsonResponse(response_payload)

    except DatabaseError as db_err:
        logger.error(f"[SmartBids] Error de PostgreSQL al guardar preferencias: {str(db_err)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error de base de datos: {str(db_err)}'}, status=500)
    except Exception as e:
        logger.error(f"[SmartBids] Error general al guardar preferencias: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error al guardar preferencias: {str(e)}'}, status=500)


@csrf_exempt
def actualizar_perfil_suscriptor(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')
        suscriptor = Suscriptor.objects.filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'error', 'mensaje': 'Suscriptor no encontrado.'}, status=404)

        autorizado, motivo = validar_autorizacion_suscriptor(request, suscriptor)
        if not autorizado:
            return JsonResponse({'status': 'error', 'mensaje': motivo}, status=403)

        suscriptor.sus_nombre1 = (data.get('sus_nombre1') or '').strip()
        suscriptor.sus_nombre2 = (data.get('sus_nombre2') or '').strip()
        suscriptor.sus_apellido1 = (data.get('sus_apellido1') or '').strip()
        suscriptor.sus_apellido2 = (data.get('sus_apellido2') or '').strip()
        suscriptor.sus_nombre_social = (data.get('sus_nombre_social') or '').strip()

        partes = [suscriptor.sus_nombre1, suscriptor.sus_nombre2, suscriptor.sus_apellido1, suscriptor.sus_apellido2]
        iniciales_auto = "".join([p[0].upper() for p in partes if p])[:5]
        suscriptor.sus_iniciales = (data.get('sus_iniciales') or iniciales_auto).strip().upper()[:5]

        suscriptor.fecha_actualizacion = timezone.now()
        suscriptor.save()
        return JsonResponse({
            'status': 'ok',
            'mensaje': 'Datos del suscriptor actualizados con éxito.',
            'sus_iniciales': suscriptor.sus_iniciales
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': f'Error al actualizar: {str(e)}'}, status=500)


@csrf_exempt
def actualizar_empresa_suscriptor(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')
        suscriptor = Suscriptor.objects.filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'error', 'mensaje': 'Suscriptor no encontrado.'}, status=404)

        autorizado, motivo = validar_autorizacion_suscriptor(request, suscriptor)
        if not autorizado:
            return JsonResponse({'status': 'error', 'mensaje': motivo}, status=403)

        rut = _formatear_rut(data.get('emp_rut'))
        if not rut:
            return JsonResponse({'status': 'error', 'mensaje': 'El RUT no es válido. Revisa su longitud y dígito verificador.'}, status=400)

        telefono = (data.get('emp_contacto_telefono') or '').strip()
        if telefono and (
            len(telefono) > 20 or
            len(telefono) < 7 or
            not re.fullmatch(r'\+?[0-9() .-]+', telefono)
        ):
            return JsonResponse({
                'status': 'error',
                'mensaje': 'El teléfono debe tener entre 7 y 20 caracteres y usar solo números, espacios y + ( ) . -.'
            }, status=400)

        empresa_existente = _buscar_empresa_por_rut(rut)

        # Si la empresa ya existe, validar si es cuenta asociada (no dueña)
        if empresa_existente:
            primer_suscriptor = Suscriptor.objects.filter(sus_rut_empresa=empresa_existente).order_by('fecha_registro').first()
            if primer_suscriptor and primer_suscriptor.id_suscriptor != suscriptor.id_suscriptor:
                # La cuenta secundaria solo se vincula a la empresa existente sin alterar sus datos
                suscriptor.sus_rut_empresa = empresa_existente
                suscriptor.save(update_fields=['sus_rut_empresa'])
                return JsonResponse({
                    'status': 'ok',
                    'es_dueno': False,
                    'mensaje': f'Te has vinculado a la empresa. Administrada por {empresa_existente.emp_contacto_correo}. Solo lectura.'
                })

        codigo_comuna_raw = (data.get('emp_codigo_comuna') or '').strip()
        codigo_comuna = _normalizar_codigo_comuna(codigo_comuna_raw)

        comuna_guardada_raw = getattr(empresa_existente, 'emp_codigo_comuna_id', None) if empresa_existente else None
        if not comuna_guardada_raw and empresa_existente and hasattr(empresa_existente, 'emp_codigo_comuna'):
            c_inst = empresa_existente.emp_codigo_comuna
            comuna_guardada_raw = getattr(c_inst, 'codigo_comuna', None) if c_inst else None
        comuna_guardada = _normalizar_codigo_comuna(comuna_guardada_raw) if comuna_guardada_raw else ''

        if comuna_guardada and codigo_comuna and codigo_comuna != comuna_guardada:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'La comuna de una empresa registrada no se puede modificar.'
            }, status=400)

        emp_comuna_final = comuna_guardada or codigo_comuna or None
        if emp_comuna_final:
            emp_comuna_final = str(emp_comuna_final)[:5]
            if not Comuna.objects.filter(codigo_comuna=emp_comuna_final).exists():
                return JsonResponse({
                    'status': 'error',
                    'mensaje': f'La comuna ingresada ("{codigo_comuna_raw}") no es válida. Selecciona una comuna oficial.'
                }, status=400)

        # Si es el primer usuario o la cuenta administradora oficial, guarda y actualiza los campos permitidos
        empresa, _ = Empresa.objects.update_or_create(
            emp_rut=empresa_existente.emp_rut if empresa_existente else rut,
            defaults={
                'emp_razon_social': (data.get('emp_razon_social') or '').strip()[:200],
                'emp_nombre_fantasia': (data.get('emp_nombre_fantasia') or '').strip()[:200],
                'emp_contacto_nombre': (data.get('emp_contacto_nombre') or '').strip()[:100],
                'emp_iniciales': (data.get('emp_iniciales') or '').strip()[:20],
                'emp_contacto_correo': (data.get('emp_contacto_correo') or '').strip()[:254],
                'emp_direccion': (data.get('emp_direccion') or '').strip()[:300],
                'emp_codigo_comuna_id': emp_comuna_final,
                'emp_contacto_telefono': telefono[:20],
            }
        )

        suscriptor.sus_rut_empresa = empresa
        suscriptor.save(update_fields=['sus_rut_empresa'])
        return JsonResponse({
            'status': 'ok',
            'es_dueno': True,
            'mensaje': 'Datos de la empresa actualizados correctamente.'
        })
    except DataError as de:
        logger.warning(f'[SmartBids] Se rechazaron datos que exceden el tamaño de las columnas de empresa: {str(de)}')
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Uno de los campos supera la longitud permitida por la base de datos: {str(de)}'
        }, status=400)
    except Exception as e:
        logger.error(f"[SmartBids] Error al actualizar empresa: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error al actualizar empresa: {str(e)}'}, status=500)


@csrf_exempt
def buscar_empresa_por_rut(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        rut_raw = _formatear_rut(data.get('rut'))

        if not rut_raw:
            return JsonResponse({'status': 'error', 'mensaje': 'Debe ingresar un RUT válido con su dígito verificador.'}, status=400)

        rut_normalizado = _normalizar_rut(rut_raw)

        # 1. Comprobar si ya existe en la tabla core.empresa
        emp_existente = _buscar_empresa_por_rut(rut_raw)

        if emp_existente:
            cod_c_raw = getattr(emp_existente, 'emp_codigo_comuna_id', None)
            if not cod_c_raw and hasattr(emp_existente, 'emp_codigo_comuna'):
                c_inst = emp_existente.emp_codigo_comuna
                cod_c_raw = getattr(c_inst, 'codigo_comuna', '') if c_inst else ''
            cod_c = _normalizar_codigo_comuna(cod_c_raw)
            com_obj = Comuna.objects.filter(codigo_comuna=cod_c).first() if cod_c else None

            return JsonResponse({
                'status': 'ok',
                'ya_registrada': True,
                'correo_dueno': emp_existente.emp_contacto_correo,
                'datos': {
                    'emp_rut': emp_existente.emp_rut,
                    'emp_razon_social': emp_existente.emp_razon_social,
                    'emp_nombre_fantasia': emp_existente.emp_nombre_fantasia,
                    'emp_direccion': emp_existente.emp_direccion,
                    'emp_codigo_comuna': cod_c,
                    'emp_nombre_comuna': com_obj.nombre_comuna if com_obj else '',
                    'emp_contacto_nombre': emp_existente.emp_contacto_nombre,
                    'emp_contacto_correo': emp_existente.emp_contacto_correo,
                    'emp_contacto_telefono': emp_existente.emp_contacto_telefono,
                    'emp_iniciales': emp_existente.emp_iniciales
                },
                'mensaje': 'Empresa existente encontrada en la base de datos.'
            })

        # 2. Búsqueda de respaldo en catálogo de Proveedores
        filtro = (
            Q(prov_rut__iexact=rut_raw) |
            Q(prov_rut__iexact=rut_normalizado) |
            Q(prov_rut__icontains=rut_normalizado)
        )

        cuerpo = rut_normalizado[:-1]
        if len(cuerpo) >= 5:
            filtro |= Q(prov_rut__icontains=cuerpo)

        proveedor = Proveedor.objects.filter(filtro).first()

        if not proveedor:
            return JsonResponse({
                'status': 'not_found',
                'mensaje': 'Empresa no encontrada en los registros de proveedores. Puedes ingresar los datos manualmente.'
            })

        codigo_comuna = ''
        nombre_comuna = ''
        if proveedor.prov_codigo_comuna:
            c_val = getattr(proveedor, 'prov_codigo_comuna_id', None)
            if not c_val:
                c_obj = proveedor.prov_codigo_comuna
                c_val = getattr(c_obj, 'codigo_comuna', '') if c_obj else ''
            codigo_comuna = _normalizar_codigo_comuna(c_val)
            com_obj = Comuna.objects.filter(codigo_comuna=codigo_comuna).first() if codigo_comuna else None
            if com_obj:
                nombre_comuna = com_obj.nombre_comuna

        datos_empresa = {
            'emp_rut': proveedor.prov_rut or rut_raw,
            'emp_razon_social': (proveedor.prov_razon_social or '').strip(),
            'emp_nombre_fantasia': (proveedor.prov_nombre or '').strip(),
            'emp_direccion': (proveedor.prov_direccion or '').strip(),
            'emp_codigo_comuna': codigo_comuna,
            'emp_nombre_comuna': nombre_comuna,
            'emp_contacto_correo': '',
            'emp_contacto_telefono': '',
            'emp_iniciales': ''
        }

        return JsonResponse({
            'status': 'ok',
            'ya_registrada': False,
            'datos': datos_empresa,
            'mensaje': 'Datos de la empresa obtenidos con éxito.'
        })

    except Exception as e:
        logger.error(f"[SmartBids] Error al buscar empresa por RUT: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@csrf_exempt
def desvincular_empresa_suscriptor(request):
    """Permite al suscriptor autenticado desvincular su cuenta de la empresa asociada actualmente."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        uid = data.get('uid')

        if not uid:
            return JsonResponse({'status': 'error', 'mensaje': 'No se recibió la identidad del suscriptor (UID requerido).'}, status=400)

        suscriptor = Suscriptor.objects.select_related('sus_rut_empresa').filter(firebase_uid=uid).first()
        if not suscriptor:
            return JsonResponse({'status': 'error', 'mensaje': 'Cuenta de suscriptor no encontrada.'}, status=404)

        autorizado, motivo = validar_autorizacion_suscriptor(request, suscriptor)
        if not autorizado:
            return JsonResponse({'status': 'error', 'mensaje': motivo}, status=403)

        empresa_actual = suscriptor.sus_rut_empresa
        if not empresa_actual:
            return JsonResponse({'status': 'error', 'mensaje': 'El suscriptor no se encuentra vinculado a ninguna empresa actualmente.'}, status=400)

        nombre_empresa = empresa_actual.emp_nombre_fantasia or empresa_actual.emp_razon_social or empresa_actual.emp_rut

        # Desvincular al suscriptor de la empresa
        suscriptor.sus_rut_empresa = None
        suscriptor.fecha_actualizacion = timezone.now()
        suscriptor.save(update_fields=['sus_rut_empresa', 'fecha_actualizacion'])

        logger.info(f"[SmartBids] Suscriptor {suscriptor.id_suscriptor} desvinculado de empresa {empresa_actual.emp_rut}")

        return JsonResponse({
            'status': 'ok',
            'mensaje': f'Se ha desvinculado exitosamente de la empresa {nombre_empresa}.'
        })

    except Exception as e:
        logger.error(f"[SmartBids] Error al desvincular empresa: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error interno al procesar la desvinculación: {str(e)}'}, status=500)