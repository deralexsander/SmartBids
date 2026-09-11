# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models

class ActividadEconomica(models.Model):
    codigo_actividad = models.CharField(primary_key=True, max_length=8)
    nombre_actividad = models.CharField(max_length=300)
    afecto_iva = models.CharField(max_length=2)
    categoria_tributaria = models.CharField(max_length=1)
    disponible_internet = models.BooleanField()
    activo = models.BooleanField()
    codigo_subrubro = models.ForeignKey('SubrubroActividad', models.DO_NOTHING, db_column='codigo_subrubro')

    class Meta:
        managed = False
        db_table = '"catalog"."actividad_economica"'
    def __str__(self):
        return f"{self.codigo_actividad} - {self.nombre_actividad}"

class Ambito(models.Model):
    codigo_ambito = models.CharField(primary_key=True, max_length=3)
    nombre_ambito = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = '"catalog"."ambito"'

    def __str__(self):
        return f"{self.codigo_ambito} - {self.nombre_ambito}"

class CategoriaLicitacion(models.Model):
    codigo_cat_licitacion = models.SmallAutoField(primary_key=True)
    nombre_cat_licitacion = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = '"catalog"."categoria_licitacion"'

class Comuna(models.Model):
    codigo_comuna = models.CharField(primary_key=True, max_length=5)
    nombre_comuna = models.CharField(max_length=100)
    codigo_provincia = models.ForeignKey('Provincia', models.DO_NOTHING, db_column='codigo_provincia')

    class Meta:
        managed = False
        db_table = '"catalog"."comuna"'

    def __str__(self):
        return f"{self.codigo_comuna} - {self.nombre_comuna}"


class GrupoProducto(models.Model):
    codigo_grupo_producto = models.CharField(primary_key=True, max_length=3)
    nombre_grupo_producto = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = '"catalog"."grupo_producto"'

    def __str__(self):
        return f"{self.codigo_grupo_producto} - {self.nombre_grupo_producto}"
        


