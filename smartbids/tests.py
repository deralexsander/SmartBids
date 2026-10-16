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

    def test_exportacion_excel_genera_archivo_y_protege_formulas(self):
        from io import BytesIO
        import openpyxl
        from .licitacion_utils import generar_excel_response

        response = generar_excel_response(
            'test.xlsx',
            ('Columna 1', 'Columna 2'),
            [('=SUM(A1:A2)', 'Texto simple'), ('@link', 123)]
        )
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('test.xlsx', response['Content-Disposition'])

        wb = openpyxl.load_workbook(BytesIO(response.content))
        ws = wb.active
        self.assertEqual(ws.cell(row=1, column=1).value, 'Columna 1')
        self.assertEqual(ws.cell(row=2, column=1).value, "'=SUM(A1:A2)")
        self.assertEqual(ws.cell(row=2, column=2).value, 'Texto simple')
        self.assertEqual(ws.cell(row=3, column=1).value, "'@link")
        self.assertEqual(ws.cell(row=3, column=2).value, 123)


class FormatoMontosTests(SimpleTestCase):
    def test_formatea_montos_con_separador_de_miles_chileno(self):
        self.assertEqual(miles_chilenos('125000000'), '125.000.000')

    def test_redondea_montos_sin_decimales(self):
        self.assertEqual(miles_chilenos('125000000.50'), '125.000.001')


class PreferenciasTests(SimpleTestCase):
    def test_normalizar_cadena_simple(self):
        from .perfil_views import normalizar_cadena_simple
        self.assertEqual(normalizar_cadena_simple("Mantención"), "mantencion")
        self.assertEqual(normalizar_cadena_simple("¡Cloud & Seguridad!"), "cloud seguridad")
        self.assertEqual(normalizar_cadena_simple(""), "")


