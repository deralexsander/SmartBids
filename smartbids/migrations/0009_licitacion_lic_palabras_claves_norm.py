# Generated for SmartBids - Habilitar campo de palabras claves normalizadas en licitaciones

import django.contrib.postgres.fields
from django.db import migrations, models


def agregar_columna_lic_palabras_claves_norm(apps, schema_editor):
    """
    Agrega de forma idempotente la columna lic_palabras_claves_norm a la tabla procurement.licitacion.
    """
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE "procurement"."licitacion"
            ADD COLUMN IF NOT EXISTS "lic_palabras_claves_norm" character varying(100)[] NULL;
            
            COMMENT ON COLUMN "procurement"."licitacion"."lic_palabras_claves_norm" 
            IS 'conjunto de palabras claves normalizadas de la licitacion';
        """)


def revertir_columna_lic_palabras_claves_norm(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE "procurement"."licitacion"
            DROP COLUMN IF EXISTS "lic_palabras_claves_norm";
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('smartbids', '0008_cumplimiento_legal_arcop'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='licitacion',
                    name='lic_palabras_claves_norm',
                    field=django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=100),
                        blank=True,
                        db_comment='conjunto de palabras claves normalizadas de la licitacion',
                        null=True,
                        size=None
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    agregar_columna_lic_palabras_claves_norm,
                    reverse_code=revertir_columna_lic_palabras_claves_norm
                ),
            ],
        ),
    ]
