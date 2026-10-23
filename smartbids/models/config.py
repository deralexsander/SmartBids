from django.db import models


class EstadoSuscriptor(models.Model):
    codigo_estado = models.SmallAutoField(primary_key=True)
    nombre_estado = models.CharField(max_length=30, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = '"config"."estado_suscriptor"'

    def __str__(self):
        return self.nombre_estado
    
    


class Mensajeria(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    ]

    TIPO_ALERTA_CHOICES = [
        ('alerta', 'Alerta'),
        ('precaucion', 'Precaución'),
        ('exito', 'Éxito'),
    ]

    asunto = models.CharField(max_length=200)
    cuerpo = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    tipo_alerta = models.CharField(max_length=20, choices=TIPO_ALERTA_CHOICES, default='alerta')
    creado_el = models.DateTimeField(auto_now_add=True)
    actualizado_el = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = '"config"."mensajeria"'
        verbose_name = 'Mensajería'
        verbose_name_plural = 'Mensajerías'

    def __str__(self):
        return f"[{self.tipo_alerta.upper()}] {self.asunto} ({self.estado})"


class ParametroGlobal(models.Model):
    codigo_parametro = models.SmallIntegerField(primary_key=True)
    nombre_parametro = models.CharField(max_length=50, unique=True)
    valor_parametro = models.SmallIntegerField()
    descripcion = models.CharField(max_length=255)

    class Meta:
        db_table = '"config"."parametros_globales"'
        verbose_name = 'Parámetro Global'
        verbose_name_plural = 'Parámetros Globales'

    def __str__(self):
        return f"{self.nombre_parametro}: {self.valor_parametro}"



class InfoContacto(models.Model):
    # La clave primaria real de la tabla
    id = models.AutoField(primary_key=True)
    
    # Texto libre para los datos de contacto (permite null y blank)
    contacto_texto = models.TextField(
        blank=True,
        null=True,
        verbose_name="Información de Contacto"
    )
    
    # Arreglo JSON para las empresas dinámicas
    empresas_enlaces = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Empresas y Enlaces"
    )

    class Meta:
        managed = True
        db_table = '"config"."info_contacto"'
        verbose_name = "Configuración de Contacto y Enlaces"

    def __str__(self):
        return f"Configuración de Contacto #{self.id}"


import logging
logger = logging.getLogger(__name__)


class AuditoriaAdmin(models.Model):
    id = models.BigAutoField(primary_key=True)
    ejecutor_uid = models.CharField(max_length=128, verbose_name="UID del administrador ejecutor")
    ejecutor_email = models.CharField(max_length=255, verbose_name="Email del administrador ejecutor")
    ejecutor_nombre = models.CharField(max_length=255, blank=True, default='', verbose_name="Nombre del ejecutor")
    afectado_uid = models.CharField(max_length=128, verbose_name="UID del administrador afectado")
    afectado_email = models.CharField(max_length=255, verbose_name="Email del administrador afectado")
    afectado_nombre = models.CharField(max_length=255, blank=True, default='', verbose_name="Nombre del afectado")
    accion = models.CharField(max_length=50, verbose_name="Acción ejecutada")  # 'ELIMINACION', 'CAMBIO_ROL'
    detalle = models.TextField(blank=True, default='', verbose_name="Detalle de la acción")
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y hora")
    ip_origen = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP de origen")

    class Meta:
        db_table = '"config"."auditoria_admin"'
        verbose_name = 'Auditoría de Administradores'
        verbose_name_plural = 'Auditorías de Administradores'
        ordering = ['-creado_el']

    def __str__(self):
        return f"[{self.accion}] {self.ejecutor_email} -> {self.afectado_email} ({self.creado_el})"


class ConfiguracionCorreo(models.Model):
    id = models.AutoField(primary_key=True)
    email_contacto = models.EmailField(max_length=255, default='contacto@chileavanza.cl', verbose_name="Correo de contacto y soporte")
    email_notificaciones = models.EmailField(max_length=255, default='smartbids.qa@chileavanza.cl', verbose_name="Correo emisor de notificaciones")
    nombre_remitente = models.CharField(max_length=100, default='SmartBids', verbose_name="Nombre del remitente")
    email_seguridad_auditoria = models.EmailField(max_length=255, default='contacto@chileavanza.cl', verbose_name="Correo de alertas de seguridad y auditoría")
    actualizado_el = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = '"config"."configuracion_correo"'
        verbose_name = 'Configuración de Correos'
        verbose_name_plural = 'Configuraciones de Correos'

    def __str__(self):
        return f"Configuración de Correos ({self.email_contacto})"


