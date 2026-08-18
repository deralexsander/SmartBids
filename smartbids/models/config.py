from django.db import models


class EstadoSuscriptor(models.Model):
    codigo_estado = models.SmallAutoField(primary_key=True)
    nombre_estado = models.CharField(max_length=30, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = '"config"."estado_suscriptor"'

    def __str__(self):
        return self.nombre_estado

from django.db import models

#esto es para agregar un 'excluir' o un 'incluir' a las preferencias de perfil, como en productos, palabras clave, etc. Así puede crear una whitelist y/o blacklist
class TipoPreferencia(models.Model):
    codigo_tipo_preferencia = models.SmallAutoField(primary_key=True)

    nombre_tipo_preferencia = models.CharField(
        max_length=20,
        unique=True
    )

    descripcion = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        db_table = '"config"."tipo_preferencia"'

    def __str__(self):
        return self.nombre_tipo_preferencia