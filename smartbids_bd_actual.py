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
        db_table = 'actividad_economica'


class Ambito(models.Model):
    codigo_ambito = models.CharField(primary_key=True, max_length=3)
    nombre_ambito = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'ambito'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class CategoriaLicitacion(models.Model):
    codigo_cat_licitacion = models.SmallAutoField(primary_key=True)
    nombre_cat_licitacion = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'categoria_licitacion'


class Comuna(models.Model):
    codigo_comuna = models.CharField(primary_key=True, max_length=5)
    nombre_comuna = models.CharField(max_length=100)
    codigo_provincia = models.ForeignKey('Provincia', models.DO_NOTHING, db_column='codigo_provincia')

    class Meta:
        managed = False
        db_table = 'comuna'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class Empresa(models.Model):
    emp_rut = models.CharField(primary_key=True, max_length=15)
    emp_razon_social = models.CharField(max_length=200)
    emp_nombre_fantasia = models.CharField(max_length=200)
    emp_iniciales = models.CharField(max_length=20)
    emp_contacto_correo = models.CharField(max_length=254)
    emp_direccion = models.CharField(max_length=300, blank=True, null=True)
    emp_codigo_comuna = models.CharField(max_length=5, blank=True, null=True)
    emp_contacto_nombre = models.CharField(max_length=100, blank=True, null=True)
    emp_contacto_telefono = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'empresa'


class EstadoSuscriptor(models.Model):
    codigo_estado = models.SmallAutoField(primary_key=True)
    nombre_estado = models.CharField(unique=True, max_length=30)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'estado_suscriptor'


class GrupoProducto(models.Model):
    codigo_grupo_producto = models.CharField(primary_key=True, max_length=3)
    nombre_grupo_producto = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'grupo_producto'


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
        db_table = 'licitacion'


class LicitacionesProductos(models.Model):
    pk = models.CompositePrimaryKey('lic_codigo', 'codigo_producto')
    lic_codigo = models.ForeignKey(Licitacion, models.DO_NOTHING, db_column='lic_codigo')
    codigo_producto = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'licitaciones_productos'


class Mensajeria(models.Model):
    id = models.BigAutoField(primary_key=True)
    asunto = models.CharField(max_length=200)
    cuerpo = models.TextField()
    estado = models.CharField(max_length=20)
    tipo_alerta = models.CharField(max_length=20)
    creado_el = models.DateTimeField()
    actualizado_el = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'mensajeria'


class Nivel1Producto(models.Model):
    codigo_nivel1 = models.CharField(primary_key=True, max_length=10)
    descripcion = models.CharField(max_length=300, blank=True, null=True)
    codigo_grupo_producto = models.ForeignKey(GrupoProducto, models.DO_NOTHING, db_column='codigo_grupo_producto', blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'nivel1_producto'


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
        db_table = 'organismo'


class Pais(models.Model):
    pais_codigo = models.BigAutoField(primary_key=True)
    pais_nombre = models.CharField(max_length=100)
    pais_codigo_iso2 = models.CharField(unique=True, max_length=2, blank=True, null=True)
    pais_activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'pais'


class Preferencia(models.Model):
    id_suscriptor = models.OneToOneField('Suscriptor', models.DO_NOTHING, db_column='id_suscriptor', primary_key=True)
    pref_ucom = models.TextField(blank=True, null=True)  # This field type is a guess.
    pref_comunas = models.TextField(blank=True, null=True)  # This field type is a guess.
    pref_tipo_licitacion = models.TextField(blank=True, null=True)  # This field type is a guess.
    pref_productos = models.TextField(blank=True, null=True)  # This field type is a guess.
    pref_palabras_claves = models.TextField(blank=True, null=True, db_comment='poner un límite de palabras claves, ej: 20')  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'preferencia'


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
        db_table = 'producto'


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
        db_table = 'proveedor'


class Provincia(models.Model):
    codigo_provincia = models.CharField(primary_key=True, max_length=3)
    nombre_provincia = models.CharField(max_length=100)
    codigo_region = models.ForeignKey('Region', models.DO_NOTHING, db_column='codigo_region')

    class Meta:
        managed = False
        db_table = 'provincia'


class Region(models.Model):
    codigo_region = models.CharField(primary_key=True, max_length=2)
    nombre_region = models.CharField(max_length=100)
    region_3l = models.CharField(db_column='region_3L', max_length=3, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'region'


class RubroActividad(models.Model):
    codigo_rubro = models.CharField(primary_key=True, max_length=2)
    nombre_rubro = models.CharField(unique=True, max_length=200)

    class Meta:
        managed = False
        db_table = 'rubro_actividad'


class Sector(models.Model):
    codigo_sector = models.CharField(primary_key=True, max_length=3)
    nombre_sector = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'sector'


class SubrubroActividad(models.Model):
    codigo_subrubro = models.CharField(primary_key=True, max_length=5)
    nombre_subrubro = models.CharField(max_length=200)
    codigo_rubro = models.ForeignKey(RubroActividad, models.DO_NOTHING, db_column='codigo_rubro')

    class Meta:
        managed = False
        db_table = 'subrubro_actividad'


class Suscriptor(models.Model):
    id_suscriptor = models.BigAutoField(primary_key=True)
    firebase_uid = models.CharField(unique=True, max_length=128)
    fecha_registro = models.DateTimeField()
    fecha_actualizacion = models.DateTimeField()
    codigo_estado = models.SmallIntegerField()
    sus_nombre1 = models.CharField(max_length=100)
    sus_apellido1 = models.CharField(max_length=100)
    sus_apellido2 = models.CharField(max_length=100, blank=True, null=True)
    sus_rut_empresa = models.ForeignKey(Empresa, models.DO_NOTHING, db_column='sus_rut_empresa', blank=True, null=True)
    sus_nombre_social = models.CharField(max_length=100, blank=True, null=True)
    sus_iniciales = models.CharField(max_length=5, blank=True, null=True)
    sus_nombre2 = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'suscriptor'


class TipoLicitacion(models.Model):
    codigo_tipo_licitacion = models.CharField(primary_key=True, max_length=2)
    glosa = models.CharField(max_length=255, blank=True, null=True)
    codigo_cat_licitacion = models.ForeignKey(CategoriaLicitacion, models.DO_NOTHING, db_column='codigo_cat_licitacion')
    codigo_tramo_licitacion = models.ForeignKey('TramoLicitacion', models.DO_NOTHING, db_column='codigo_tramo_licitacion')
    activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'tipo_licitacion'


class TramoLicitacion(models.Model):
    codigo_tramo_licitacion = models.SmallAutoField(primary_key=True)
    nombre_tramo_licitacion = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'tramo_licitacion'


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
        db_table = 'unidad_compra'


class UnidadMedida(models.Model):
    codigo_unidad_medida = models.CharField(primary_key=True, max_length=3)
    nombre_unidad_medida = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'unidad_medida'
