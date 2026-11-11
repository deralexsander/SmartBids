"""
Módulo de utilidades para el envío de notificaciones y correos institucionales de SmartBids.
"""
from smartbids.models.config import notificar_cambio_rol_suscriptor, notificar_accion_entre_administradores

__all__ = ['notificar_cambio_rol_suscriptor', 'notificar_accion_entre_administradores']
