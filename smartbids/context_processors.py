import logging
# Importación correcta según tu estructura de carpetas
from smartbids.models.config import InfoContacto

logger = logging.getLogger(__name__)

def footer_info_context(request):
    """
    Inyecta la información institucional y de contacto del footer en todos los templates.
    """
    lineas_contacto = []
    empresas_list = []

    try:
        info = InfoContacto.objects.first()
        if info:
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
    }