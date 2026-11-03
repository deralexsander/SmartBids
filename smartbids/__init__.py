"""SmartBids core app package."""


def __getattr__(name):
    if name in (
        'auth_views',
        'dashboard_views',
        'firebase_policy_views',
        'licitaciones_views',
        'mensajeria_views',
        'page_views',
        'perfil_views',
        'resumen_views',
        'tracking_views',
    ):
        from . import views
        return getattr(views, name)
    if name in ('licitacion_utils', 'storage_guard'):
        from . import utils
        return getattr(utils, name)
    if name == 'mercadopublico_service':
        from . import services
        return getattr(services, name)
    if name == 'gmail_backend':
        from . import backends
        return getattr(backends, name)
    raise AttributeError(f"module 'smartbids' has no attribute '{name}'")
