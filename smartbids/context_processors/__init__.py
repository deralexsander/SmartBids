import logging
import re
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
# Importación correcta según tu estructura de carpetas
from smartbids.models.config import InfoContacto, obtener_correos_sistema

logger = logging.getLogger(__name__)
EMAIL_CONTACTO_RESPALDO = 'contacto@chileavanza.cl'


def extraer_correo_contacto(texto):
    for correo in re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', texto or ''):
        try:
            validate_email(correo)
            return correo
        except ValidationError:
            continue
    correos = obtener_correos_sistema()
    return correos.get('email_contacto', EMAIL_CONTACTO_RESPALDO)


def extraer_razon_social(texto):
    """
    Extrae dinámicamente la Razón Social desde líneas como 'Razón Social: no informada' o 'Razon Social: ...'
    """
    if not texto:
        return 'no informada'
    match = re.search(r'(?:Razón|Razon)\s*Social\s*:\s*(.+)', texto, re.IGNORECASE)
    if match:
        val = match.group(1).strip()
        if val:
            return val
    return 'no informada'


def extraer_rut_empresa(texto):
    """
    Extrae dinámicamente el RUT institucional desde líneas como 'RUT: 00000000-5'
    """
    if not texto:
        return '00000000-5'
    match = re.search(r'RUT\s*:\s*(.+)', texto, re.IGNORECASE)
    if match:
        val = match.group(1).strip()
        if val:
            return val
    return '00000000-5'


def footer_info_context(request):
    """
    Inyecta la información institucional y de contacto del footer en todos los templates.
    """
    correos = obtener_correos_sistema()
    lineas_contacto = []
    empresas_list = []
    contacto_email = correos.get('email_contacto', EMAIL_CONTACTO_RESPALDO)
    razon_social = 'no informada'
    rut = '00000000-5'

    try:
        info = InfoContacto.objects.first()
        if info:
            contacto_email = extraer_correo_contacto(info.contacto_texto)
            razon_social = extraer_razon_social(info.contacto_texto)
            rut = extraer_rut_empresa(info.contacto_texto)
            if info.contacto_texto:
                lineas_contacto = [
                    linea.strip() 
                    for linea in info.contacto_texto.splitlines() 
                    if linea.strip()
                ]
            if info.empresas_enlaces:
                empresas_list = info.empresas_enlaces
    except Exception as e:
        logger.warning(f"[Footer Context Processor] No se pudo obtener info de contacto: {e}")

    return {
        'footer_contacto_lineas': lineas_contacto,
        'footer_empresas': empresas_list,
        'contacto_email': contacto_email,
        'razon_social': razon_social,
        'rut': rut,
        'app_version': getattr(settings, 'APP_VERSION', 'v1.0.0'),
    }