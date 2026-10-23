from django.contrib.postgres.fields import ArrayField
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('smartbids', '0005_crear_config_faltante'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='licitacion',
                    name='lic_codigos_producto',
                    field=ArrayField(
                        models.CharField(max_length=20),
                        blank=True,
                        null=True,
                    ),
                ),
                migrations.AlterField(
                    model_name='licitacion',
                    name='lic_diccionario_palabras',
                    field=ArrayField(
                        models.CharField(max_length=100),
                        blank=True,
                        null=True,
                    ),
                ),
            ],
        ),
    ]