import json
import logging
import re
import difflib
import unicodedata
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import DatabaseError
from django.db.models import Q

from .models import Suscriptor, Empresa, Preferencia, EstadoSuscriptor
from .models.catalog import Comuna, Organismo, Producto, Region, Provincia, Sector, Proveedor
from .models.procurement import UnidadCompra

logger = logging.getLogger(__name__)

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

NOMBRES_SEGMENTOS_ONU = {
    '10': 'Material Vivo Animal y Vegetal',
    '11': 'Materiales de Minerales y Tejidos no Comestibles',
    '12': 'Productos Químicos y Gases Químicos',
    '13': 'Resina, Caucho y Espuma',
    '14': 'Materiales y Productos de Papel',
    '15': 'Combustibles, Lubricantes y Materiales Anticorrosivos',
    '20': 'Maquinaria y Accesorios de Minería y Perforación',
    '21': 'Maquinaria y Accesorios para Agricultura y Pesca',
    '22': 'Maquinaria pesada de Construcción y Edificación',
    '23': 'Maquinaria de Procesamiento Industrial',
    '24': 'Empaque, Envases y Contenedores',
    '25': 'Vehículos Comerciales, Militares y Privados',
    '26': 'Sistemas de Potencia y Componentes Eléctricos',
    '27': 'Herramientas y Maquinaria General',
    '30': 'Estructuras, Edificación y Materiales de Construcción',
    '31': 'Artículos de Fabricación y Componentes',
    '32': 'Componentes Electrónicos',
    '39': 'Iluminación y Componentes Eléctricos',
    '40': 'Distribución y Acondicionamiento de Fluidos',
    '41': 'Equipamiento de Laboratorio y Científico',
    '42': 'Equipos y Suministros Médicos',
    '43': 'Tecnología de la Información, Telecomunicaciones y Software',
    '44': 'Equipos y Suministros de Oficina',
    '45': 'Equipamiento para Artes, Imprenta y Fotografía',
    '46': 'Seguridad, Vigilancia y Primeros Auxilios',
    '47': 'Limpieza y Eliminación de Residuos',
    '50': 'Alimentos, Bebidas y Tabaco',
    '51': 'Medicamentos y Productos Farmacéuticos',
    '52': 'Muebles, Mobiliario y Accesorios Domésticos',
    '53': 'Ropa, Calzado y Equipaje',
    '55': 'Publicaciones, Medios Impresos y Audiovisuales',
    '56': 'Construcciones prefabricadas',
    '60': 'Instrumentos Musicales, Juegos y Deportes',
    '70': 'Servicios de Recursos Vivos (Agricultura y Pesca)',
    '71': 'Servicios de Minería, Petróleo y Gas',
    '72': 'Servicios de Construcción y Mantenimiento',
    '73': 'Servicios de Producción y Fabricación Industrial',
    '76': 'Servicios de Limpieza, Descontaminación y Residuos',
    '77': 'Servicios de Medio Ambiente',
    '78': 'Servicios de Transporte, Correo y Almacenamiento',
    '80': 'Servicios de Gestión, Administración y Consultoría',
    '81': 'Servicios Profesionales de Ingeniería e Investigación',
    '82': 'Servicios Editoriales, Diseño y Gráficos',
    '83': 'Servicios Públicos y de Obras Públicas',
    '84': 'Servicios Financieros, Seguros y Contables',
    '85': 'Servicios Sanitarios y de Salud Humana',
    '86': 'Servicios Educativos y de Capacitación',
    '90': 'Servicios de Viajes, Alojamiento y Banquetes',
    '91': 'Servicios Personales y Domésticos',
    '92': 'Servicios de Seguridad y Defensa',
    '93': 'Servicios Políticos, Cívicos y Gubernamentales',
    '94': 'Organizaciones y Clubes',
    '95': 'Terrenos, Bienes Inmuebles y Estructuras',
}


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
            query_base = Producto.objects.exclude(descripcion__isnull=True).exclude(descripcion__exact='')

            if q_filtro:
                query_base = query_base.filter(
                    Q(descripcion__icontains=q_filtro) | Q(codigo_producto__icontains=q_filtro)
                )[:250]
            else:
                query_base = query_base.order_by('codigo_producto')

            prods = list(query_base.values('codigo_producto', 'descripcion'))

            rubros_map = {}
            for p in prods:
                cod = str(p['codigo_producto']).strip()
                desc_raw = str(p['descripcion'] or '').replace('\r', ' ').replace('\n', ' ')
                desc = re.sub(r'\s+', ' ', desc_raw).strip()

                if not desc or desc in ['1°', '1a S', '1era', '1.1']:
                    desc = f"Producto ONU {cod}"

                seg_code = cod[:2] if len(cod) >= 2 else '00'
                nombre_seg = NOMBRES_SEGMENTOS_ONU.get(seg_code, f"Segmento ONU {seg_code}")

                if seg_code not in rubros_map:
                    rubros_map[seg_code] = {
                        'codigo_rubro': seg_code,
                        'nombre_rubro': f"{seg_code} – {nombre_seg}",
                        'productos': []
                    }
                rubros_map[seg_code]['productos'].append({
                    'codigo_producto': cod,
                    'descripcion': desc
                })

            rubros_list = sorted(list(rubros_map.values()), key=lambda r: r['codigo_rubro'])
            return JsonResponse({'status': 'ok', 'rubros': rubros_list})
        except Exception as e:
            logger.error(f"[SmartBids] Error al generar árbol de productos: {str(e)}")
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

    if tipo == 'ucom_arbol':
        try:
            q_filtro = request.GET.get('q', '').strip()

            ucom_cols = [f.name for f in UnidadCompra._meta.concrete_fields]
            campo_org_ucom = None
            for c in ['codigo_organismo', 'codigo_organismo_id', 'org_codigo', 'ucom_codigo_organismo']:
                if c in ucom_cols:
                    campo_org_ucom = c
                    break

            campos_ucom = ['codigo_unidad_compra', 'ucom_descripcion']
            if campo_org_ucom:
                campos_ucom.append(campo_org_ucom)

            ucom_qs = UnidadCompra.objects.all()
            if q_filtro:
                ucom_qs = ucom_qs.filter(ucom_descripcion__icontains=q_filtro)[:350]
            else:
                ucom_qs = ucom_qs.order_by('codigo_unidad_compra')[:500]

            ucom_list = list(ucom_qs.values(*campos_ucom))

            org_cols = [f.name for f in Organismo._meta.concrete_fields]
            campo_sec_org = None
            for c in ['org_codigo_sector', 'org_codigo_sector_id', 'codigo_sector', 'codigo_sector_id']:
                if c in org_cols:
                    campo_sec_org = c
                    break

            campos_org = ['codigo_organismo', 'org_nombre']
            if campo_sec_org:
                campos_org.append(campo_sec_org)

            org_map = {}
            for o in Organismo.objects.values(*campos_org):
                cod_str = str(o['codigo_organismo']).strip()
                sec_val = o.get(campo_sec_org)
                sec_val_str = str(sec_val).strip() if sec_val is not None else '0'
                org_map[cod_str] = {
                    'codigo_organismo': cod_str,
                    'org_nombre': (o.get('org_nombre') or f"Organismo {cod_str}").strip(),
                    'codigo_sector': sec_val_str
                }

            sec_map = {}
            for s in Sector.objects.values('codigo_sector', 'nombre_sector'):
                sec_map[str(s['codigo_sector']).strip()] = (s.get('nombre_sector') or '').strip()

            sectores_dict = {}

            if not ucom_list:
                for org_id, org_info in org_map.items():
                    sec_key = org_info['codigo_sector']
                    sec_nombre = sec_map.get(sec_key) or ("Organismos Centralizados" if sec_key == '0' else f"Sector {sec_key}")
                    if sec_key not in sectores_dict:
                        sectores_dict[sec_key] = {
                            'codigo_sector': sec_key,
                            'nombre_sector': sec_nombre,
                            'organismos_map': {}
                        }
                    sectores_dict[sec_key]['organismos_map'][org_id] = {
                        'codigo_organismo': org_id,
                        'nombre_organismo': org_info['org_nombre'],
                        'unidades': [{
                            'codigo_ucom': org_id,
                            'descripcion': f"{org_info['org_nombre']} (Unidad Central)"
                        }]
                    }
            else:
                for u in ucom_list:
                    cod_ucom = u['codigo_unidad_compra']
                    desc_ucom = (u.get('ucom_descripcion') or f"Unidad {cod_ucom}").strip()
                    org_key = str(u.get(campo_org_ucom) or '0').strip() if campo_org_ucom else '0'

                    org_info = org_map.get(org_key)
                    if org_info:
                        org_nombre = org_info['org_nombre']
                        sec_key = org_info['codigo_sector']
                    else:
                        org_nombre = f"Organismo {org_key}" if org_key != '0' else "Organismos Generales del Estado"
                        sec_key = '0'

                    sec_nombre = sec_map.get(sec_key) or ("Organismos Públicos Centralizados" if sec_key == '0' else f"Sector {sec_key}")

                    if sec_key not in sectores_dict:
                        sectores_dict[sec_key] = {
                            'codigo_sector': sec_key,
                            'nombre_sector': sec_nombre,
                            'organismos_map': {}
                        }

                    orgs_dict = sectores_dict[sec_key]['organismos_map']
                    if org_key not in orgs_dict:
                        orgs_dict[org_key] = {
                            'codigo_organismo': org_key,
                            'nombre_organismo': org_nombre,
                            'unidades': []
                        }

                    orgs_dict[org_key]['unidades'].append({
                        'codigo_ucom': cod_ucom,
                        'descripcion': desc_ucom
                    })

            sectores_final = []
            for sec_data in sectores_dict.values():
                organismos_list = sorted(list(sec_data['organismos_map'].values()), key=lambda o: o['nombre_organismo'])
                sectores_final.append({
                    'codigo_sector': sec_data['codigo_sector'],
                    'nombre_sector': sec_data['nombre_sector'],
                    'organismos': organismos_list
                })

            sectores_final = sorted(sectores_final, key=lambda s: s['nombre_sector'])
            return JsonResponse({'status': 'ok', 'sectores': sectores_final})

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
        mapa_prods = {
            str(p['codigo_producto']).strip(): p['descripcion']
            for p in Producto.objects.filter(codigo_producto__in=raw_prods).values('codigo_producto', 'descripcion')
        }
        productos_detalle = [{'code': cod, 'label': f"{mapa_prods.get(cod, cod)} ({cod})" if cod in mapa_prods else cod} for cod in raw_prods]

        raw_ucom = to_list(pref.pref_ucom) if pref else []
        ucom_ids = [int(x) for x in raw_ucom if str(x).isdigit()]
        mapa_ucom = {
            str(u['codigo_unidad_compra']): u['ucom_descripcion']
            for u in UnidadCompra.objects.filter(codigo_unidad_compra__in=ucom_ids).values('codigo_unidad_compra', 'ucom_descripcion')
        }
        ucom_detalle = [{'code': str(cod), 'label': mapa_ucom.get(str(cod), f"Unidad {cod}")} for cod in raw_ucom]

        nom_comuna_emp = ''
        cod_comuna_emp = ''
        if emp and emp.emp_codigo_comuna:
            cod_comuna_emp = getattr(emp, 'emp_codigo_comuna_id', getattr(emp, 'emp_codigo_comuna', '')) or ''
            comuna_obj = Comuna.objects.filter(codigo_comuna=cod_comuna_emp).first()
            if comuna_obj:
                nom_comuna_emp = comuna_obj.nombre_comuna

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
                'sus_iniciales': suscriptor.sus_iniciales or '',
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

        comunas = [str(c).strip()[:5] for c in data.get('pref_comunas', []) if str(c).strip()]
        productos = [str(p).strip()[:20] for p in data.get('pref_productos', []) if str(p).strip()]
        tipo_lic = [str(t).strip()[:2] for t in data.get('pref_tipo_licitacion', []) if str(t).strip()]

        ucom = []
        for u in data.get('pref_ucom', []):
            try:
                ucom.append(int(u))
            except (ValueError, TypeError):
                continue

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

        pref, _ = Preferencia.objects.get_or_create(id_suscriptor=suscriptor)
        pref.pref_comunas = comunas
        pref.pref_productos = productos
        pref.pref_tipo_licitacion = tipo_lic
        pref.pref_ucom = ucom
        pref.pref_palabras_claves = palabras_limpias
        pref.save()

        suscriptor.fecha_actualizacion = timezone.now()
        suscriptor.save(update_fields=['fecha_actualizacion'])

        return JsonResponse({
            'status': 'ok',
            'mensaje': 'Preferencias guardadas con éxito.',
            'palabras_sanitizadas': palabras_limpias
        })

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

        rut = (data.get('emp_rut') or '').strip()
        if not rut:
            return JsonResponse({'status': 'error', 'mensaje': 'El RUT es obligatorio.'}, status=400)

        empresa_existente = Empresa.objects.filter(emp_rut=rut).first()

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

        # Si es el primer usuario o la cuenta administradora oficial, guarda y actualiza los campos permitidos
        empresa, _ = Empresa.objects.update_or_create(
            emp_rut=rut,
            defaults={
                'emp_razon_social': (data.get('emp_razon_social') or '').strip(),
                'emp_nombre_fantasia': (data.get('emp_nombre_fantasia') or '').strip(),
                'emp_contacto_nombre': (data.get('emp_contacto_nombre') or '').strip(),
                'emp_iniciales': (data.get('emp_iniciales') or '').strip(),
                'emp_contacto_correo': (data.get('emp_contacto_correo') or '').strip(),
                'emp_direccion': (data.get('emp_direccion') or '').strip(),
                'emp_codigo_comuna_id': (data.get('emp_codigo_comuna') or '').strip() or None,
                'emp_contacto_telefono': (data.get('emp_contacto_telefono') or '').strip(),
            }
        )

        suscriptor.sus_rut_empresa = empresa
        suscriptor.save(update_fields=['sus_rut_empresa'])
        return JsonResponse({
            'status': 'ok',
            'es_dueno': True,
            'mensaje': 'Datos de la empresa actualizados correctamente.'
        })
    except Exception as e:
        logger.error(f"[SmartBids] Error al actualizar empresa: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error al actualizar empresa: {str(e)}'}, status=500)


@csrf_exempt
def buscar_empresa_por_rut(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        rut_raw = (data.get('rut') or '').strip()

        if not rut_raw:
            return JsonResponse({'status': 'error', 'mensaje': 'Debe ingresar un RUT.'}, status=400)

        rut_sin_puntos = rut_raw.replace('.', '').strip()

        # 1. Comprobar si ya existe en la tabla core.empresa
        emp_existente = Empresa.objects.filter(emp_rut__iexact=rut_raw).first() or \
                        Empresa.objects.filter(emp_rut__iexact=rut_sin_puntos).first()

        if emp_existente:
            cod_c = getattr(emp_existente, 'emp_codigo_comuna_id', getattr(emp_existente, 'emp_codigo_comuna', '')) or ''
            com_obj = Comuna.objects.filter(codigo_comuna=cod_c).first()

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
            Q(prov_rut__iexact=rut_sin_puntos) |
            Q(prov_rut__icontains=rut_sin_puntos)
        )

        if '-' in rut_sin_puntos:
            cuerpo = rut_sin_puntos.split('-')[0]
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
            codigo_comuna = getattr(proveedor.prov_codigo_comuna, 'codigo_comuna', '') or ''
            nombre_comuna = getattr(proveedor.prov_codigo_comuna, 'nombre_comuna', '') or ''

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