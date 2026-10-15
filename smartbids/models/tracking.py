from django.db import models

from .core import Suscriptor
from .procurement import Licitacion


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
        db_table = 'smartbids_seguimiento_licitacion'
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
        db_table = 'smartbids_notificacion_licitacion'
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
        db_table = 'smartbids_licitacion_documento'
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
        db_table = 'smartbids_licitacion_pregunta'
        ordering = ('fecha_pregunta', 'id')
