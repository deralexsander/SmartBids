import json
import logging
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import DatabaseError
from django.db.models import Q

from .models import Suscriptor, Empresa, Preferencia, EstadoSuscriptor
from .models.catalog import Comuna, Organismo, Producto, Region, Provincia, Sector, Proveedor
from .models.procurement import UnidadCompra

logger = logging.getLogger(__name__)


@csrf_exempt
def catalogos_preferencias(request):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    tipo = request.GET.get('tipo', '').strip()
    query = request.GET.get('q', '').strip()
    
    try:
        limite = min(int(request.GET.get('limit', 40) or 40), 100)
    except ValueError:
        limite = 40

    if tipo == 'territorio':
        regiones = list(Region.objects.values('codigo_region', 'nombre_region').order_by('codigo_region'))
        provincias = list(Provincia.objects.values('codigo_provincia', 'nombre_provincia', 'codigo_region_id').order_by('nombre_provincia'))
        comunas = list(Comuna.objects.values('codigo_comuna', 'nombre_comuna', 'codigo_provincia_id').order_by('nombre_comuna'))
        return JsonResponse({'regiones': regiones, 'provincias': provincias, 'comunas': comunas})

    if tipo == 'comuna':
        resultados = Comuna.objects.filter(nombre_comuna__icontains=query).values(
            'codigo_comuna', 'nombre_comuna'
        )[:limite]
    elif tipo == 'producto':
        resultados = Producto.objects.filter(descripcion__icontains=query).values(
            'codigo_producto', 'descripcion'
        )[:limite]
    elif tipo == 'unidad_compra':
        resultados = UnidadCompra.objects.filter(ucom_descripcion__icontains=query).values(
            'codigo_unidad_compra', 'ucom_descripcion'
        )[:limite]
    elif tipo == 'organismo':
        resultados = Organismo.objects.filter(org_nombre__icontains=query).values(
            'codigo_organismo', 'org_nombre', 'org_codigo_sector_id'
        )[:limite]
    elif tipo == 'sector':
        resultados = Sector.objects.filter(nombre_sector__icontains=query).values(
            'codigo_sector', 'nombre_sector'
        )[:limite]
    else:
        return JsonResponse({'status': 'error', 'mensaje': 'Catálogo no válido.'}, status=400)

    return JsonResponse({'resultados': list(resultados)})


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
        productos_detalle = [{'code': cod, 'label': mapa_prods.get(cod, cod)} for cod in raw_prods]

        raw_ucom = to_list(pref.pref_ucom) if pref else []
        ucom_ids = [int(x) for x in raw_ucom if str(x).isdigit()]
        mapa_ucom = {
            str(u['codigo_unidad_compra']): u['ucom_descripcion']
            for u in UnidadCompra.objects.filter(codigo_unidad_compra__in=ucom_ids).values('codigo_unidad_compra', 'ucom_descripcion')
        }
        ucom_detalle = [{'code': str(cod), 'label': mapa_ucom.get(str(cod), str(cod))} for cod in raw_ucom]

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
                'empresa': {
                    'emp_rut': emp.emp_rut if emp else '',
                    'emp_fantasia': emp.emp_nombre_fantasia if emp else '',
                    'emp_razon_social': emp.emp_razon_social if emp else '',
                    'emp_contacto_nombre': getattr(emp, 'emp_contacto_nombre', '') if emp else '',
                    'emp_contacto_correo': emp.emp_contacto_correo if emp else '',
                    'emp_iniciales': emp.emp_iniciales if emp else '',
                    'emp_contacto_telefono': emp.emp_contacto_telefono if emp else '',
                    'emp_codigo_comuna': getattr(emp, 'emp_codigo_comuna_id', getattr(emp, 'emp_codigo_comuna', '')) if emp else '',
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
    """Guarda los códigos de las preferencias en core.preferencia en PostgreSQL."""
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

        palabras = [str(w).strip()[:50] for w in data.get('pref_palabras_claves', []) if str(w).strip()]

        pref, _ = Preferencia.objects.get_or_create(id_suscriptor=suscriptor)
        pref.pref_comunas = comunas
        pref.pref_productos = productos
        pref.pref_tipo_licitacion = tipo_lic
        pref.pref_ucom = ucom
        pref.pref_palabras_claves = palabras
        pref.save()

        suscriptor.fecha_actualizacion = timezone.now()
        suscriptor.save(update_fields=['fecha_actualizacion'])

        return JsonResponse({
            'status': 'ok',
            'mensaje': 'Preferencias guardadas con éxito.'
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
        
        iniciales = (data.get('sus_iniciales') or '').strip()
        if not iniciales and suscriptor.sus_nombre1 and suscriptor.sus_apellido1:
            iniciales = (suscriptor.sus_nombre1[0] + suscriptor.sus_apellido1[0]).upper()
        suscriptor.sus_iniciales = iniciales[:5]
        
        suscriptor.fecha_actualizacion = timezone.now()
        suscriptor.save()
        return JsonResponse({'status': 'ok', 'mensaje': 'Datos del suscriptor actualizados con éxito.'})
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
        return JsonResponse({'status': 'ok', 'mensaje': 'Datos de la empresa actualizados correctamente.'})
    except Exception as e:
        logger.error(f"[SmartBids] Error al actualizar empresa: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error al actualizar empresa: {str(e)}'}, status=500)


@csrf_exempt
def buscar_empresa_por_rut(request):
    """
    Busca la empresa en catalog.proveedor por RUT considerando formatos
    con o sin puntos y con o sin guion.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        rut_raw = (data.get('rut') or '').strip()

        if not rut_raw:
            return JsonResponse({'status': 'error', 'mensaje': 'Debe ingresar un RUT.'}, status=400)

        rut_sin_puntos = rut_raw.replace('.', '').strip()

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
        if proveedor.prov_codigo_comuna:
            codigo_comuna = getattr(proveedor.prov_codigo_comuna, 'codigo_comuna', '') or ''

        datos_empresa = {
            'emp_rut': proveedor.prov_rut or rut_raw,
            'emp_razon_social': (proveedor.prov_razon_social or '').strip(),
            'emp_nombre_fantasia': (proveedor.prov_nombre or '').strip(),
            'emp_direccion': (proveedor.prov_direccion or '').strip(),
            'emp_codigo_comuna': codigo_comuna,
            'emp_contacto_correo': '',
            'emp_contacto_telefono': '',
            'emp_iniciales': ''
        }

        return JsonResponse({
            'status': 'ok',
            'datos': datos_empresa,
            'mensaje': 'Datos de la empresa obtenidos con éxito.'
        })

    except Exception as e:
        logger.error(f"[SmartBids] Error al buscar empresa por RUT: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)