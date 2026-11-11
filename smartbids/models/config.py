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
    email_seguridad_auditoria = models.EmailField(max_length=255, default='smartbids.qa@chileavanza.cl', verbose_name="Correo de alertas de seguridad y auditoría")
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
    Prioridad:
    1. Base de datos (ConfiguracionCorreo) si existe y tiene valores definidos.
    2. Variables de entorno (.env) o settings.
    3. Valores institucionales por defecto.
    """
    import os
    from django.conf import settings

    env_contacto = os.getenv('EMAIL_CONTACTO') or getattr(settings, 'EMAIL_CONTACTO', 'contacto@chileavanza.cl')
    env_host_user = os.getenv('EMAIL_HOST_USER') or getattr(settings, 'EMAIL_HOST_USER', 'smartbids.qa@chileavanza.cl')
    env_notificaciones = (
        os.getenv('EMAIL_NOTIFICACIONES')
        or getattr(settings, 'EMAIL_NOTIFICACIONES', None)
        or env_host_user
    )
    env_remitente = os.getenv('EMAIL_NOMBRE_REMITENTE') or getattr(settings, 'EMAIL_NOMBRE_REMITENTE', 'SmartBids')
    env_seguridad = (
        os.getenv('EMAIL_SEGURIDAD_AUDITORIA')
        or getattr(settings, 'EMAIL_SEGURIDAD_AUDITORIA', None)
        or env_notificaciones
    )

    try:
        cfg = ConfiguracionCorreo.objects.first()
        if cfg:
            return {
                'email_contacto': cfg.email_contacto or env_contacto,
                'email_notificaciones': cfg.email_notificaciones or env_notificaciones,
                'nombre_remitente': cfg.nombre_remitente or env_remitente,
                'email_seguridad_auditoria': cfg.email_seguridad_auditoria or env_seguridad,
            }
    except Exception:
        pass

    return {
        'email_contacto': env_contacto,
        'email_notificaciones': env_notificaciones,
        'nombre_remitente': env_remitente,
        'email_seguridad_auditoria': env_seguridad,
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
    para garantizar transparencia total.
    """
    cfg = obtener_correos_sistema()
    email_qa = cfg.get('email_notificaciones') or 'smartbids.qa@chileavanza.cl'
    asunto = "[SmartBids Seguridad] Notificación: Acción administrativa sobre cuenta de administrador"
    mensaje_plano = (
        f"Atención de Seguridad - SmartBids\n\n"
        f"Se ha registrado una acción administrativa sobre la cuenta de administrador: {afectado_email}\n\n"
        f"Acción: {accion}\n"
        f"Administrador ejecutor: {ejecutor_email} ({ejecutor_nombre})\n"
        f"Detalle: {detalle}\n\n"
        f"Esta acción fue registrada en la bitácora de auditoría del sistema.\n"
        f"Si no autorizaste o no reconoces esta acción, puedes responder directamente a este correo ({email_qa})."
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
                Si consideras que esto es un error o una acción no autorizada, por favor responde directamente a este correo o escribe a: <a href="mailto:{email_qa}">{email_qa}</a>.
            </p>
        </div>
    </div>
    """
    destinatarios = [afectado_email]

    try:
        from django.core.mail import send_mail
        remitente = f"{cfg.get('nombre_remitente') or 'SmartBids'} <{email_qa}>"
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


def notificar_cambio_rol_suscriptor(ejecutor_email, ejecutor_nombre, afectado_email, afectado_nombre, estado_anterior, estado_nuevo):
    """
    Envía una notificación formal por correo electrónico cuando se modifica el estado
    o rol de un suscriptor en SmartBids (ej: Prospecto -> Suscriptor, Promoción a Administrador,
    Revocación de Administrador).

    Utiliza la cuenta institucional de QA (smartbids.qa@chileavanza.cl) como remitente.
    """
    from html import escape
    from django.conf import settings
    from django.core.mail import send_mail

    afectado_email = (afectado_email or '').strip()
    if not afectado_email or '@' not in afectado_email:
        logger.warning(f"[SmartBids] No se envió notificación de rol: email de afectado inválido '{afectado_email}'")
        return {'enviado': False, 'motivo': 'Email afectado inválido'}

    ejecutor_email = (ejecutor_email or '').strip() or 'smartbids.qa@chileavanza.cl'
    ejecutor_nombre = (ejecutor_nombre or '').strip() or ejecutor_email
    afectado_nombre = (afectado_nombre or '').strip() or (afectado_email.split('@')[0] if '@' in afectado_email else 'Usuario')

    cfg = obtener_correos_sistema()
    email_qa = (
        cfg.get('email_notificaciones')
        or getattr(settings, 'EMAIL_HOST_USER', None)
        or 'smartbids.qa@chileavanza.cl'
    )
    nombre_remitente = cfg.get('nombre_remitente') or 'SmartBids'
    remitente = f"{nombre_remitente} <{email_qa}>"

    cod_anterior = getattr(estado_anterior, 'codigo_estado', None) if estado_anterior else None
    nombre_anterior = (getattr(estado_anterior, 'nombre_estado', '') or '').strip()
    nombre_anterior_lower = nombre_anterior.casefold()

    cod_nuevo = getattr(estado_nuevo, 'codigo_estado', None) if estado_nuevo else None
    nombre_nuevo = (getattr(estado_nuevo, 'nombre_estado', '') or '').strip()
    nombre_nuevo_lower = nombre_nuevo.casefold()

    es_anterior_admin = cod_anterior == 5 or 'administrador' in nombre_anterior_lower or 'admin' in nombre_anterior_lower
    es_nuevo_admin = cod_nuevo == 5 or 'administrador' in nombre_nuevo_lower or 'admin' in nombre_nuevo_lower

    es_anterior_suscriptor = cod_anterior == 2 or 'suscriptor' in nombre_anterior_lower or 'habilitado' in nombre_anterior_lower
    es_nuevo_suscriptor = (cod_nuevo == 2 or 'suscriptor' in nombre_nuevo_lower or 'habilitado' in nombre_nuevo_lower) and not es_nuevo_admin

    es_anterior_prospecto = cod_anterior == 1 or 'prospecto' in nombre_anterior_lower or 'deshabilitado' in nombre_anterior_lower
    es_nuevo_prospecto = (cod_nuevo == 1 or 'prospecto' in nombre_nuevo_lower or 'deshabilitado' in nombre_nuevo_lower) and not es_nuevo_admin

    destinatarios = [afectado_email]

    # Caso 1: Promoción a Administrador
    if es_nuevo_admin and not es_anterior_admin:
        tipo = 'ASIGNACION_ADMIN'
        asunto = "[SmartBids Seguridad] Notificación: Asignación de Rol Administrador"

        mensaje_plano = (
            f"Atención de Seguridad - SmartBids\n\n"
            f"Estimado(a) {afectado_nombre},\n\n"
            f"Te informamos formalmente que se te ha otorgado el rol de Administrador en la plataforma SmartBids.\n\n"
            f"El administrador con correo {ejecutor_email} te ha otorgado el rol de Administrador en SmartBids.\n\n"
            f"Como Administrador institucional, cuentas con las siguientes facultades y responsabilidades:\n"
            f"• Gestión y Control de Usuarios: Asignación y actualización de estados y suscripciones de usuarios registrados.\n"
            f"• Políticas de Seguridad Institucional: Supervisión de requerimientos de seguridad, sesiones y contraseñas.\n"
            f"• Bitácora de Auditoría: Acceso transparente al historial de acciones y operaciones administrativas.\n\n"
            f"Aviso de Seguridad: El rol de administrador otorga privilegios de nivel superior sobre la plataforma y datos confidenciales. "
            f"Resguarda tus credenciales de acceso y mantén estricta confidencialidad.\n\n"
            f"Esta acción ha sido registrada en el sistema de auditoría permanente de SmartBids.\n"
            f"Si no autorizaste o desconoces esta asignación, contáctate respondiendo directamente a este correo ({email_qa}).\n\n"
            f"Atentamente,\n"
            f"Equipo de Seguridad y Control de Gestión\n"
            f"SmartBids — ChileAvanza SpA"
        )

        html_mensaje = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>{escape(asunto)}</title></head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; color: #1e293b;">
  <div style="max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
    <div style="background: linear-gradient(135deg, #072421 0%, #0c3b37 100%); padding: 30px 24px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">
        Smart<span style="color: #04c657;">Bids</span> <span style="font-size: 17px; font-weight: 400; color: #94a3b8;">Seguridad</span>
      </h1>
      <p style="margin: 6px 0 0; font-size: 13px; color: #94a3b8;">Notificación Institucional de Gestión y Control</p>
    </div>
    <div style="padding: 28px 24px;">
      <p style="font-size: 16px; margin: 0 0 14px;">Estimado(a) <strong>{escape(afectado_nombre)}</strong>,</p>
      <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 16px;">
        Te informamos formalmente que se te ha otorgado el rol de <strong>Administrador</strong> en la plataforma SmartBids.
      </p>
      <div style="background: #f0fdf4; border-left: 4px solid #04c657; padding: 14px 18px; border-radius: 6px; margin: 0 0 20px;">
        <p style="margin: 0; font-size: 15px; line-height: 1.6; color: #14532d;">
          El administrador con correo <strong style="color: #0f172a;">{escape(ejecutor_email)}</strong> te ha otorgado el rol de <strong>Administrador</strong> en SmartBids.
        </p>
      </div>
      <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 12px;">
        Como Administrador institucional, ahora cuentas con facultades de control y supervisión sobre la plataforma:
      </p>
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 18px; margin: 0 0 20px;">
        <ul style="margin: 0; padding-left: 18px; color: #1e293b; font-size: 13px; line-height: 1.8;">
          <li><strong>Gestión y Control de Usuarios:</strong> Supervisión, asignación y actualización de estados y suscripciones de usuarios registrados.</li>
          <li><strong>Políticas de Seguridad Institucional:</strong> Administración de directrices de seguridad, contraseñas y accesos.</li>
          <li><strong>Auditoría Permanente:</strong> Consulta de bitácoras de acciones administrativas para garantizar la trazabilidad de operaciones.</li>
        </ul>
      </div>
      <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; margin: 0 0 22px;">
        <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #92400e;">
          <strong>Aviso de Seguridad:</strong> El acceso de administrador implica alta responsabilidad sobre la confidencialidad del sistema. Resguarda tus credenciales y no compartas tu contraseña.<br><br>
          Esta acción fue registrada en la bitácora de auditoría. Si no autorizaste esta asignación, responde directamente a este correo o escribe a: <a href="mailto:{escape(email_qa)}" style="color: #b45309; font-weight: 700;">{escape(email_qa)}</a>.
        </p>
      </div>
      <p style="font-size: 13px; color: #334155; margin: 18px 0 0;">
        Saludos cordiales,<br>
        <strong style="color: #072421;">Equipo de Seguridad y Control de Gestión</strong><br>
        <span style="font-size: 12px; color: #64748b;">SmartBids — ChileAvanza SpA</span>
      </p>
    </div>
    <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px; text-align: center; font-size: 11px; color: #94a3b8;">
      © SmartBids — Correo institucional emitido desde la cuenta oficial de soporte y QA: {escape(email_qa)}
    </div>
  </div>
</body>
</html>"""

    # Caso 2: Revocación de Administrador
    elif es_anterior_admin and not es_nuevo_admin:
        tipo = 'REVOCACION_ADMIN'
        asunto = "[SmartBids Seguridad] Notificación: Revocación de Rol Administrador"

        mensaje_plano = (
            f"Atención de Seguridad - SmartBids\n\n"
            f"Estimado(a) {afectado_nombre},\n\n"
            f"Te informamos formalmente que tu rol de Administrador en la plataforma SmartBids ha sido revocado. Tu cuenta ha sido asignada al estado de '{nombre_nuevo}'.\n\n"
            f"El administrador con correo {ejecutor_email} te ha quitado el rol de Administrador en SmartBids.\n\n"
            f"Detalles de la modificación:\n"
            f"• Rol anterior: Administrador\n"
            f"• Nuevo estado asignado: {nombre_nuevo}\n"
            f"• Administrador ejecutor: {ejecutor_email} ({ejecutor_nombre})\n\n"
            f"A partir de este momento, se han inhabilitado tus facultades de control sobre otros usuarios, modificación de políticas y paneles de auditoría. Puedes continuar utilizando la plataforma con los beneficios y funciones correspondientes a tu nuevo estado ({nombre_nuevo}).\n\n"
            f"Esta acción ha sido registrada en las bitácoras de auditoría de SmartBids.\n"
            f"Si consideras que esto es un error o fue una acción no autorizada, por favor responde directamente a este correo ({email_qa}).\n\n"
            f"Atentamente,\n"
            f"Equipo de Seguridad y Control de Gestión\n"
            f"SmartBids — ChileAvanza SpA"
        )

        html_mensaje = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>{escape(asunto)}</title></head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; color: #1e293b;">
  <div style="max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
    <div style="background: linear-gradient(135deg, #072421 0%, #0c3b37 100%); padding: 30px 24px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">
        Smart<span style="color: #04c657;">Bids</span> <span style="font-size: 17px; font-weight: 400; color: #94a3b8;">Seguridad</span>
      </h1>
      <p style="margin: 6px 0 0; font-size: 13px; color: #94a3b8;">Alerta Institucional de Auditoría y Control</p>
    </div>
    <div style="padding: 28px 24px;">
      <p style="font-size: 16px; margin: 0 0 14px;">Estimado(a) <strong>{escape(afectado_nombre)}</strong>,</p>
      <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 16px;">
        Te informamos formalmente que tu rol de <strong>Administrador</strong> en la plataforma SmartBids ha sido revocado. Tu cuenta ha sido asignada al estado de <strong>{escape(nombre_nuevo)}</strong>.
      </p>
      <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 14px 18px; border-radius: 6px; margin: 0 0 20px;">
        <p style="margin: 0; font-size: 15px; line-height: 1.6; color: #991b1b;">
          El administrador con correo <strong style="color: #0f172a;">{escape(ejecutor_email)}</strong> te ha quitado el rol de <strong>Administrador</strong> en SmartBids.
        </p>
      </div>
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin: 0 0 20px;">
        <p style="margin: 0 0 6px; font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 700;">Detalles de la modificación:</p>
        <p style="margin: 0 0 4px; font-size: 13px;"><strong>Rol anterior:</strong> Administrador</p>
        <p style="margin: 0 0 4px; font-size: 13px;"><strong>Nuevo estado asignado:</strong> {escape(nombre_nuevo)}</p>
        <p style="margin: 0; font-size: 13px;"><strong>Administrador ejecutor:</strong> {escape(ejecutor_email)} ({escape(ejecutor_nombre)})</p>
      </div>
      <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 16px;">
        A partir de este momento, se han inhabilitado tus facultades de control sobre otros usuarios, modificación de políticas y paneles de auditoría. Puedes continuar utilizando la plataforma con los beneficios y funciones correspondientes a tu nuevo estado (<strong>{escape(nombre_nuevo)}</strong>).
      </p>
      <div style="background: #f8fafc; border-left: 4px solid #64748b; padding: 12px 16px; border-radius: 6px; margin: 0 0 22px;">
        <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #475569;">
          Esta acción fue registrada en la bitácora de auditoría permanente del sistema.<br>
          Si consideras que esto es un error o fue una acción no autorizada, responde directamente a este correo o escribe a: <a href="mailto:{escape(email_qa)}" style="color: #072421; font-weight: 700;">{escape(email_qa)}</a>.
        </p>
      </div>
      <p style="font-size: 13px; color: #334155; margin: 18px 0 0;">
        Saludos cordiales,<br>
        <strong style="color: #072421;">Equipo de Seguridad y Control de Gestión</strong><br>
        <span style="font-size: 12px; color: #64748b;">SmartBids — ChileAvanza SpA</span>
      </p>
    </div>
    <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px; text-align: center; font-size: 11px; color: #94a3b8;">
      © SmartBids — Correo institucional emitido desde la cuenta oficial de soporte y QA: {escape(email_qa)}
    </div>
  </div>
</body>
</html>"""

    # Caso 3: Promoción a Suscriptor (ej. Prospecto -> Suscriptor)
    elif es_nuevo_suscriptor and not es_anterior_suscriptor:
        tipo = 'PROSPECTO_A_SUSCRIPTOR'
        asunto = "¡Bienvenido(a) a SmartBids Suscriptor! Tu acceso completo ha sido habilitado"

        mensaje_plano = (
            f"¡Bienvenido(a) a SmartBids Suscriptor!\n\n"
            f"Estimado(a) {afectado_nombre},\n\n"
            f"Te informamos con agrado que tu cuenta ha sido actualizada exitosamente al estado de Suscriptor (Acceso Total) en SmartBids.\n\n"
            f"¡Ahora eres parte de nuestra comunidad de suscriptores y puedes disfrutar de todos los beneficios y herramientas avanzadas de la plataforma!\n\n"
            f"Beneficios de tu suscripción habilitados:\n"
            f"• Explorador Licitatorio Total: Monitoreo exhaustivo de licitaciones de Mercado Público en las 346 comunas de Chile sin restricciones territoriales ni límites diarios.\n"
            f"• Fichas Técnicas Oficiales y Documentación: Acceso y descarga directa de bases administrativas, aclaraciones y anexos oficiales.\n"
            f"• Dashboards Analíticos en Tiempo Real: Indicadores interactivos de montos presupuestados, históricos de adjudicación y comportamiento de compradores.\n"
            f"• Inteligencia Predictiva (Machine Learning XGBoost): Estimación predictiva de probabilidades de adjudicación y recomendaciones estratégicas para optimizar tus postulaciones.\n"
            f"• Alertas Inteligentes y Seguimiento: Avisos oportunos de nuevas publicaciones y modificaciones en compras públicas de tu rubro.\n"
            f"• Exportación Masiva: Descarga de reportes estructurados para análisis estratégico con tu equipo comercial.\n\n"
            f"Esta activación fue procesada por el equipo de administración de SmartBids ({ejecutor_email}).\n\n"
            f"Ingresa a la plataforma y comienza a explorar:\n"
            f"https://chileavanza.cl/\n\n"
            f"Si tienes dudas o requieres asistencia técnica, puedes responder directamente a este correo ({email_qa}).\n\n"
            f"Atentamente,\n"
            f"Equipo SmartBids\n"
            f"ChileAvanza SpA"
        )

        html_mensaje = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>{escape(asunto)}</title></head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; color: #1e293b;">
  <div style="max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
    <div style="background: linear-gradient(135deg, #072421 0%, #0c3b37 100%); padding: 32px 24px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;">
        Smart<span style="color: #04c657;">Bids</span>
      </h1>
      <p style="margin: 6px 0 0; font-size: 13px; color: #94a3b8;">Inteligencia Licitatoria y Compras Públicas de Chile</p>
    </div>
    <div style="padding: 28px 24px;">
      <p style="font-size: 16px; margin: 0 0 14px;">Estimado(a) <strong>{escape(afectado_nombre)}</strong>,</p>
      <div style="background: #f0fdf4; border-left: 4px solid #04c657; padding: 14px 18px; border-radius: 6px; margin: 0 0 20px;">
        <span style="display: block; font-size: 15px; font-weight: 700; color: #166534;">
          ¡Tu membresía Suscriptor ha sido activada exitosamente!
        </span>
        <span style="display: block; font-size: 13px; color: #15803d; margin-top: 4px;">
          Tu cuenta ahora cuenta con el estado <strong>Suscriptor (Acceso Total)</strong> en SmartBids.
        </span>
      </div>
      <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 16px;">
        A partir de este momento, tienes acceso irrestricto a todas las herramientas avanzadas y módulos de inteligencia de negocios para optimizar tus postulaciones en el mercado público:
      </p>
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 18px; margin: 0 0 20px;">
        <ul style="margin: 0; padding-left: 18px; color: #1e293b; font-size: 13px; line-height: 1.8;">
          <li><strong>Explorador Licitatorio Total:</strong> Monitoreo de convocatorias públicas en las 346 comunas de Chile sin restricciones de búsqueda ni límites diarios.</li>
          <li><strong>Bases y Fichas Técnicas Oficiales:</strong> Acceso y descarga directa de documentación, requerimientos y anexos de Mercado Público.</li>
          <li><strong>Dashboards Analíticos en Tiempo Real:</strong> Gráficos interactivos de presupuestos, históricos de adjudicación y comportamiento de compradores.</li>
          <li><strong>Inteligencia Predictiva (Machine Learning XGBoost):</strong> Estimación predictiva de probabilidades de adjudicación y recomendaciones basadas en datos.</li>
          <li><strong>Alertas Automatizadas y Seguimiento:</strong> Avisos oportunos ante nuevas publicaciones, aclaraciones y aperturas de tu sector.</li>
          <li><strong>Exportación Masiva:</strong> Descarga de reportes estructurados para análisis estratégico con tu equipo comercial.</li>
        </ul>
      </div>
      <div style="text-align: center; margin: 26px 0 22px;">
        <a href="https://chileavanza.cl/" style="display: inline-block; background: #04c657; color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 700; padding: 13px 30px; border-radius: 8px; box-shadow: 0 2px 6px rgba(4,198,87,0.3);">
          Acceder a SmartBids
        </a>
      </div>
      <p style="font-size: 12px; color: #64748b; line-height: 1.5; margin: 18px 0 0; border-top: 1px solid #e2e8f0; padding-top: 14px;">
        Activación gestionada por la administración de SmartBids ({escape(ejecutor_email)}).<br>
        Si tienes preguntas o necesitas asistencia, puedes responder directamente a este correo o escribirnos a <a href="mailto:{escape(email_qa)}" style="color: #04c657; text-decoration: none;">{escape(email_qa)}</a>.
      </p>
      <p style="font-size: 13px; color: #334155; margin: 16px 0 0;">
        Saludos cordiales,<br>
        <strong style="color: #072421;">Equipo SmartBids</strong><br>
        <span style="font-size: 12px; color: #64748b;">ChileAvanza SpA</span>
      </p>
    </div>
    <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px; text-align: center; font-size: 11px; color: #94a3b8;">
      © SmartBids — Correo institucional emitido desde la cuenta oficial de soporte y QA: {escape(email_qa)}
    </div>
  </div>
</body>
</html>"""

    # Caso 4: Suscriptor -> Prospecto
    elif es_nuevo_prospecto and es_anterior_suscriptor:
        tipo = 'SUSCRIPTOR_A_PROSPECTO'
        asunto = "[SmartBids] Notificación: Actualización de estado de cuenta a Prospecto"

        mensaje_plano = (
            f"Notificación de Estado de Cuenta - SmartBids\n\n"
            f"Estimado(a) {afectado_nombre},\n\n"
            f"Te informamos que el estado de tu cuenta en SmartBids ha sido actualizado a Prospecto.\n\n"
            f"Tu cuenta continúa activa con acceso a las funciones iniciales de la plataforma. Si deseas reactivar tu membresía Suscriptor para recuperar el acceso total al explorador nacional de 346 comunas, dashboards analíticos y Machine Learning predictivo, puedes solicitarlo en cualquier momento desde nuestra plataforma.\n\n"
            f"Revisa los planes disponibles:\n"
            f"https://chileavanza.cl/planes/\n\n"
            f"Cualquier consulta no dudes en responder directamente a este correo ({email_qa}).\n\n"
            f"Atentamente,\n"
            f"Equipo SmartBids\n"
            f"ChileAvanza SpA"
        )

        html_mensaje = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>{escape(asunto)}</title></head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; color: #1e293b;">
  <div style="max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
    <div style="background: linear-gradient(135deg, #072421 0%, #0c3b37 100%); padding: 30px 24px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">
        Smart<span style="color: #04c657;">Bids</span>
      </h1>
      <p style="margin: 6px 0 0; font-size: 13px; color: #94a3b8;">Notificación de Estado de Cuenta</p>
    </div>
    <div style="padding: 28px 24px;">
      <p style="font-size: 16px; margin: 0 0 14px;">Estimado(a) <strong>{escape(afectado_nombre)}</strong>,</p>
      <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 16px;">
        Te informamos que el estado de tu cuenta en SmartBids ha sido actualizado a <strong>Prospecto</strong>.
      </p>
      <div style="background: #f8fafc; border-left: 4px solid #64748b; padding: 14px 18px; border-radius: 6px; margin: 0 0 20px;">
        <p style="margin: 0; font-size: 13px; line-height: 1.6; color: #334155;">
          Tu cuenta continúa activa con acceso a las funciones iniciales de la plataforma. Si deseas reactivar tu membresía Suscriptor y recuperar el acceso total al explorador nacional de 346 comunas, dashboards analíticos y modelos de Machine Learning predictivo, puedes solicitarlo en cualquier momento.
        </p>
      </div>
      <div style="text-align: center; margin: 24px 0 20px;">
        <a href="https://chileavanza.cl/planes/" style="display: inline-block; background: #072421; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 700; padding: 12px 28px; border-radius: 8px;">
          Ver Planes Disponibles
        </a>
      </div>
      <p style="font-size: 13px; color: #334155; margin: 18px 0 0;">
        Saludos cordiales,<br>
        <strong style="color: #072421;">Equipo SmartBids</strong><br>
        <span style="font-size: 12px; color: #64748b;">ChileAvanza SpA</span>
      </p>
    </div>
    <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px; text-align: center; font-size: 11px; color: #94a3b8;">
      © SmartBids — Correo institucional emitido desde la cuenta oficial de soporte y QA: {escape(email_qa)}
    </div>
  </div>
</body>
</html>"""

    # Caso 5: Otro cambio de rol o estado
    elif cod_anterior != cod_nuevo:
        tipo = 'CAMBIO_ESTADO_GENERAL'
        asunto = f"[SmartBids] Notificación: Actualización de estado a {nombre_nuevo}"

        mensaje_plano = (
            f"Notificación de Cuenta - SmartBids\n\n"
            f"Estimado(a) {afectado_nombre},\n\n"
            f"Te informamos que tu cuenta en SmartBids ha sido actualizada al estado de '{nombre_nuevo}'.\n\n"
            f"Actualización procesada por el administrador {ejecutor_email}.\n\n"
            f"Para más detalles o consultas, puedes responder directamente a este correo ({email_qa}).\n\n"
            f"Atentamente,\n"
            f"Equipo SmartBids\n"
            f"ChileAvanza SpA"
        )

        html_mensaje = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>{escape(asunto)}</title></head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; color: #1e293b;">
  <div style="max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
    <div style="background: linear-gradient(135deg, #072421 0%, #0c3b37 100%); padding: 30px 24px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">
        Smart<span style="color: #04c657;">Bids</span>
      </h1>
      <p style="margin: 6px 0 0; font-size: 13px; color: #94a3b8;">Actualización de Estado de Cuenta</p>
    </div>
    <div style="padding: 28px 24px;">
      <p style="font-size: 16px; margin: 0 0 14px;">Estimado(a) <strong>{escape(afectado_nombre)}</strong>,</p>
      <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 16px;">
        Te informamos que tu cuenta en SmartBids ha sido actualizada al estado de <strong>{escape(nombre_nuevo)}</strong>.
      </p>
      <p style="font-size: 12px; color: #64748b; margin: 16px 0 0;">
        Actualización procesada por el administrador {escape(ejecutor_email)}.
      </p>
      <p style="font-size: 13px; color: #334155; margin: 18px 0 0;">
        Saludos cordiales,<br>
        <strong style="color: #072421;">Equipo SmartBids</strong><br>
        <span style="font-size: 12px; color: #64748b;">ChileAvanza SpA</span>
      </p>
    </div>
    <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px; text-align: center; font-size: 11px; color: #94a3b8;">
      © SmartBids — Correo institucional emitido desde la cuenta oficial de soporte y QA: {escape(email_qa)}
    </div>
  </div>
</body>
</html>"""
    else:
        return {'enviado': False, 'motivo': 'Sin cambio de estado'}

    try:
        send_mail(
            subject=asunto,
            message=mensaje_plano,
            html_message=html_mensaje,
            from_email=remitente,
            recipient_list=destinatarios,
            fail_silently=False,
        )
        logger.info(f"[SmartBids] Notificación de rol '{tipo}' enviada con éxito a {destinatarios} desde {remitente}")
        return {'enviado': True, 'tipo': tipo, 'asunto': asunto, 'destinatarios': destinatarios}
    except Exception as e:
        logger.warning(f"[SmartBids] Error al enviar notificación de rol '{tipo}' a {destinatarios}: {e}")
        return {'enviado': False, 'tipo': tipo, 'error': str(e)}

class StopWord(models.Model):
    codigo_stop_word = models.SmallAutoField(primary_key=True)
    nombre_stop_word = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = True
        db_table = '"config"."stop_word"'

    def __str__(self):
        return self.nombre_stop_word