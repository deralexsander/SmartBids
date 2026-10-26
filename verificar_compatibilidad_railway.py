"""Run through manage.py shell. Only SELECT queries; no migrate, DDL or DML."""
import importlib
from contextlib import contextmanager
from types import SimpleNamespace
from django.db import connections
from django.db.migrations.loader import MigrationLoader

connection = connections['default']
if connection.vendor != 'postgresql':
    raise RuntimeError('Se requiere PostgreSQL.')
editor = SimpleNamespace(connection=connection, quote_name=connection.ops.quote_name)
m3 = importlib.import_module('smartbids.migrations.0003_mover_tracking_a_core')
m4 = importlib.import_module('smartbids.migrations.0004_conciliar_modelos')
m5 = importlib.import_module('smartbids.migrations.0005_crear_config_faltante')
loader = MigrationLoader(connection)
state = loader.project_state([('smartbids', '0005_crear_config_faltante')])
plan = m3.mover_a_core(state.apps, editor, dry_run=True)
for source, table in plan:
    print(f'Seguimiento: {source}.{table} -> core (sin ejecutar)')
# 0004 runs after the move. For this read-only check, resolve its core table
# names to the existing source OIDs, without physically moving anything.
sources = {'"core"."' + table + '"': '"' + source + '"."' + table + '"' for source, table in plan}


class CursorAfterMove:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, sql, params=None):
        if 'to_regclass' in sql and params:
            params = [sources.get(params[0], params[0]), *params[1:]]
        return self.cursor.execute(sql, params)

    def __getattr__(self, name):
        return getattr(self.cursor, name)


@contextmanager
def cursor_after_move():
    with connection.cursor() as cursor:
        yield CursorAfterMove(cursor)


after_move_editor = SimpleNamespace(connection=SimpleNamespace(vendor='postgresql', cursor=cursor_after_move))
m4.comprobar_base(state.apps, after_move_editor)
print('OK: tablas y columnas operacionales presentes (no certifica todos sus tipos/constraints).')
pending = m5.planificar_config(state.apps, editor)
print('Tablas config que se crearían:', ', '.join(m._meta.db_table for m in pending) or 'ninguna')
print('OK: tablas config existentes compatibles con las comprobaciones de 0005.')
print('No se modificó la BD. Falta probar migrate completo sobre una copia de Railway.')
