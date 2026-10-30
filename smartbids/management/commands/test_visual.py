"""
Comando de Pruebas Visuales y Detección de Desbordes Responsivos para SmartBids.

Uso:
    python manage.py test_visual
    python manage.py test_visual --screenshot
    python manage.py test_visual --url=http://127.0.0.1:8000
"""
import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand


DEFAULT_VIEWPORTS = [
    ('Móvil Compacto (360px)', {'width': 360, 'height': 740}),
    ('Móvil Estándar (390px)', {'width': 390, 'height': 844}),
    ('Tablet (768px)', {'width': 768, 'height': 1024}),
    ('Laptop (1280px)', {'width': 1280, 'height': 800}),
    ('Escritorio Full HD (1920px)', {'width': 1920, 'height': 1080}),
]

DEFAULT_ROUTES = [
    ('/', 'Inicio / Landing'),
    ('/informacion/', 'Información Legal y Seguridad'),
    ('/ingreso/', 'Ingreso / Iniciar Sesión'),
    ('/registro/', 'Registro de Cuenta'),
    ('/perfil/', 'Perfil de Empresa y Palabras Clave'),
    ('/mis-licitaciones/', 'Mis Licitaciones y Filtros'),
    ('/dashboard/', 'Dashboard Analítico'),
    ('/resumen/', 'Resumen del Día'),
]

JS_OVERFLOW_CHECK = '''
() => {
    const viewportWidth = window.innerWidth;
    const docWidth = document.documentElement.clientWidth;
    const scrollWidth = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
    const hasHorizontalScroll = scrollWidth > (viewportWidth + 1.5);

    const elements = document.querySelectorAll('*');
    const offenders = [];

    elements.forEach(el => {
        if (el.offsetWidth === 0 && el.offsetHeight === 0) return;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden') return;
        if (style.position === 'fixed' || style.position === 'absolute' && el.parentElement === document.body && el.id === 'page-loader') return;

        const rect = el.getBoundingClientRect();
        // Margen de tolerancia de 1.5px por redondeo de subpíxeles
        if (rect.right > (viewportWidth + 1.5)) {
            offenders.push({
                tag: el.tagName.toLowerCase(),
                id: el.id || '',
                className: (typeof el.className === 'string' ? el.className : '').trim().split(' ')[0] || '',
                right: Math.round(rect.right),
                excess: Math.round(rect.right - viewportWidth),
                text: (el.innerText || '').slice(0, 35).replace(/\\s+/g, ' ').trim()
            });
        }
    });

    return {
        viewportWidth,
        scrollWidth,
        hasHorizontalScroll,
        offenderCount: offenders.length,
        topOffenders: offenders.slice(0, 4)
    };
}
'''


