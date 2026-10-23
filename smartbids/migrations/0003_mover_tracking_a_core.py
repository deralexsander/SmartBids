from django.db import migrations


TABLAS = (
    'smartbids_seguimiento_licitacion',
    'smartbids_notificacion_licitacion',
    'smartbids_licitacion_documento',
    'smartbids_licitacion_pregunta',
)


def mover_a_core(apps, schema_editor, dry_run=False):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        raise RuntimeError('El traslado requiere PostgreSQL.')
    quote = schema_editor.quote_name
    plan = []
    with connection.cursor() as cursor:
        # Check every table before moving any of them. Never choose silently
        # between two copies of the same table.
        for tabla in TABLAS:
            cursor.execute(
                "SELECT n.nspname, c.relkind FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relname = %s AND n.nspname IN ('public', 'tracking', 'core')",
                [tabla],
            )
            matches = cursor.fetchall()
            if len(matches) != 1:
                raise RuntimeError(
                    f'{tabla}: se esperaba una sola tabla en public, tracking o core; '
                    f'se encontraron {matches}. No se trasladó ninguna tabla.'
                )
            source, kind = matches[0]
            if kind not in ('r', 'p'):
                raise RuntimeError(f'{source}.{tabla} no es una tabla PostgreSQL.')
            plan.append((source, tabla))
        if dry_run:
            return plan
        cursor.execute('CREATE SCHEMA IF NOT EXISTS core')
        for source, tabla in plan:
            if source != 'core':
                cursor.execute(
                    f'ALTER TABLE {quote(source)}.{quote(tabla)} SET SCHEMA {quote("core")}'
                )


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ('smartbids', '0002_licitacion_tracking'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # Intentionally irreversible: the source schema varies by DB.
                migrations.RunPython(mover_a_core),
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