class VistasExportacionTests(SimpleTestCase):
    def setUp(self):
        from django.test import RequestFactory
        self.rf = RequestFactory()

    def test_exportar_licitaciones_csv_por_defecto(self):
        from unittest.mock import patch
        from .licitaciones_views import exportar_licitaciones_view

        with patch('smartbids.licitaciones_views.resolver_suscriptor', return_value=None), \
             patch('smartbids.licitaciones_views.filtrar_licitaciones', return_value=([], 0)):
            req = self.rf.get('/mis-licitaciones/exportar/')
            resp = exportar_licitaciones_view(req)
            self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')
            self.assertIn('licitaciones-smartbids.csv', resp['Content-Disposition'])

    def test_exportar_licitaciones_excel(self):
        from unittest.mock import patch
        from .licitaciones_views import exportar_licitaciones_view

        with patch('smartbids.licitaciones_views.resolver_suscriptor', return_value=None), \
             patch('smartbids.licitaciones_views.filtrar_licitaciones', return_value=([], 0)):
            req = self.rf.get('/mis-licitaciones/exportar/?formato=xlsx')
            resp = exportar_licitaciones_view(req)
            self.assertEqual(resp['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.assertIn('licitaciones-smartbids.xlsx', resp['Content-Disposition'])

    def test_exportar_dashboard_excel(self):
        from unittest.mock import patch
        from .page_views import exportar_dashboard_view

        with patch('smartbids.page_views.Licitacion.objects') as mock_objects:
            mock_objects.select_related.return_value.filter.return_value.order_by.return_value = []
            req = self.rf.get('/dashboard/exportar/?formato=xlsx')
            resp = exportar_dashboard_view(req)
            self.assertEqual(resp['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.assertIn('dashboard-smartbids.xlsx', resp['Content-Disposition'])


class ReenvioActivacionTests(SimpleTestCase):
    def setUp(self):
        from django.test import RequestFactory
        from django.core.cache import cache
        self.rf = RequestFactory()
        cache.clear()

    def test_metodo_no_permitido(self):
        from .auth_views import reenviar_correo_activacion
        req = self.rf.get('/api/reenviar-correo-activacion/')
        resp = reenviar_correo_activacion(req)
        self.assertEqual(resp.status_code, 405)

    def test_correo_requerido(self):
        from .auth_views import reenviar_correo_activacion
        req = self.rf.post('/api/reenviar-correo-activacion/', data=b'{}', content_type='application/json')
        resp = reenviar_correo_activacion(req)
        self.assertEqual(resp.status_code, 400)

    def test_usuario_no_encontrado(self):
        from unittest.mock import patch, MagicMock
        from firebase_admin import auth as fb_auth
        from .auth_views import reenviar_correo_activacion

        mock_app = MagicMock()
        with patch('smartbids.auth_views._firebase_admin_app', return_value=mock_app), \
             patch('firebase_admin.auth.get_user_by_email', side_effect=fb_auth.UserNotFoundError('No user')):
            req = self.rf.post(
                '/api/reenviar-correo-activacion/',
                data=b'{"email": "inexistente@smartbids.cl"}',
                content_type='application/json'
            )
            resp = reenviar_correo_activacion(req)
            self.assertEqual(resp.status_code, 404)

    def test_usuario_ya_activado(self):
        from unittest.mock import patch, MagicMock
        from .auth_views import reenviar_correo_activacion

        mock_user = MagicMock(email_verified=True)
        with patch('smartbids.auth_views._firebase_admin_app', return_value=MagicMock()), \
             patch('firebase_admin.auth.get_user_by_email', return_value=mock_user):
            req = self.rf.post(
                '/api/reenviar-correo-activacion/',
                data=b'{"email": "activo@smartbids.cl"}',
                content_type='application/json'
            )
            resp = reenviar_correo_activacion(req)
            self.assertEqual(resp.status_code, 400)

    def test_reenvio_exitoso_y_rate_limit(self):
        from unittest.mock import patch, MagicMock
        from .auth_views import reenviar_correo_activacion

        mock_user = MagicMock(email_verified=False)
        with patch('smartbids.auth_views._firebase_admin_app', return_value=MagicMock()), \
             patch('firebase_admin.auth.get_user_by_email', return_value=mock_user), \
             patch('smartbids.auth_views._enviar_email_activacion') as mock_envio:
            req = self.rf.post(
                '/api/reenviar-correo-activacion/',
                data=b'{"email": "pendiente@smartbids.cl"}',
                content_type='application/json'
            )
            resp = reenviar_correo_activacion(req)
            self.assertEqual(resp.status_code, 200)
            mock_envio.assert_called_once_with('pendiente@smartbids.cl', app=mock_envio.call_args.kwargs.get('app'))

            # Segundo intento inmediato debe devolver 429
            req2 = self.rf.post(
                '/api/reenviar-correo-activacion/',
                data=b'{"email": "pendiente@smartbids.cl"}',
                content_type='application/json'
            )
            resp2 = reenviar_correo_activacion(req2)
            self.assertEqual(resp2.status_code, 429)

    def test_correo_malformado_admin(self):
        import json
        from .auth_views import reenviar_correo_activacion

        req = self.rf.post(
            '/api/reenviar-correo-activacion/',
            data=b'{"email": "admin"}',
            content_type='application/json'
        )
        resp = reenviar_correo_activacion(req)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(data.get('status'), 'error')
        self.assertIn('formato del correo ingresado no es válido', data.get('mensaje', ''))
        self.assertNotIn('Malformed email address', data.get('mensaje', ''))

    def test_correo_malformado_en_enviar_codigo_login(self):
        import json
        from .auth_views import enviar_codigo_login

        req = self.rf.post(
            '/api/enviar-codigo-login/',
            data=b'{"email": "admin"}',
            content_type='application/json'
        )
        resp = enviar_codigo_login(req)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(data.get('status'), 'error')
        self.assertIn('formato del correo ingresado no es válido', data.get('mensaje', ''))


class TemplateIngresoTests(SimpleTestCase):
    def test_renderizado_boton_ayuda_y_panel_opciones(self):
        from unittest.mock import patch
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        rf = RequestFactory()
        req = rf.get('/ingreso/')

        with patch('smartbids.context_processors.InfoContacto.objects.first', return_value=None):
            html = render_to_string('registro/ingreso.html', request=req)

        # Botón de ayuda en la posición de login actions
        self.assertIn('id="btn-ayuda-login"', html)
        self.assertIn('Ayuda', html)

        # Panel de ayuda con ambas opciones
        self.assertIn('id="ayuda-login-panel"', html)
        self.assertIn('id="forgot-password-link"', html)
        self.assertIn('Recuperar contraseña', html)
        self.assertIn('id="btn-reenviar-activacion"', html)
        self.assertIn('Reenviar activación', html)


class AdministracionGeneralTests(SimpleTestCase):
    def test_navbar_no_contiene_administracion_general(self):
        from unittest.mock import patch
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        rf = RequestFactory()
        req = rf.get('/mis-licitaciones/')

        with patch('smartbids.context_processors.InfoContacto.objects.first', return_value=None):
            html = render_to_string('smartbids/Mis_licitaciones.html', request=req, context={'licitaciones': [], 'total_licitaciones': 0})

        self.assertNotIn('id="admin-general-nav"', html)
        self.assertNotIn('Administración General</a>', html)

    def test_perfil_contiene_seccion_admin_en_sesiones(self):
        from unittest.mock import patch
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        rf = RequestFactory()
        req = rf.get('/perfil/')

        with patch('smartbids.context_processors.InfoContacto.objects.first', return_value=None):
            html = render_to_string('smartbids/perfil.html', request=req)

        self.assertIn('id="perfil-admin-section"', html)
        self.assertIn('Administración General', html)

    def test_acceso_denegado_no_administrador(self):
        from unittest.mock import patch, MagicMock
        from django.test import RequestFactory
        from .page_views import administracion_general_view

        rf = RequestFactory()
        req = rf.get('/administracion-general/')

        mock_susc = MagicMock()
        mock_susc.codigo_estado = MagicMock(codigo_estado=2, nombre_estado='Habilitado')

        with patch('smartbids.page_views.resolver_suscriptor', return_value=mock_susc):
            resp = administracion_general_view(req)
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.url, '/mis-licitaciones/')
