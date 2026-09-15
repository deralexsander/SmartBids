# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class DimComprador(models.Model):
    comprador_key = models.BigAutoField(primary_key=True)
    comprador_unidad_codigo_publico = models.BigIntegerField(unique=True)
    comprador_unidad_nombre = models.TextField(blank=True, null=True)
    comprador_organismo_codigo = models.BigIntegerField()
    comprador_organismo_nombre = models.TextField(blank=True, null=True)
    comprador_sector = models.TextField(blank=True, null=True)
    comprador_ciudad = models.TextField(blank=True, null=True)
    comprador_region = models.TextField(blank=True, null=True)
    comprador_pais = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"dw"."dim_comprador"'

class DimFecha(models.Model):
    fecha_key = models.IntegerField(primary_key=True)
    fecha = models.DateField(unique=True)
    dia = models.SmallIntegerField()
    dia_semana = models.SmallIntegerField()
    nombre_dia = models.CharField(max_length=10)
    nombre_dia_corto = models.CharField(max_length=3)
    mes = models.SmallIntegerField()
    nombre_mes = models.CharField(max_length=10)
    nombre_mes_corto = models.CharField(max_length=3)
    trimestre = models.SmallIntegerField()
    anio = models.SmallIntegerField()
    anio_mes = models.CharField(max_length=7)
    es_fin_semana = models.BooleanField()

    class Meta:
        managed = False
        db_table = '"dw"."dim_fecha"'


class DimProducto(models.Model):
    producto_key = models.BigAutoField(primary_key=True)
    producto_codigo = models.CharField(unique=True, max_length=30)
    producto_nombre = models.TextField()
    producto_categoria_codigo = models.CharField(max_length=30, blank=True, null=True)
    producto_categoria = models.TextField(blank=True, null=True)
    producto_rubro_n1 = models.TextField(blank=True, null=True)
    producto_rubro_n2 = models.TextField(blank=True, null=True)
    producto_rubro_n3 = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"dw"."dim_producto"'


class DimProveedor(models.Model):
    proveedor_key = models.BigAutoField(primary_key=True)
    proveedor_codigo = models.CharField(max_length=30)
    proveedor_nombre = models.TextField(blank=True, null=True)
    proveedor_comuna = models.TextField(blank=True, null=True)
    proveedor_region = models.TextField(blank=True, null=True)
    proveedor_pais = models.CharField(max_length=100, blank=True, null=True)
    proveedor_sucursal_codigo = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = '"dw"."dim_proveedor"'
        unique_together = (('proveedor_codigo', 'proveedor_sucursal_codigo'),)


class FactItemOrdenCompra(models.Model):
    item_key = models.BigAutoField(primary_key=True)
    item_id_mercado_publico = models.CharField(unique=True, max_length=30, db_comment='identificador que viene desde Mercado Público')
    producto_key = models.ForeignKey(DimProducto, models.DO_NOTHING, db_column='producto_key')
    item_cantidad = models.DecimalField(max_digits=30, decimal_places=8, blank=True, null=True)
    item_unidad_medida = models.CharField(max_length=100, blank=True, null=True)
    item_moneda = models.CharField(max_length=3, blank=True, null=True)
    item_precio_neto = models.DecimalField(max_digits=30, decimal_places=8, blank=True, null=True, db_comment='Precio neto por unidad')
    item_total_linea_neto = models.DecimalField(max_digits=30, decimal_places=8, blank=True, null=True, db_comment='Cantidad por precio neto') #cantidad × precio_neto − descuentos + cargos
    item_fecha_carga = models.DateTimeField()
    fecha_creacion_key = models.ForeignKey(DimFecha, models.DO_NOTHING, db_column='fecha_creacion_key', db_comment='Fecha en que se creó la orden')
    proveedor_key = models.ForeignKey(DimProveedor, models.DO_NOTHING, db_column='proveedor_key', db_comment='Proveedor-sucursal adjudicado')
    comprador_key = models.ForeignKey(DimComprador, models.DO_NOTHING, db_column='comprador_key', db_comment='Unidad compradora')
    orden_codigo = models.CharField(max_length=50)
    licitacion_codigo = models.CharField(max_length=50)
    fecha_envio_key = models.ForeignKey(DimFecha, models.DO_NOTHING, db_column='fecha_envio_key', related_name='factitemordencompra_fecha_envio_key_set', blank=True, null=True, db_comment='Fecha en que se envió al proveedor')
    fecha_aceptacion_key = models.ForeignKey(DimFecha, models.DO_NOTHING, db_column='fecha_aceptacion_key', related_name='factitemordencompra_fecha_aceptacion_key_set', blank=True, null=True, db_comment='Fecha en que fue aceptada')
    fecha_ultima_modificacion_key = models.ForeignKey(DimFecha, models.DO_NOTHING, db_column='fecha_ultima_modificacion_key', related_name='factitemordencompra_fecha_ultima_modificacion_key_set', blank=True, null=True)
    orden_es_confirmada = models.BooleanField()

    class Meta:
        managed = False
        db_table = '"dw"."fact_item_orden_compra"'


class FactOrdenCompra(models.Model):
    orden_key = models.BigAutoField(primary_key=True)
    orden_codigo = models.CharField(unique=True, max_length=50)
    licitacion_codigo = models.CharField(max_length=50)
    fecha_creacion_key = models.ForeignKey(DimFecha, models.DO_NOTHING, db_column='fecha_creacion_key')
    fecha_envio_key = models.ForeignKey(DimFecha, models.DO_NOTHING, db_column='fecha_envio_key', related_name='factordencompra_fecha_envio_key_set', blank=True, null=True)
    fecha_aceptacion_key = models.ForeignKey(DimFecha, models.DO_NOTHING, db_column='fecha_aceptacion_key', related_name='factordencompra_fecha_aceptacion_key_set', blank=True, null=True)
    fecha_ultima_modificacion_key = models.ForeignKey(DimFecha, models.DO_NOTHING, db_column='fecha_ultima_modificacion_key', related_name='factordencompra_fecha_ultima_modificacion_key_set', blank=True, null=True)
    proveedor_key = models.ForeignKey(DimProveedor, models.DO_NOTHING, db_column='proveedor_key')
    comprador_key = models.ForeignKey(DimComprador, models.DO_NOTHING, db_column='comprador_key')
    orden_nombre = models.TextField(blank=True, null=True)
    orden_link = models.TextField(blank=True, null=True)
    orden_estado_codigo = models.SmallIntegerField()
    orden_estado = models.CharField(max_length=100, blank=True, null=True)
    proveedor_estado_codigo = models.SmallIntegerField()
    proveedor_estado = models.CharField(max_length=100, blank=True, null=True)
    orden_es_confirmada = models.BooleanField()
    orden_moneda = models.CharField(max_length=3, blank=True, null=True)
    orden_monto_total = models.DecimalField(max_digits=30, decimal_places=8, blank=True, null=True)
    orden_monto_total_clp = models.DecimalField(max_digits=30, decimal_places=8, blank=True, null=True)
    orden_total_neto = models.DecimalField(max_digits=30, decimal_places=8, blank=True, null=True)
    orden_cantidad_items = models.IntegerField()
    orden_fecha_carga = models.DateTimeField()

    class Meta:
        managed = False
        db_table = '"dw"."fact_orden_compra"'