class Nivel1Producto(models.Model):
    codigo_nivel1 = models.CharField(primary_key=True, max_length=10)
    descripcion = models.CharField(max_length=300, blank=True, null=True)
    codigo_grupo_producto = models.ForeignKey(GrupoProducto, models.DO_NOTHING, db_column='codigo_grupo_producto', blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"catalog"."nivel1_producto"'

    def __str__(self):
        return f"{self.codigo_nivel1} - {self.descripcion}"


class Organismo(models.Model):
    codigo_organismo = models.BigIntegerField(primary_key=True)
    activo = models.BooleanField(blank=True, null=True)
    org_nombre = models.CharField(max_length=200)
    org_sigla = models.CharField(max_length=30, blank=True, null=True)
    org_rut = models.CharField(max_length=15, blank=True, null=True)
    org_reclamos = models.IntegerField(blank=True, null=True)
    org_codigo_comuna = models.ForeignKey(Comuna, models.DO_NOTHING, db_column='org_codigo_comuna', blank=True, null=True)
    org_codigo_sector = models.ForeignKey('Sector', models.DO_NOTHING, db_column='org_codigo_sector', blank=True, null=True)
    org_direccion = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"catalog"."organismo"'

    def __str__(self):
        if self.org_sigla:
            return f"{self.codigo_organismo} - {self.org_nombre} ({self.org_sigla})"
        return f"{self.codigo_organismo} - {self.org_nombre}"

class Pais(models.Model):
    pais_codigo = models.BigAutoField(primary_key=True)
    pais_nombre = models.CharField(max_length=100)
    pais_codigo_iso2 = models.CharField(unique=True, max_length=2, blank=True, null=True)
    pais_activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = '"catalog"."pais"'

class Producto(models.Model):
    codigo_producto = models.CharField(primary_key=True, max_length=20, db_comment='codigo_producto = concatenación de nivel 1 + nivel 2 +nivel 3 + nivel 4')
    descripcion = models.CharField(max_length=255)
    codigo_unidad_medida = models.ForeignKey('UnidadMedida', models.DO_NOTHING, db_column='codigo_unidad_medida', blank=True, null=True)
    activo = models.BooleanField()
    nivel1 = models.ForeignKey(Nivel1Producto, models.DO_NOTHING, db_column='nivel1', blank=True, null=True, db_comment='utilizar como FK de nivel1_producto')
    nivel2 = models.CharField(max_length=10, blank=True, null=True)
    nivel3 = models.CharField(max_length=10, blank=True, null=True)
    nivel4 = models.CharField(max_length=10, blank=True, null=True)
    glosa_nivel2 = models.CharField(max_length=200, blank=True, null=True)
    glosa_nivel3 = models.CharField(max_length=200, blank=True, null=True)
    glosa_nivel4 = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"catalog"."producto"'
        
class Proveedor(models.Model):
    pk = models.CompositePrimaryKey('prov_codigo_proveedor', 'prov_codigo_sucursal')
    prov_codigo_proveedor = models.BigIntegerField()
    prov_codigo_sucursal = models.BigIntegerField()
    prov_rut = models.CharField(max_length=25, blank=True, null=True)
    prov_nombre = models.CharField(max_length=250, blank=True, null=True)
    prov_razon_social = models.CharField(max_length=250, blank=True, null=True)
    prov_direccion = models.CharField(max_length=200, blank=True, null=True)
    prov_codigo_comuna = models.ForeignKey(Comuna, models.DO_NOTHING, db_column='prov_codigo_comuna', blank=True, null=True)
    prov_tamano = models.CharField(max_length=50, blank=True, null=True)
    prov_codigo_pais = models.ForeignKey(Pais, models.DO_NOTHING, db_column='prov_codigo_pais', blank=True, null=True)
    prov_cod_actividad_economica = models.ForeignKey(ActividadEconomica, models.DO_NOTHING, db_column='prov_cod_actividad_economica', blank=True, null=True)
    prov_activo = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"catalog"."proveedor"'

class Provincia(models.Model):
    codigo_provincia = models.CharField(primary_key=True, max_length=3)
    nombre_provincia = models.CharField(max_length=100)
    codigo_region = models.ForeignKey('Region', models.DO_NOTHING, db_column='codigo_region')

    class Meta:
        managed = False
        db_table = '"catalog"."provincia"'

    def __str__(self):
        return f"{self.codigo_provincia} - {self.nombre_provincia}"


class Region(models.Model):
    codigo_region = models.CharField(primary_key=True, max_length=2)
    nombre_region = models.CharField(max_length=100)
    region_3l = models.CharField(db_column='region_3L', max_length=3, blank=True, null=True)  # nombre de la region resumido en 3 letras


    class Meta:
        managed = False
        db_table = '"catalog"."region"'

    def __str__(self):
        return f"{self.codigo_region} - {self.nombre_region}"

class RubroActividad(models.Model):
    codigo_rubro = models.CharField(primary_key=True, max_length=2)
    nombre_rubro = models.CharField(unique=True, max_length=200)

    class Meta:
        managed = False
        db_table = '"catalog"."rubro_actividad"'
    def __str__(self):
        return self.nombre_rubro

class Sector(models.Model):
    codigo_sector = models.CharField(primary_key=True, max_length=3)
    nombre_sector = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = '"catalog"."sector"'

    def __str__(self):
        return f"{self.codigo_sector} - {self.nombre_sector}"

class SubrubroActividad(models.Model):
    codigo_subrubro = models.CharField(primary_key=True, max_length=5)
    nombre_subrubro = models.CharField(max_length=200)
    codigo_rubro = models.ForeignKey(RubroActividad, models.DO_NOTHING, db_column='codigo_rubro')

    class Meta:
        managed = False
        db_table = '"catalog"."subrubro_actividad"'
    def __str__(self):
        return self.nombre_subrubro

class TipoLicitacion(models.Model):
    codigo_tipo_licitacion = models.CharField(primary_key=True, max_length=2)
    glosa = models.CharField(max_length=255, blank=True, null=True)
    codigo_cat_licitacion = models.ForeignKey(CategoriaLicitacion, models.DO_NOTHING, db_column='codigo_cat_licitacion')
    codigo_tramo_licitacion = models.ForeignKey('TramoLicitacion', models.DO_NOTHING, db_column='codigo_tramo_licitacion')
    activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = '"catalog"."tipo_licitacion"'

class TramoLicitacion(models.Model):
    codigo_tramo_licitacion = models.SmallAutoField(primary_key=True)
    nombre_tramo_licitacion = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = '"catalog"."tramo_licitacion"'
    
    def __str__(self):
        return self.nombre_tramo_licitacion
    


class UnidadMedida(models.Model):
    codigo_unidad_medida = models.CharField(primary_key=True, max_length=3)
    nombre_unidad_medida = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = '"catalog"."unidad_medida"'

    def __str__(self):
        return f"{self.codigo_unidad_medida} - {self.nombre_unidad_medida}"

    
        
    