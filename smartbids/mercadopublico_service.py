import html
import logging
import re
from urllib.parse import urljoin

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def obtener_datos_externos_licitacion(lic_codigo: str) -> dict:
    """
    Obtiene los enlaces oficiales de adjuntos, foro de preguntas y el listado de
    preguntas/respuestas directamente desde la ficha de Mercado Público para un lic_codigo.
    Se cachea el resultado para optimizar los tiempos de carga en la ficha.
    """
    if not lic_codigo:
        return {'url_adjuntos': None, 'url_preguntas': None, 'preguntas': []}

    cache_key = f'mp_ext_data_{lic_codigo.strip()}'
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    resultado = {
        'url_adjuntos': None,
        'url_preguntas': None,
        'preguntas': [],
    }

    url_base = 'https://www.mercadopublico.cl/Procurement/Modules/RFB/'
    url_ficha = f'https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={lic_codigo.strip()}'
    headers = {'User-Agent': USER_AGENT}

    try:
        r = requests.get(url_ficha, timeout=6, headers=headers)
        if r.status_code == 200:
            text = html.unescape(r.text)

            # 1. Enlace oficial de Ver Adjuntos
            m_adj = re.search(r'open\(\'([^\']*ViewAttachment[^\']*)\'', text)
            if m_adj:
                resultado['url_adjuntos'] = urljoin(url_base, m_adj.group(1))

            # 2. Enlace oficial del foro de preguntas
            m_preg = re.search(r'id=\"imgPreguntasLicitacion\"[^>]+href=\"([^\"]+)\"', text)
            if m_preg:
                url_preguntas = urljoin(url_base, m_preg.group(1))
                resultado['url_preguntas'] = url_preguntas

                # 3. Extraer preguntas y respuestas vía servicesPub
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
                    logger.warning('Error extrayendo preguntas de Mercado Público para %s: %s', lic_codigo, ex_preg)

        # Cachear durante 2 horas (7200 segundos)
        cache.set(cache_key, resultado, 7200)

    except Exception as e:
        logger.error('Error consultando ficha externa de Mercado Público para %s: %s', lic_codigo, e)

    return resultado
