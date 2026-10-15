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
        db_table = 'mensajeria'
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
        managed = False
        db_table = '"config"."info_contacto"'
        verbose_name = "Configuración de Contacto y Enlaces"

    def __str__(self):
        return f"Configuración de Contacto #{self.id}"