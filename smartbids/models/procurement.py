
from django.db import models


class UnidadCompra(models.Model):
    codigo_unidad_compra = models.BigIntegerField(primary_key=True)
    activo = models.BooleanField(blank=True, null=True)
    codigo_ambito = models.ForeignKey(
        'Ambito',
        models.DO_NOTHING,
        db_column='codigo_ambito',
        blank=True,
        null=True
    )
    codigo_organismo = models.ForeignKey(
        'Organismo',
        models.DO_NOTHING,
        db_column='codigo_organismo',
        blank=True,
        null=True
    )

    class Meta:
        managed = False
        db_table = 'unidad_compra'

    def __str__(self):
        return str(self.codigo_unidad_compra)