class Command(BaseCommand):
    help = 'Ejecuta pruebas visuales automatizadas en Headless Chrome para detectar desbordes responsivos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            default='http://127.0.0.1:8000',
            help='URL base del servidor a probar (por defecto: http://127.0.0.1:8000)',
        )
        parser.add_argument(
            '--screenshot',
            action='store_true',
            help='Guarda capturas de pantalla de cada vista y resolución en visual_reports/',
        )
        parser.add_argument(
            '--route',
            default=None,
            help='Prueba una ruta específica en lugar de todas (ej: /perfil/)',
        )

    def handle(self, *args, **options):
        base_url = options['url'].rstrip('/')
        save_screenshots = options['screenshot']
        specific_route = options['route']

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.stderr.write(self.style.ERROR(
                'Playwright no está instalado en el entorno. Ejecuta: pip install playwright'
            ))
            sys.exit(1)

        chrome_path = None
        for path in ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium-browser']:
            if os.path.exists(path):
                chrome_path = path
                break

        routes = [(specific_route, 'Ruta específica')] if specific_route else DEFAULT_ROUTES
        screenshot_dir = Path('visual_reports')
        if save_screenshots:
            screenshot_dir.mkdir(exist_ok=True)

        self.stdout.write(self.style.SUCCESS(
            '\n' + '=' * 75 + '\n'
            ' 🎨 SMARTBIDS — SUITE DE PRUEBAS VISUALES Y DESBORDE RESPONSIVO\n'
            '=' * 75
        ))
        self.stdout.write(f'  Servidor objetivo : {base_url}')
        self.stdout.write(f'  Navegador         : {chrome_path or "Chromium bundled"}')
        self.stdout.write(f'  Resoluciones ({len(DEFAULT_VIEWPORTS)})  : {[v[0] for v in DEFAULT_VIEWPORTS]}')
        self.stdout.write(f'  Rutas a probar ({len(routes)}): {[r[0] for r in routes]}')
        self.stdout.write('-' * 75 + '\n')

        total_checks = 0
        total_failures = 0

        with sync_playwright() as p:
            launch_kwargs = {'headless': True}
            if chrome_path:
                launch_kwargs['executable_path'] = chrome_path

            browser = p.chromium.launch(**launch_kwargs)

            for route, label in routes:
                target_url = f'{base_url}{route}'
                self.stdout.write(self.style.HTTP_INFO(f'📄 Probando vista: {label} ({route})'))

                for vp_name, vp in DEFAULT_VIEWPORTS:
                    total_checks += 1
                    context = browser.new_context(viewport=vp)
                    page = context.new_page()

                    try:
                        resp = page.goto(target_url, wait_until='networkidle', timeout=15000)
                        if not resp or resp.status >= 400:
                            self.stdout.write(self.style.WARNING(
                                f'   ⚠️ {vp_name}: HTTP {resp.status if resp else "Sin respuesta"}'
                            ))
                            context.close()
                            continue

                        result = page.evaluate(JS_OVERFLOW_CHECK)

                        if result['hasHorizontalScroll']:
                            total_failures += 1
                            self.stdout.write(self.style.ERROR(
                                f'   🚨 DESBORDE en {vp_name}: '
                                f'scrollWidth={result["scrollWidth"]}px > viewport={result["viewportWidth"]}px '
                                f'({result["offenderCount"]} elementos desbordados)'
                            ))
                            for off in result['topOffenders']:
                                ident = f'#{off["id"]}' if off["id"] else (f'.{off["className"]}' if off["className"] else '')
                                self.stdout.write(
                                    f'      -> <{off["tag"]}{ident}> sobresale por {off["excess"]}px: "{off["text"]}"'
                                )
                        else:
                            self.stdout.write(self.style.SUCCESS(
                                f'   ✅ OK {vp_name}: ancho perfecto ({result["viewportWidth"]}px) sin desbordes'
                            ))

                        if save_screenshots:
                            clean_route = route.strip('/').replace('/', '_') or 'home'
                            clean_vp = vp_name.split(' ')[0].lower()
                            file_path = screenshot_dir / f'{clean_route}_{clean_vp}_{vp["width"]}x{vp["height"]}.png'
                            page.screenshot(path=str(file_path), full_page=True)

                    except Exception as e:
                        total_failures += 1
                        self.stdout.write(self.style.ERROR(f'   ❌ Error en {vp_name}: {e}'))
                    finally:
                        context.close()

                self.stdout.write('')

            browser.close()

        self.stdout.write('=' * 75)
        if total_failures == 0:
            self.stdout.write(self.style.SUCCESS(
                f' 🎉 RESULTADO: {total_checks} comprobaciones visuales exitosas. '
                f'¡Ningún elemento se desborda de la pantalla!'
            ))
            self.stdout.write('=' * 75 + '\n')
        else:
            self.stdout.write(self.style.ERROR(
                f' ❌ RESULTADO: Se detectaron {total_failures} desbordes en {total_checks} comprobaciones.'
            ))
            self.stdout.write('=' * 75 + '\n')
            sys.exit(1)
