from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('smartbids', '0002_licitacion_tracking'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE tracking.smartbids_seguimiento_licitacion
                        SET SCHEMA core;

                        ALTER TABLE tracking.smartbids_notificacion_licitacion
                        SET SCHEMA core;

                        ALTER TABLE tracking.smartbids_licitacion_documento
                        SET SCHEMA core;

                        ALTER TABLE tracking.smartbids_licitacion_pregunta
                        SET SCHEMA core;
                    """,
                    reverse_sql="""
                        ALTER TABLE core.smartbids_licitacion_pregunta
                        SET SCHEMA tracking;

                        ALTER TABLE core.smartbids_licitacion_documento
                        SET SCHEMA tracking;

                        ALTER TABLE core.smartbids_notificacion_licitacion
                        SET SCHEMA tracking;

                        ALTER TABLE core.smartbids_seguimiento_licitacion
                        SET SCHEMA tracking;
                    """,
                ),
            ],
            state_operations=[
                migrations.AlterModelTable(
                    name='seguimientolicitacion',
                    table='"core"."smartbids_seguimiento_licitacion"',
                ),
                migrations.AlterModelTable(
                    name='notificacionlicitacion',
                    table='"core"."smartbids_notificacion_licitacion"',
                ),
                migrations.AlterModelTable(
                    name='licitaciondocumento',
                    table='"core"."smartbids_licitacion_documento"',
                ),
                migrations.AlterModelTable(
                    name='licitacionpregunta',
                    table='"core"."smartbids_licitacion_pregunta"',
                ),
            ],
        ),
    ]