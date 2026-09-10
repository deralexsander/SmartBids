from django.db import models
from .config import EstadoSuscriptor
from .catalog import Comuna, ActividadEconomica, Producto, Organismo


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
        db_table = '"core"."empresa"'

class Suscriptor(models.Model):
    id_suscriptor = models.BigAutoField(primary_key=True)
    firebase_uid = models.CharField(unique=True, max_length=128)
    fecha_registro = models.DateTimeField()
    fecha_actualizacion = models.DateTimeField()
    codigo_estado = models.SmallIntegerField() #falta unir con la fk 
    sus_nombre1 = models.CharField(max_length=100)
    sus_apellido1 = models.CharField(max_length=100)
    sus_apellido2 = models.CharField(max_length=100, blank=True, null=True)
    sus_rut_empresa = models.ForeignKey(Empresa, models.DO_NOTHING, db_column='sus_rut_empresa', blank=True, null=True)
    sus_nombre_social = models.CharField(max_length=100, blank=True, null=True)
    sus_iniciales = models.CharField(max_length=5, blank=True, null=True)
    sus_nombre2 = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"core"."suscriptor"'

    def __str__(self):
        return f"Suscriptor {self.id_suscriptor} - {self.estado_suscriptor.nombre_estado}"


class Preferencia(models.Model):
    id_suscriptor = models.OneToOneField('Suscriptor', models.DO_NOTHING, db_column='id_suscriptor', primary_key=True)
    pref_ucom = models.TextField(blank=True, null=True)  # This field type is a guess. aca hay que ver como poner un array
    pref_comunas = models.TextField(blank=True, null=True)  # This field type is a guess.
    pref_tipo_licitacion = models.TextField(blank=True, null=True)  # This field type is a guess.
    pref_productos = models.TextField(blank=True, null=True)  # This field type is a guess.
    pref_palabras_claves = models.TextField(blank=True, null=True, db_comment='poner un límite de palabras claves, ej: 20')  # This field type is a guess.

    class Meta:
        managed = False
        db_table = '"core"."preferencia"'