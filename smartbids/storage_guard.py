import os
import logging
from django.db import connection
from django.http import HttpResponseServerError

logger = logging.getLogger(__name__)

def obtener_limite_bytes():
    """
    Lee la variable MAX_STORAGE_GB del entorno (por defecto 0.9 GB para discos de 1 GB).
    Deja automáticamente un margen seguro para no tocar el tope del hosting.
    """
    try:
        limite_gb = float(os.getenv('MAX_STORAGE_GB', '0.9'))
    except ValueError:
        limite_gb = 0.9

    return int(limite_gb * 1024 * 1024 * 1024)

class StorageSafetyMiddleware:
    """
    Bloquea escrituras (POST, PUT, PATCH) si la base de datos supera la cuota
    definida en MAX_STORAGE_GB para evitar cobros adicionales.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_database_size(current_database());")
                    tamano_actual = cursor.fetchone()[0]

                limite_seguridad = obtener_limite_bytes()

                if tamano_actual >= limite_seguridad:
                    logger.critical(
                        f"[STORAGE KILL-SWITCH] Tamaño BD ({tamano_actual} bytes) superó "
                        f"el límite de seguridad ({limite_seguridad} bytes). Rechazando escritura."
                    )
                    return HttpResponseServerError(
                        "<h1>503 Servicio Temporalmente No Disponible</h1>"
                        "<p>El sistema ha alcanzado el límite de almacenamiento de seguridad. "
                        "No se guardarán nuevos registros para proteger la plataforma.</p>"
                    )
            except Exception as e:
                logger.error(f"Error verificando tamaño de base de datos: {e}")

        return self.get_response(request)