def obtener_correos_sistema():
    """
    Retorna la configuración de correos activa del sistema.
    Usa la base de datos si está disponible o memoria caché/fallbacks seguros.
    """
    try:
        cfg = ConfiguracionCorreo.objects.first()
        if cfg:
            return {
                'email_contacto': cfg.email_contacto or 'contacto@chileavanza.cl',
                'email_notificaciones': cfg.email_notificaciones or 'smartbids.qa@chileavanza.cl',
                'nombre_remitente': cfg.nombre_remitente or 'SmartBids',
                'email_seguridad_auditoria': cfg.email_seguridad_auditoria or 'contacto@chileavanza.cl',
            }
    except Exception:
        pass

    return {
        'email_contacto': 'contacto@chileavanza.cl',
        'email_notificaciones': 'smartbids.qa@chileavanza.cl',
        'nombre_remitente': 'SmartBids',
        'email_seguridad_auditoria': 'contacto@chileavanza.cl',
    }


def registrar_auditoria_admin(ejecutor_uid, ejecutor_email, ejecutor_nombre, afectado_uid, afectado_email, afectado_nombre, accion, detalle='', ip_origen=None):
    """
    Registra un evento de seguridad de auditoría entre administradores.
    """
    try:
        return AuditoriaAdmin.objects.create(
            ejecutor_uid=ejecutor_uid or '',
            ejecutor_email=ejecutor_email or '',
            ejecutor_nombre=ejecutor_nombre or '',
            afectado_uid=afectado_uid or '',
            afectado_email=afectado_email or '',
            afectado_nombre=afectado_nombre or '',
            accion=accion,
            detalle=detalle or '',
            ip_origen=ip_origen,
        )
    except Exception as e:
        logger.warning(f"[SmartBids] Error al guardar auditoría admin en DB: {e}")
        return None


def notificar_accion_entre_administradores(ejecutor_email, ejecutor_nombre, afectado_email, accion, detalle=''):
    """
    Envía notificación inmediata por correo electrónico al administrador afectado
    y al buzón de auditoría de seguridad para garantizar transparencia total.
    """
    cfg = obtener_correos_sistema()
    asunto = "[SmartBids Seguridad] Notificación: Acción administrativa sobre cuenta de administrador"
    mensaje_plano = (
        f"Atención de Seguridad - SmartBids\n\n"
        f"Se ha registrado una acción administrativa sobre la cuenta de administrador: {afectado_email}\n\n"
        f"Acción: {accion}\n"
        f"Administrador ejecutor: {ejecutor_email} ({ejecutor_nombre})\n"
        f"Detalle: {detalle}\n\n"
        f"Esta acción fue registrada en la bitácora de auditoría del sistema.\n"
        f"Si no autorizaste o no reconoces esta acción, contacta de inmediato al equipo de seguridad: {cfg['email_seguridad_auditoria']}."
    )
    html_mensaje = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
        <div style="background: #072421; padding: 20px; text-align: center; color: white;">
            <h2 style="margin: 0; font-size: 20px;">Smart<span style="color: #04c657;">Bids</span> Seguridad</h2>
            <p style="margin: 5px 0 0; font-size: 13px; color: #a0aec0;">Alerta de Auditoría entre Administradores</p>
        </div>
        <div style="padding: 24px; color: #2d3748; line-height: 1.6;">
            <p style="font-size: 15px; margin-top: 0;">Estimado(a) Administrador(a),</p>
            <p style="font-size: 14px;">
                Te informamos que se ha ejecutado una acción administrativa que afecta tu cuenta o rol en la plataforma:
            </p>
            <div style="background: #f7fafc; border-left: 4px solid #e53e3e; padding: 14px 16px; border-radius: 6px; margin: 18px 0;">
                <p style="margin: 0 0 6px;"><strong>Acción:</strong> {accion}</p>
                <p style="margin: 0 0 6px;"><strong>Administrador ejecutor:</strong> {ejecutor_email} ({ejecutor_nombre})</p>
                <p style="margin: 0;"><strong>Detalle:</strong> {detalle}</p>
            </div>
            <p style="font-size: 13px; color: #718096;">
                Esta acción ha sido registrada en el sistema de auditoría permanente de SmartBids para que todas las partes involucradas tengan conocimiento transparente de lo ocurrido.
            </p>
            <p style="font-size: 13px; color: #718096;">
                Si consideras que esto es un error o una acción no autorizada, por favor escribe inmediatamente a: <a href="mailto:{cfg['email_seguridad_auditoria']}">{cfg['email_seguridad_auditoria']}</a>.
            </p>
        </div>
    </div>
    """
    destinatarios = [afectado_email]
    if cfg['email_seguridad_auditoria'] and cfg['email_seguridad_auditoria'] not in destinatarios:
        destinatarios.append(cfg['email_seguridad_auditoria'])

    try:
        from django.core.mail import send_mail
        remitente = f"{cfg['nombre_remitente']} <{cfg['email_notificaciones']}>"
        send_mail(
            subject=asunto,
            message=mensaje_plano,
            html_message=html_mensaje,
            from_email=remitente,
            recipient_list=destinatarios,
            fail_silently=True,
        )
    except Exception as e:
        logger.warning(f"[SmartBids] No se pudo enviar correo de auditoría admin: {e}")

class StopWord(models.Model):
    codigo_stop_word = models.SmallAutoField(primary_key=True)
    nombre_stop_word = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = True
        db_table = '"config"."stop_word"'

    def __str__(self):
        return self.nombre_stop_word