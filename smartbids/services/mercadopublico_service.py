import html
import logging
import re
from urllib.parse import urljoin

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def obtener_datos_externos_licitacion(lic_codigo: str, url_licitacion: str = None) -> dict:
    """
    Obtiene datos complementarios directamente desde la ficha oficial de Mercado Público
    cuando no están presentes en la base de datos (descripción faltante, enlaces de adjuntos,
    foro de preguntas y listado de preguntas/respuestas).
    Los resultados se guardan en caché para optimizar las consultas subsecuentes.
    """
    codigo_limpio = (lic_codigo or '').strip()
    if not codigo_limpio:
        return {
            'descripcion': None,
            'url_adjuntos': None,
            'url_preguntas': None,
            'preguntas': [],
            'direccion': None,
        }

    cache_key = f'mp_ext_data_{codigo_limpio}'
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    resultado = {
        'descripcion': None,
        'url_adjuntos': None,
        'url_preguntas': None,
        'preguntas': [],
        'direccion': None,
    }

    url_base = 'https://www.mercadopublico.cl/Procurement/Modules/RFB/'
    # Si viene una URL específica de RFB en la licitación la respetamos, de lo contrario usamos DetailsAcquisition directa
    if url_licitacion and 'DetailsAcquisition.aspx' in url_licitacion:
        url_ficha = url_licitacion.strip()
    else:
        url_ficha = f'https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={codigo_limpio}'

    headers = {'User-Agent': USER_AGENT}

    try:
        r = requests.get(url_ficha, timeout=6, headers=headers)
        if r.status_code == 200:
            text = html.unescape(r.text)

            # 1. Descripción del Proceso (fallback si no está en la BD)
            m_desc = re.search(r'id=\"[^\"]*lblFicha1Descripcion\"[^>]*>(.*?)</span>', text, re.IGNORECASE | re.DOTALL)
            if not m_desc:
                m_desc = re.search(r'id=\"[^\"]*Descripcion[^\"]*\"[^>]*>(.*?)</span>', text, re.IGNORECASE | re.DOTALL)
            if m_desc:
                desc_raw = re.sub(r'<[^>]+>', ' ', m_desc.group(1))
                desc_limpia = ' '.join(desc_raw.split()).strip()
                if desc_limpia:
                    resultado['descripcion'] = desc_limpia

            # 2. Dirección del organismo (fallback si no está en la BD)
            m_dir = re.search(r'id=\"[^\"]*lblFicha2Direccion\"[^>]*>(.*?)</span>', text, re.IGNORECASE | re.DOTALL)
            if m_dir:
                dir_raw = re.sub(r'<[^>]+>', ' ', m_dir.group(1))
                dir_limpia = ' '.join(dir_raw.split()).strip()
                if dir_limpia:
                    resultado['direccion'] = dir_limpia

            # 3. Enlace oficial de Ver Adjuntos
            m_adj = re.search(r'open\(\'([^\']*ViewAttachment[^\']*)\'', text)
            if not m_adj:
                m_adj = re.search(r'href=[\'\"]([^\'\"]*ViewAttachment[^\'\"]*)[\'\"]', text)
            if m_adj:
                resultado['url_adjuntos'] = urljoin(url_base, m_adj.group(1))

            # 4. Enlace oficial del foro de preguntas
            m_preg = re.search(r'id=\"imgPreguntasLicitacion\"[^>]+href=\"([^\"]+)\"', text)
            if not m_preg:
                m_preg = re.search(r'href=[\'\"]([^\'\"]*PreguntasRespuestas[^\'\"]*)[\'\"]', text)
            if m_preg:
                url_preguntas = urljoin(url_base, m_preg.group(1))
                resultado['url_preguntas'] = url_preguntas

                # 5. Extraer preguntas y respuestas vía servicesPub
                try:
                    r_preg = requests.get(url_preguntas, timeout=5, headers=headers)
                    if r_preg.status_code == 200:
                        m_rbf = re.search(r'id=\"h_intRBFCode\"\s+value=\"([^\"]+)\"', r_preg.text)
                        if m_rbf:
                            rbf_code = m_rbf.group(1)
                            service_url = urljoin(url_preguntas, '../servicesPub.aspx')
                            r_serv = requests.post(
                                service_url,
                                data={'opt': 101, 'RFBCode': rbf_code},
                                timeout=5,
                                headers=headers,
                            )
                            if r_serv.status_code == 200:
                                raw_preguntas = r_serv.json()
                                if isinstance(raw_preguntas, list):
                                    for item in raw_preguntas:
                                        resp_obj = item.get('RespuestaPublicada') or {}
                                        resultado['preguntas'].append({
                                            'numero': item.get('Numero') or item.get('idP'),
                                            'pregunta': (item.get('Descripcion') or '').strip(),
                                            'fecha_pregunta': item.get('FechaHora'),
                                            'respuesta': (resp_obj.get('Descripcion') or '').strip(),
                                            'fecha_respuesta': resp_obj.get('FechaHora'),
                                        })
                except Exception as ex_preg:
                    logger.warning('Error extrayendo preguntas de Mercado Público para %s: %s', codigo_limpio, ex_preg)

        # Cachear durante 2 horas (7200 segundos)
        cache.set(cache_key, resultado, 7200)

    except Exception as e:
        logger.error('Error consultando ficha externa de Mercado Público para %s: %s', codigo_limpio, e)

    return resultado
