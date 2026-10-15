import csv
from datetime import date, datetime, time, timezone as datetime_timezone
from io import StringIO

from django.test import SimpleTestCase, override_settings

from .licitacion_utils import estado_licitacion, escribir_fila_csv
from .models.procurement import Licitacion
from .templatetags.montos import miles_chilenos


@override_settings(TIME_ZONE='UTC')
class EstadoLicitacionTests(SimpleTestCase):
    ahora = datetime(2026, 10, 13, 12, 0, tzinfo=datetime_timezone.utc)

    def test_calcula_periodo_de_preguntas(self):
        licitacion = Licitacion(
            lic_fecha_cierre=date(2026, 10, 20),
            lic_fecha_preguntas=datetime(2026, 10, 13, 11, 0, tzinfo=datetime_timezone.utc),
            lic_fecha_respuestas=datetime(2026, 10, 14, 11, 0, tzinfo=datetime_timezone.utc),
        )
        self.assertEqual(estado_licitacion(licitacion, self.ahora), ('preguntas', 'Período de preguntas'))

    def test_calcula_recepcion_de_ofertas(self):
        licitacion = Licitacion(
            lic_fecha_cierre=date(2026, 10, 20),
            lic_fecha_respuestas=datetime(2026, 10, 13, 11, 0, tzinfo=datetime_timezone.utc),
        )
        self.assertEqual(estado_licitacion(licitacion, self.ahora)[0], 'ofertas')

    def test_acepta_fechas_legacy_sin_zona_horaria(self):
        licitacion = Licitacion(
            lic_fecha_cierre=date(2026, 10, 20),
            lic_fecha_preguntas=datetime(2026, 10, 13, 11, 0),
            lic_fecha_respuestas=datetime(2026, 10, 14, 11, 0),
        )
        self.assertEqual(estado_licitacion(licitacion, self.ahora)[0], 'preguntas')

    def test_cierre_tiene_precedencia_sobre_otros_hitos(self):
        licitacion = Licitacion(
            lic_fecha_cierre=date(2026, 10, 12),
            lic_fecha_respuestas=datetime(2026, 10, 13, 11, 0, tzinfo=datetime_timezone.utc),
        )
        self.assertEqual(estado_licitacion(licitacion, self.ahora)[0], 'cerrada')

    def test_estado_inicial_si_no_hay_hitos_vencidos(self):
        licitacion = Licitacion(
            lic_fecha_public=date(2026, 10, 13),
            lic_fecha_cierre=date(2026, 10, 20),
            lic_hora_cierre=time(17, 0),
        )
        self.assertEqual(estado_licitacion(licitacion, self.ahora)[0], 'publicada')

    def test_exportacion_csv_protege_formulas_de_hoja_de_calculo(self):
        output = StringIO()
        writer = csv.writer(output)
        escribir_fila_csv(writer, ('=1+1', 'Texto normal'))
        self.assertEqual(next(csv.reader(StringIO(output.getvalue()))), ["'=1+1", 'Texto normal'])


class FormatoMontosTests(SimpleTestCase):
    def test_formatea_montos_con_separador_de_miles_chileno(self):
        self.assertEqual(miles_chilenos('125000000'), '125.000.000')

    def test_redondea_montos_sin_decimales(self):
        self.assertEqual(miles_chilenos('125000000.50'), '125.000.001')
