
from django.db import models


class UnidadCompra(models.Model):
    codigo_unidad_compra = models.BigIntegerField(primary_key=True)
    ucom_activo = models.BooleanField(blank=True, null=True)
    ucom_codigo_ambito = models.CharField(max_length=3, blank=True, null=True)
    ucom_codigo_organismo = models.BigIntegerField(blank=True, null=True)
    ucom_rut = models.CharField(max_length=15, blank=True, null=True)
    ucom_direccion = models.CharField(max_length=300, blank=True, null=True)
    ucom_codigo_comuna = models.CharField(max_length=5, blank=True, null=True)
    ucom_descripcion = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"procurement"."unidad_compra"'
        
class Licitacion(models.Model):
    lic_codigo = models.CharField(primary_key=True, max_length=20)
    lic_nombre = models.CharField(max_length=300, blank=True, null=True)
    lic_descripcion = models.TextField(blank=True, null=True)
    lic_fecha_cierre = models.DateField(blank=True, null=True, db_comment='date sin tiempo')
    lic_hora_cierre = models.TimeField(blank=True, null=True)
    lic_toma_razon = models.BooleanField(blank=True, null=True)
    lic_codigo_ucom = models.ForeignKey('UnidadCompra', models.DO_NOTHING, db_column='lic_codigo_ucom', blank=True, null=True)
    lic_fecha_public = models.DateField(blank=True, null=True, db_comment='esta es date con tiempo')
    lic_fecha_preguntas = models.DateTimeField(blank=True, null=True, db_comment='date con tiempo')
    lic_fecha_respuestas = models.DateTimeField(blank=True, null=True, db_comment='fecha sin hora')
    lic_tipo_licitacion = models.CharField(max_length=2, blank=True, null=True)
    lic_moneda = models.CharField(max_length=20, blank=True, null=True)
    lic_presupuesto = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True, db_comment='numero con deciamles')
    lic_items_cantidad = models.IntegerField(blank=True, null=True)
    lic_codigos_producto = models.TextField(blank=True, null=True)  # This field type is a guess.
    lic_diccionario_palabras = models.TextField(blank=True, null=True)  # This field type is a guess.
    lic_texto = models.TextField(blank=True, null=True)
    lic_url = models.TextField(blank=True, null=True)
    lic_plazo = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"procurement"."licitacion"'
        
class LicitacionesProductos(models.Model):
    pk = models.CompositePrimaryKey('lic_codigo', 'codigo_producto')
    lic_codigo = models.ForeignKey(Licitacion, models.DO_NOTHING, db_column='lic_codigo')
    codigo_producto = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = '"procurement"."licitaciones_productos"'