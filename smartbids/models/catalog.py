# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Ambito(models.Model):
    codigo_ambito = models.CharField(primary_key=True, max_length=3)
    nombre_ambito = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'ambito'

    def __str__(self):
        return f"{self.codigo_ambito} - {self.nombre_ambito}"

class Comuna(models.Model):
    codigo_comuna = models.CharField(primary_key=True, max_length=5)
    nombre_comuna = models.CharField(max_length=100)
    codigo_provincia = models.ForeignKey('Provincia', models.DO_NOTHING, db_column='codigo_provincia')

    class Meta:
        managed = False
        db_table = 'comuna'

    def __str__(self):
        return f"{self.codigo_comuna} - {self.nombre_comuna}"


class GrupoProducto(models.Model):
    codigo_grupo_producto = models.CharField(primary_key=True, max_length=3)
    nombre_grupo_producto = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'grupo_producto'

    def __str__(self):
        return f"{self.codigo_grupo_producto} - {self.nombre_grupo_producto}"
        


class Nivel1Producto(models.Model):
    codigo_nivel1 = models.CharField(primary_key=True, max_length=10)
    descripcion = models.CharField(max_length=300, blank=True, null=True)
    codigo_grupo_producto = models.ForeignKey(GrupoProducto, models.DO_NOTHING, db_column='codigo_grupo_producto', blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'nivel1_producto'

    def __str__(self):
        return f"{self.codigo_nivel1} - {self.descripcion}"



class Nivel2Producto(models.Model):
    id_nivel2 = models.BigAutoField(primary_key=True)
    codigo_nivel1 = models.ForeignKey(Nivel1Producto, models.DO_NOTHING, db_column='codigo_nivel1')
    codigo_nivel2 = models.CharField(max_length=10)
    descripcion = models.CharField(max_length=255)
    activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'nivel2_producto'
        unique_together = (('codigo_nivel1', 'codigo_nivel2', 'descripcion'),)

    def __str__(self):
        return f"{self.codigo_nivel2} - {self.descripcion}"

class Nivel3Producto(models.Model):
    id_nivel3 = models.BigAutoField(primary_key=True)
    id_nivel2 = models.ForeignKey(Nivel2Producto, models.DO_NOTHING, db_column='id_nivel2')
    codigo_nivel3 = models.CharField(max_length=10)
    descripcion = models.CharField(max_length=255)
    activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'nivel3_producto'
        unique_together = (('id_nivel2', 'codigo_nivel3', 'descripcion'),)

    def __str__(self):
        return f"{self.codigo_nivel3} - {self.descripcion}"

class Organismo(models.Model):
    codigo_organismo = models.BigIntegerField(primary_key=True)
    activo = models.BooleanField(blank=True, null=True)
    organismo = models.CharField(max_length=200)
    sigla = models.CharField(max_length=30, blank=True, null=True)
    rut = models.CharField(max_length=15)
    descripcion = models.TextField(blank=True, null=True)
    reclamos = models.IntegerField(blank=True, null=True)
    codigo_comuna = models.ForeignKey(Comuna, models.DO_NOTHING, db_column='codigo_comuna', blank=True, null=True)
    codigo_sector = models.ForeignKey('Sector', models.DO_NOTHING, db_column='codigo_sector', blank=True, null=True)
    direccion = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'organismo'

    def __str__(self):
        if self.sigla:
            return f"{self.codigo_organismo} - {self.organismo} ({self.sigla})"
        return f"{self.codigo_organismo} - {self.organismo}"

class Producto(models.Model):
    codigo_producto = models.CharField(primary_key=True, max_length=20)
    id_nivel3 = models.ForeignKey(Nivel3Producto, models.DO_NOTHING, db_column='id_nivel3')
    codigo_nivel4 = models.CharField(max_length=10)
    descripcion = models.CharField(max_length=255)
    codigo_unidad_medida = models.ForeignKey('UnidadMedida', models.DO_NOTHING, db_column='codigo_unidad_medida', blank=True, null=True)
    activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'producto'

    def __str__(self):
        return f"{self.codigo_producto} - {self.descripcion}"


class Provincia(models.Model):
    codigo_provincia = models.CharField(primary_key=True, max_length=3)
    nombre_provincia = models.CharField(max_length=100)
    codigo_region = models.ForeignKey('Region', models.DO_NOTHING, db_column='codigo_region')

    class Meta:
        managed = False
        db_table = 'provincia'

    def __str__(self):
        return f"{self.codigo_provincia} - {self.nombre_provincia}"


class Region(models.Model):
    codigo_region = models.CharField(primary_key=True, max_length=2)
    nombre_region = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'region'

    def __str__(self):
        return f"{self.codigo_region} - {self.nombre_region}"


class Sector(models.Model):
    codigo_sector = models.CharField(primary_key=True, max_length=3)
    nombre_sector = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'sector'

    def __str__(self):
        return f"{self.codigo_sector} - {self.nombre_sector}"

class TipoLicitacion(models.Model):
    codigo_tipo_licitacion = models.SmallAutoField(primary_key=True)
    nombre_tipo_licitacion = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'tipo_licitacion'

    def __str__(self):
        return self.nombre_tipo_licitacion

class TipoProcedimiento(models.Model):
    codigo_procedimiento = models.CharField(primary_key=True, max_length=2)
    glosa = models.CharField(max_length=255, blank=True, null=True)
    codigo_tipo_licitacion = models.ForeignKey(TipoLicitacion, models.DO_NOTHING, db_column='codigo_tipo_licitacion')
    codigo_tramo_licitacion = models.ForeignKey('TramoLicitacion', models.DO_NOTHING, db_column='codigo_tramo_licitacion')
    activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'tipo_procedimiento'

    def __str__(self):
        return f"{self.codigo_procedimiento} - {self.glosa}"


class TramoLicitacion(models.Model):
    codigo_tramo_licitacion = models.SmallAutoField(primary_key=True)
    nombre_tramo_licitacion = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'tramo_licitacion'

    def __str__(self):
        return self.nombre_tramo_licitacion



class UnidadMedida(models.Model):
    codigo_unidad_medida = models.CharField(primary_key=True, max_length=3)
    nombre_unidad_medida = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'unidad_medida'

    def __str__(self):
        return f"{self.codigo_unidad_medida} - {self.nombre_unidad_medida}"