import logging
import re
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
# Importación correcta según tu estructura de carpetas
from smartbids.models.config import InfoContacto

logger = logging.getLogger(__name__)
EMAIL_CONTACTO_RESPALDO = 'contacto@chileavanza.cl'


def extraer_correo_contacto(texto):
    for correo in re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', texto or ''):
        try:
            validate_email(correo)
            return correo
        except ValidationError:
            continue
    return EMAIL_CONTACTO_RESPALDO

def footer_info_context(request):
    """
    Inyecta la información institucional y de contacto del footer en todos los templates.
    """
    lineas_contacto = []
    empresas_list = []
    contacto_email = EMAIL_CONTACTO_RESPALDO

    try:
        info = InfoContacto.objects.first()
        if info:
            contacto_email = extraer_correo_contacto(info.contacto_texto)
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
    }