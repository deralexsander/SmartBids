from django.db import models

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