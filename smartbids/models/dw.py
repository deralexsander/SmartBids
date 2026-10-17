"""Modelos del DW actual para Django 5.2+. Tablas administradas por ETL.

Consultar con .using("dw"). managed=False no bloquea escrituras: para
lectura exclusiva, usar un usuario PostgreSQL con permisos SELECT.
Los numeric sin escala se declaran con límites amplios para el ORM;
no se altera su definición SQL ni se redondean aquí los datos leídos.
"""
from django.db import models



class DimComprador(models.Model):
    comprador_key = models.AutoField(primary_key=True)
    comprador_organismo_codigo = models.BigIntegerField(unique=True)
    comprador_organismo_nombre = models.CharField(max_length=200, blank=True, null=True)
    comprador_sector = models.CharField(max_length=100, blank=True, null=True)
    comprador_comuna = models.CharField(max_length=100, blank=True, null=True)
    comprador_region = models.CharField(max_length=100, blank=True, null=True)
    comprador_org_sigla = models.CharField(max_length=50, blank=True, null=True)
    comprador_provincia = models.CharField(max_length=100, blank=True, null=True)
    comprador_pais = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"dw"."dim_comprador"'



class DimFecha(models.Model):
    fecha_key = models.AutoField(primary_key=True)
    fecha = models.DateField(unique=True)
    dia = models.SmallIntegerField(blank=True, null=True)
    dia_semana = models.SmallIntegerField(blank=True, null=True)
    nombre_dia = models.CharField(max_length=10, blank=True, null=True)
    nombre_dia_corto = models.CharField(max_length=3, blank=True, null=True)
    mes = models.SmallIntegerField(blank=True, null=True)
    nombre_mes = models.CharField(max_length=10, blank=True, null=True)
    nombre_mes_corto = models.CharField(max_length=3, blank=True, null=True)
    trimestre = models.SmallIntegerField(blank=True, null=True)
    semestre = models.SmallIntegerField(blank=True, null=True)
    anio = models.SmallIntegerField(blank=True, null=True)
    anio_mes = models.CharField(max_length=7, blank=True, null=True)
    es_fin_semana = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"dw"."dim_fecha"'



class DimProducto(models.Model):
    producto_key = models.AutoField(primary_key=True)
    producto_codigo = models.CharField(max_length=12, unique=True)
    producto_descripcion = models.CharField(max_length=300)
    producto_grupo = models.CharField(max_length=100, blank=True, null=True)
    producto_nivel1 = models.CharField(max_length=200, blank=True, null=True)
    producto_nivel2 = models.CharField(max_length=200, blank=True, null=True)
    producto_nivel3 = models.CharField(max_length=200, blank=True, null=True)
    producto_nivel4 = models.CharField(max_length=200, blank=True, null=True)
    nombre_unidad_medida = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"dw"."dim_producto"'



class DimProveedor(models.Model):
    proveedor_key = models.AutoField(primary_key=True)
    proveedor_nombre = models.CharField(max_length=250, blank=True, null=True)
    proveedor_comuna = models.CharField(max_length=100, blank=True, null=True)
    proveedor_region = models.CharField(max_length=100, blank=True, null=True)
    proveedor_pais = models.CharField(max_length=100, blank=True, null=True)
    proveedor_provincia = models.CharField(max_length=100, blank=True, null=True)
    proveedor_actividad_econ = models.CharField(max_length=300, blank=True, null=True)
    proveedor_rubro = models.CharField(max_length=200, blank=True, null=True)
    proveedor_subrubro = models.CharField(max_length=200, blank=True, null=True)
    proveedor_codigo = models.BigIntegerField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"dw"."dim_proveedor"'



class DimTipoOrdenCompra(models.Model):
    tipo_orden_compra_key = models.AutoField(primary_key=True)
    codigo_tipo = models.IntegerField(unique=True)
    codigo_abreviado_tipo_oc = models.CharField(max_length=20, blank=True, null=True)
    descripcion_tipo_oc = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"dw"."dim_tipo_orden_compra"'





class FactOrdenCompra(models.Model):
    pk = models.CompositePrimaryKey("fecha_key_id", "proveedor_key_id", "comprador_key_id", "tipo_orden_compra_key_id", "producto_key_id")
    fecha_key = models.ForeignKey(DimFecha, models.DO_NOTHING, db_column="fecha_key", related_name="compras_agrupadas")
    proveedor_key = models.ForeignKey(DimProveedor, models.DO_NOTHING, db_column="proveedor_key", related_name="compras_agrupadas")
    comprador_key = models.ForeignKey(DimComprador, models.DO_NOTHING, db_column="comprador_key", related_name="compras_agrupadas")
    tipo_orden_compra_key = models.ForeignKey(DimTipoOrdenCompra, models.DO_NOTHING, db_column="tipo_orden_compra_key", related_name="compras_agrupadas")
    producto_key = models.ForeignKey(DimProducto, models.DO_NOTHING, db_column="producto_key", related_name="compras_agrupadas")
    monto_neto = models.DecimalField(max_digits=1000, decimal_places=60, blank=True, null=True)
    impuesto = models.DecimalField(max_digits=1000, decimal_places=60, blank=True, null=True)
    monto_bruto = models.DecimalField(max_digits=1000, decimal_places=60, blank=True, null=True)
    cantidad_productos = models.DecimalField(max_digits=1000, decimal_places=60, blank=True, null=True)
    precio_unitario = models.DecimalField(max_digits=1000, decimal_places=60, blank=True, null=True)
    cantidad_ordenes_compra = models.IntegerField(blank=True, null=True)
    cantidad_items = models.IntegerField(blank=True, null=True)
    costo = models.DecimalField(max_digits=1000, decimal_places=60, blank=True, null=True)
    descuento = models.DecimalField(max_digits=1000, decimal_places=60, blank=True, null=True)
    monto_item_origen = models.DecimalField(max_digits=1000, decimal_places=60, blank=True, null=True)
    monto_item_pesos = models.DecimalField(max_digits=1000, decimal_places=60, blank=True, null=True)
    monto_item_utm = models.DecimalField(max_digits=1000, decimal_places=60, blank=True, null=True)
    total_oc_procesadas = models.BigIntegerField(null=True,blank=True)
    monto_total_procesado_clp = models.DecimalField(max_digits=50,decimal_places=10,null=True,blank=True)

    class Meta:
        managed = False
        db_table = '"dw"."fact_orden_compra"'
