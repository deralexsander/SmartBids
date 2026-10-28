# Generated for SmartBids - Ley N° 21.719 Cumplimiento Legal y Derechos ARCOP

import django.db.models.deletion
from django.db import migrations, models


def aplicar_cambios_idempotentes(apps, schema_editor):
    """
    Verifica y crea de forma segura e idempotente las columnas y tablas requeridas
    para el cumplimiento de la Ley N° 21.719 de Protección de Datos Personales.
    Si la tabla o columnas ya existen, las conserva sin generar errores.
    """
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        # 1. Agregar columnas de trazabilidad de consentimiento en "core"."suscriptor" si no existen
        cursor.execute("""
            ALTER TABLE "core"."suscriptor"
            ADD COLUMN IF NOT EXISTS "consentimiento_terminos_fecha" TIMESTAMPTZ NULL,
            ADD COLUMN IF NOT EXISTS "consentimiento_terminos_version" VARCHAR(20) DEFAULT 'v1.0',
            ADD COLUMN IF NOT EXISTS "consentimiento_marketing" BOOLEAN DEFAULT FALSE;
        """)

        # 2. Crear tabla de auditoría y gestión de Derechos ARCOP si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "core"."smartbids_solicitud_arcop" (
                "id" BIGSERIAL PRIMARY KEY,
                "id_suscriptor" BIGINT NOT NULL REFERENCES "core"."suscriptor" ("id_suscriptor") ON DELETE CASCADE,
                "tipo_derecho" VARCHAR(20) NOT NULL,
                "detalle" TEXT NOT NULL DEFAULT '',
                "estado" VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
                "creado_el" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                "respondido_el" TIMESTAMPTZ NULL,
                "observaciones" TEXT NOT NULL DEFAULT ''
            );
        """)


def revertir_cambios_noop(apps, schema_editor):
    # Protege datos existentes en caso de rollback
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('smartbids', '0007_cambios_catalogo_preferencias'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(aplicar_cambios_idempotentes, reverse_code=revertir_cambios_noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='suscriptor',
                    name='consentimiento_terminos_fecha',
                    field=models.DateTimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='suscriptor',
                    name='consentimiento_terminos_version',
                    field=models.CharField(blank=True, default='v1.0', max_length=20, null=True),
                ),
                migrations.AddField(
                    model_name='suscriptor',
                    name='consentimiento_marketing',
                    field=models.BooleanField(default=False),
                ),
                migrations.CreateModel(
                    name='SolicitudArcop',
                    fields=[
                        ('id', models.BigAutoField(primary_key=True, serialize=False)),
                        ('tipo_derecho', models.CharField(choices=[('ACCESO', 'Acceso a Datos'), ('RECTIFICACION', 'Rectificación'), ('CANCELACION', 'Cancelación / Supresión'), ('OPOSICION', 'Oposición al Tratamiento'), ('PORTABILIDAD', 'Portabilidad de Datos')], max_length=20)),
                        ('detalle', models.TextField(blank=True, default='')),
                        ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente de Revisión'), ('PROCESADO', 'Procesado'), ('RECHAZADO', 'Rechazado')], default='PENDIENTE', max_length=20)),
                        ('creado_el', models.DateTimeField(auto_now_add=True)),
                        ('respondido_el', models.DateTimeField(blank=True, null=True)),
                        ('observaciones', models.TextField(blank=True, default='')),
                        ('id_suscriptor', models.ForeignKey(db_column='id_suscriptor', on_delete=django.db.models.deletion.CASCADE, to='smartbids.suscriptor')),
                    ],
                    options={
                        'verbose_name': 'Solicitud ARCOP',
                        'verbose_name_plural': 'Solicitudes ARCOP',
                        'db_table': '"core"."smartbids_solicitud_arcop"',
                        'managed': True,
                    },
                ),
            ],
        ),
    ]
