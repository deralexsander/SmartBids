from django.db import models
from .config import EstadoSuscriptor
from .catalog import Comuna
from .procurement import Licitacion
from django.contrib.postgres.fields import ArrayField

class Empresa(models.Model):
    emp_rut = models.CharField(primary_key=True, max_length=15)
    emp_razon_social = models.CharField(max_length=200)
    emp_nombre_fantasia = models.CharField(max_length=200)
    emp_iniciales = models.CharField(max_length=20)
    emp_contacto_correo = models.CharField(max_length=254)
    emp_direccion = models.CharField(max_length=300, blank=True, null=True)
    emp_codigo_comuna = models.ForeignKey(
        Comuna,
        models.DO_NOTHING,
        db_column='emp_codigo_comuna',
        blank=True,
        null=True
    )
    emp_contacto_nombre = models.CharField(max_length=100, blank=True, null=True)
    emp_contacto_telefono = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = True
        db_table = '"core"."empresa"'

class Suscriptor(models.Model):
    id_suscriptor = models.BigAutoField(primary_key=True)
    firebase_uid = models.CharField(unique=True, max_length=128)
    fecha_registro = models.DateTimeField()
    fecha_actualizacion = models.DateTimeField()
    codigo_estado = models.ForeignKey(
        EstadoSuscriptor,
        models.DO_NOTHING,
        db_column='codigo_estado'
    )
    sus_nombre1 = models.CharField(max_length=100)
    sus_apellido1 = models.CharField(max_length=100)
    sus_apellido2 = models.CharField(max_length=100, blank=True, null=True)
    sus_rut_empresa = models.ForeignKey(Empresa, models.DO_NOTHING, db_column='sus_rut_empresa', blank=True, null=True)
    sus_nombre_social = models.CharField(max_length=100, blank=True, null=True)
    sus_iniciales = models.CharField(max_length=5, blank=True, null=True)
    sus_nombre2 = models.CharField(max_length=100, blank=True, null=True)
    token_sesion = models.CharField(max_length=128, blank=True, null=True)

    class Meta:
        managed = True
        db_table = '"core"."suscriptor"'

    def __str__(self):
        return f"Suscriptor {self.id_suscriptor} - {self.codigo_estado.nombre_estado}"


class Preferencia(models.Model):
    id_suscriptor = models.OneToOneField('Suscriptor', models.DO_NOTHING, db_column='id_suscriptor', primary_key=True)
    
    pref_ucom = ArrayField(
    models.BigIntegerField(),
    blank=True,
    null=True
)
    pref_comunas = ArrayField(
    models.CharField(max_length=5),
    blank=True,
    null=True
)
    pref_tipo_licitacion = ArrayField(
    models.CharField(max_length=2),
    blank=True,
    null=True
)
    pref_productos = ArrayField(
    models.CharField(max_length=20),
    blank=True,
    null=True
)
    pref_palabras_claves = ArrayField(
    models.CharField(max_length=50),
    blank=True,
    null=True,
    db_comment='poner un límite de palabras claves, ej: 20'
)
    pref_palabras_claves_norm = ArrayField(
    models.CharField(max_length=50),
    blank=True,
    null=True,
    db_comment='poner un límite de palabras claves, ej: 20',
)

    class Meta:
        managed = True
        db_table = '"core"."preferencia"'

class SeguimientoLicitacion(models.Model):
    ESTADOS = [
        ('publicada', 'Publicada'),
        ('preguntas', 'Período de preguntas'),
        ('ofertas', 'Recepción de ofertas'),
        ('cerrada', 'Cerrada'),
    ]

    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        Suscriptor,
        models.CASCADE,
        db_column='id_usuario',
        related_name='seguimientos_licitaciones',
    )
    licitacion = models.ForeignKey(
        Licitacion,
        models.CASCADE,
        db_column='id_licitacion',
        related_name='seguimientos',
    )
    estado_actual = models.CharField(max_length=20, choices=ESTADOS)
    seguimiento_activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    dejado_de_seguir_en = models.DateTimeField(blank=True, null=True)
    cerrada_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = '"core"."smartbids_seguimiento_licitacion"'
        constraints = [
            models.UniqueConstraint(
                fields=('usuario', 'licitacion'),
                name='uniq_seguimiento_usuario_licitacion',
            ),
        ]


class NotificacionLicitacion(models.Model):
    usuario = models.ForeignKey(
        Suscriptor,
        models.CASCADE,
        db_column='id_usuario',
        related_name='notificaciones_licitaciones',
    )
    licitacion = models.ForeignKey(
        Licitacion,
        models.CASCADE,
        db_column='id_licitacion',
        related_name='notificaciones',
    )
    seguimiento = models.ForeignKey(
        SeguimientoLicitacion,
        models.CASCADE,
        related_name='notificaciones',
    )
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    mensaje = models.CharField(max_length=300)
    leida = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"core"."smartbids_notificacion_licitacion"'
        ordering = ('-creado_en',)


class LicitacionDocumento(models.Model):
    licitacion = models.ForeignKey(
        Licitacion,
        models.CASCADE,
        related_name='documentos',
    )
    titulo = models.CharField(max_length=255)
    url = models.URLField(max_length=2000)
    fecha_publicacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = '"core"."smartbids_licitacion_documento"'
        ordering = ('-fecha_publicacion', 'titulo')


class LicitacionPregunta(models.Model):
    licitacion = models.ForeignKey(
        Licitacion,
        models.CASCADE,
        related_name='preguntas_respuestas',
    )
    pregunta = models.TextField()
    respuesta = models.TextField(blank=True)
    fecha_pregunta = models.DateTimeField(blank=True, null=True)
    fecha_respuesta = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = '"core"."smartbids_licitacion_pregunta"'
        ordering = ('fecha_pregunta', 'id')
