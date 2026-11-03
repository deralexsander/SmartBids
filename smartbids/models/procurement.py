
from django.db import models
from django.contrib.postgres.fields import ArrayField


class UnidadCompra(models.Model):
    codigo_unidad_compra = models.BigIntegerField(primary_key=True)
    ucom_activo = models.BooleanField(blank=True, null=True)
    ucom_codigo_ambito = models.CharField(max_length=3, blank=True, null=True)
    ucom_codigo_organismo = models.BigIntegerField(blank=True, null=True)
    ucom_rut = models.CharField(max_length=15, blank=True, null=True)
    ucom_direccion = models.CharField(max_length=300, blank=True, null=True)
    ucom_codigo_comuna = models.CharField(max_length=5, blank=True, null=True)
    ucom_descripcion = models.CharField(max_length=300, blank=True, null=True)

    @property
    def nombre_comuna(self):
        """Retorna el nombre legible de la comuna asociada a la unidad de compra."""
        if not self.ucom_codigo_comuna:
            return ''
        from smartbids.utils.licitacion_utils import obtener_nombre_comuna
        return obtener_nombre_comuna(self.ucom_codigo_comuna)

    @property
    def ucom_nombre_comuna(self):
        return self.nombre_comuna

    class Meta:
        managed = True
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
    lic_codigos_producto = ArrayField(models.CharField(max_length=20),blank=True,null=True)
    lic_diccionario_palabras = ArrayField(models.CharField(max_length=100),blank=True,null=True)
    lic_texto = models.TextField(blank=True, null=True)
    lic_url = models.TextField(blank=True, null=True)
    lic_plazo = models.IntegerField(blank=True, null=True)
    lic_estado = models.ForeignKey('EstadoLicitacion',models.DO_NOTHING,db_column='lic_estado',blank=True,null=True)

    @property
    def es_cierre_proximo(self):
        """Retorna True si la licitación cierra dentro de los próximos 3 días a contar de hoy."""
        if hasattr(self, '_es_cierre_proximo'):
            return self._es_cierre_proximo
        if not self.lic_fecha_cierre:
            return False
        from datetime import date, datetime, timedelta
        from django.utils import timezone
        fecha = self.lic_fecha_cierre
        if isinstance(fecha, datetime):
            fecha = fecha.date()
        if not isinstance(fecha, date):
            return False
        hoy = timezone.localdate()
        return hoy <= fecha <= hoy + timedelta(days=3)

    @es_cierre_proximo.setter
    def es_cierre_proximo(self, valor):
        self._es_cierre_proximo = bool(valor)

    @property
    def nombre_comuna(self):
        """Retorna el nombre de la comuna de la unidad de compra emisora."""
        if self.lic_codigo_ucom:
            return getattr(self.lic_codigo_ucom, 'nombre_comuna', '')
        return ''

    class Meta:
        managed = True
        db_table = '"procurement"."licitacion"'
        
class LicitacionesProductos(models.Model):
    pk = models.CompositePrimaryKey('lic_codigo', 'codigo_producto')
    lic_codigo = models.ForeignKey(Licitacion, models.DO_NOTHING, db_column='lic_codigo')
    codigo_producto = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = '"procurement"."licitaciones_productos"'