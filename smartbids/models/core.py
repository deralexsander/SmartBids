from django.db import models
from .config import EstadoSuscriptor, TipoPreferencia
from .catalog import Comuna, ActividadEconomica, Producto, Organismo

class Suscriptor(models.Model):
    id_suscriptor = models.BigAutoField(primary_key=True)

    firebase_uid = models.CharField(
        max_length=128,
        unique=True
    )

    estado_suscriptor = models.ForeignKey(
        EstadoSuscriptor,
        on_delete=models.PROTECT,
        db_column='codigo_estado'
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = '"core"."suscriptor"'

    def __str__(self):
        return f"Suscriptor {self.id_suscriptor} - {self.estado_suscriptor.nombre_estado}"

class Empresa(models.Model):
    id_empresa = models.BigAutoField(primary_key=True)

    suscriptor = models.OneToOneField(
        Suscriptor,
        on_delete=models.PROTECT,
        db_column='id_suscriptor'
    )

    rut = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True
    )

    razon_social = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    nombre_empresa = models.CharField(
        max_length=200
    )

    inicial_empresa = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    correo_destinatario = models.EmailField(
        help_text='Correo principal para recibir notificaciones de SmartBids.'
    )

    comuna = models.ForeignKey(
        Comuna,
        on_delete=models.PROTECT,
        db_column='codigo_comuna',
        blank=True,
        null=True
    )

    direccion = models.CharField(
        max_length=300,
        blank=True,
        null=True
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = '"core"."empresa"'

    def __str__(self):
        return self.nombre_empresa


class EmpresaCorreoCopia(models.Model):
    id_correo_copia = models.BigAutoField(primary_key=True)

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        db_column='id_empresa',
        related_name='correos_copia'
    )

    correo = models.EmailField()

    class Meta:
        db_table = '"core"."empresa_correo_copia"'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'correo'],
                name='uq_empresa_correo_copia'
            )
        ]

    def __str__(self):
        return self.correo


class EmpresaActividadEconomica(models.Model):
    id_empresa_actividad = models.BigAutoField(primary_key=True)

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        db_column='id_empresa'
    )

    actividad_economica = models.ForeignKey(
        ActividadEconomica,
        on_delete=models.PROTECT,
        db_column='codigo_actividad'
    )

    principal = models.BooleanField(default=False)

    class Meta:
        db_table = '"core"."empresa_actividad_economica"'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'actividad_economica'],
                name='uq_empresa_actividad'
            )
        ]

    def __str__(self):
        return f"{self.empresa} - {self.actividad_economica}"

class EmpresaProducto(models.Model):
    id_empresa_producto = models.BigAutoField(primary_key=True)

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        db_column='id_empresa'
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column='codigo_producto'
    )

    tipo_preferencia = models.ForeignKey(
        TipoPreferencia,
        on_delete=models.PROTECT,
        db_column='codigo_tipo_preferencia'
    )

    class Meta:
        db_table = '"core"."empresa_producto"'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'producto'],
                name='uq_empresa_producto'
            )
        ]

    def __str__(self):
        return f"{self.empresa} - {self.producto} - {self.tipo_preferencia}"

class EmpresaOrganismo(models.Model):
    id_empresa_organismo = models.BigAutoField(primary_key=True)

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        db_column='id_empresa'
    )

    organismo = models.ForeignKey(
        Organismo,
        on_delete=models.PROTECT,
        db_column='codigo_organismo'
    )

    tipo_preferencia = models.ForeignKey(
        TipoPreferencia,
        on_delete=models.PROTECT,
        db_column='codigo_tipo_preferencia'
    )

    class Meta:
        db_table = '"core"."empresa_organismo"'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'organismo'],
                name='uq_empresa_organismo'
            )
        ]

    def __str__(self):
        return f"{self.empresa} - {self.organismo} - {self.tipo_preferencia}"


class EmpresaPalabraClave(models.Model):
    id_empresa_palabra = models.BigAutoField(primary_key=True)

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        db_column='id_empresa'
    )

    palabra = models.CharField(
        max_length=100
    )

    tipo_preferencia = models.ForeignKey(
        TipoPreferencia,
        on_delete=models.PROTECT,
        db_column='codigo_tipo_preferencia'
    )

    class Meta:
        db_table = '"core"."empresa_palabra_clave"'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'palabra'],
                name='uq_empresa_palabra'
            )
        ]

    def __str__(self):
        return f"{self.palabra} - {self.tipo_preferencia}"
