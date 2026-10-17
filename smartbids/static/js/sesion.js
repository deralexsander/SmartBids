import { onAuthStateChanged, signOut } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js';
import { auth } from './firebase-config.js';
import { AuthState } from './auth-state.js';
import { hidePageLoader, SessionManager } from './functions.js';
import { inicializarVistaPerfil, evaluarYMostrarModalPerfil } from './perfil.js';



const PAGES_CONFIG = [
    { elementId: 'login-form', guestOnly: true, redirectFallback: '/perfil' },
    { elementId: 'register-form', guestOnly: true, redirectFallback: '/perfil' },
    { elementId: 'profile-email', requiresAuth: true, redirectFallback: '/ingreso' },
    { elementId: 'form-perfil-datos', requiresAuth: true, redirectFallback: '/ingreso' },
    { path: '/mis-licitaciones', requiresAuth: true, redirectFallback: '/ingreso' }, 
    { path: '/dashboard', requiresAuth: true, redirectFallback: '/ingreso' }, 
    { 
        elementId: 'form-mensajeria', 
        requiresAuth: true, 
        requiredRole: 'admin', 
        redirectFallback: '/', 
        errorMsg: 'Acceso denegado: Se requieren permisos de administrador.' 
    },
    {
        elementId: 'admin-general-page',
        requiresAuth: true,
        requiredRole: 'admin',
        redirectFallback: '/',
        errorMsg: 'Acceso denegado: se requieren permisos de administrador.'
    }
];

function matchCurrentPageConfig() {
    const currentPath = window.location.pathname;
    return PAGES_CONFIG.find(page => {
        if (page.elementId && document.getElementById(page.elementId)) return true;
        if (page.path && currentPath.includes(page.path)) return true;
        return false;
    });
}

const loginButton = document.getElementById('btn-login');
const profileButton = document.getElementById('btn-profile');
const adminGeneralNav = document.getElementById('admin-general-nav');

const updateNavButtons = (user) => {
    if (loginButton) loginButton.style.display = user ? 'none' : 'inline-flex';
    if (profileButton) profileButton.style.display = user ? 'inline-flex' : 'none';
    if (!user && adminGeneralNav) adminGeneralNav.style.display = 'none';
};

async function validarRolAdministrador(user) {
    try {
        const response = await fetch('/api/obtener-perfil/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid: user.uid })
        });
        const data = await response.json();
        const nombreEstado = data.datos?.nombre_estado || '';
        const rolNormalizado = nombreEstado.trim().toLowerCase();
        const tieneRol = rolNormalizado === 'admin' || rolNormalizado === 'administrador' || data.datos?.codigo_estado === 5;

        const perfilAdminSection = document.getElementById('perfil-admin-section');
        if (perfilAdminSection) perfilAdminSection.style.display = tieneRol ? 'block' : 'none';
        if (tieneRol && adminGeneralNav) adminGeneralNav.style.display = 'list-item';
        if (tieneRol) document.dispatchEvent(new CustomEvent('smartbids:admin-ready'));
        return tieneRol;
    } catch (error) {
        console.error('[SmartBids] Error verificando rol administrativo:', error);
        const perfilAdminSection = document.getElementById('perfil-admin-section');
        if (perfilAdminSection) perfilAdminSection.style.display = 'none';
        if (adminGeneralNav) adminGeneralNav.style.display = 'none';
        return false;
    }
}

// Variable para el temporizador de monitoreo continuo
let intervaloMonitoreoSesion = null;

// Función de validación y deslogueo automático
async function validarSesionContraPostgres(user) {
    if (!user || AuthState.isSubmittingAuth) return;

    const tokenLocal = SessionManager.getLocalToken();
    if (!tokenLocal) return;

    try {
        const resp = await fetch('/api/verificar-sesion/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid: user.uid, token: tokenLocal })
        });
        const resData = await resp.json();

        // Si el token es diferente al que está en PostgreSQL, se expulsa al usuario
        if (resData.status === 'ok' && resData.valido === false) {
            console.warn('[SmartBids] ⚠️ Sesión caducada: El token cambió en la base de datos.');

            if (intervaloMonitoreoSesion) clearInterval(intervaloMonitoreoSesion);

            SessionManager.clearLocalToken();
            await signOut(auth);

            sessionStorage.setItem('flash_message', JSON.stringify({
                texto: 'Tu sesión ha caducado porque se inició sesión desde otro dispositivo.',
                tipo: 'error'
            }));

            window.location.replace('/ingreso');
        }
    } catch (err) {
        console.error('[SmartBids] Error verificando sesión en PostgreSQL:', err);
    }
}

onAuthStateChanged(auth, async (user) => {
    const pageRule = matchCurrentPageConfig();

    // 1. Si no hay sesión iniciada
    if (!user) {
        if (intervaloMonitoreoSesion) clearInterval(intervaloMonitoreoSesion);
        SessionManager.clearLocalToken();
        localStorage.removeItem('smartbids_uid');
        document.cookie = 'sb_firebase_uid=; path=/; max-age=0; SameSite=Lax';

        if (pageRule?.requiresAuth) {
            window.location.replace(pageRule.redirectFallback || '/ingreso');
            return;
        }
        updateNavButtons(null);
        hidePageLoader();
        return;
    }

    // 2. Si ya está autenticado e intenta ir a login o registro
    if (pageRule?.guestOnly && !AuthState.isSubmittingAuth) {
        window.location.replace('/');
        return;
    }

    if (AuthState.isSubmittingAuth) return;

    // Guardar UID y fijar cookie de sesión para SSR
    localStorage.setItem('smartbids_uid', user.uid);
    document.cookie = `sb_firebase_uid=${user.uid}; path=/; max-age=604800; SameSite=Lax`;
    updateNavButtons(user);

    // 3. Validar rol solo si la ruta actual lo exige expresamente
    if (pageRule?.requiredRole) {
        const esAdministrador = await validarRolAdministrador(user);
        if (!esAdministrador) {
            sessionStorage.setItem('flash_message', JSON.stringify({
                texto: pageRule.errorMsg || 'Acceso denegado: se requieren permisos administrativos.',
                tipo: 'error'
            }));
            window.location.replace(pageRule.redirectFallback || '/');
            return;
        }
    }

    // 4. Imprimir token local si existe
    const tokenActual = SessionManager.getLocalToken();
    if (tokenActual) {
        console.log(`tokenID: ${tokenActual}`);
    }

    // 5. Validar sesión contra PostgreSQL en segundo plano
    validarSesionContraPostgres(user);
    if (!intervaloMonitoreoSesion) {
        intervaloMonitoreoSesion = setInterval(() => {
            validarSesionContraPostgres(user);
        }, 10000);
    }

    // 6. Manejo de vistas e interfaz
    const esPaginaPerfil = Boolean(
        document.getElementById('profile-email') ||
        document.getElementById('form-perfil-datos') ||
        document.getElementById('form-perfil-preferencias')
    );

    if (esPaginaPerfil) {
        await inicializarVistaPerfil(user);
        hidePageLoader();
    } else {
        // En cualquier otra página (mis-licitaciones, dashboard, etc.), liberar el loader de inmediato
        hidePageLoader();

        // Si la página de licitaciones se cargó previamente sin cookie de suscriptor, recargar
        const licitacionesList = document.getElementById('licitaciones-list');
        if (licitacionesList && licitacionesList.dataset.suscriptorActivo === 'false') {
            window.location.reload();
            return;
        }

        // Obtener perfil en segundo plano una sola vez para nav administrativo y modal de completitud
        const currentPath = window.location.pathname.toLowerCase();
        const esRutaPermitida = currentPath.includes('/mis-licitaciones') || currentPath.includes('/dashboard');

        fetch('/api/obtener-perfil/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid: user.uid })
        })
        .then(resp => resp.json())
        .then(resData => {
            if (resData.status === 'ok' && resData.datos) {
                const nombreEstado = resData.datos.nombre_estado || '';
                const rolNormalizado = nombreEstado.trim().toLowerCase();
                const tieneRol = rolNormalizado === 'admin' || rolNormalizado === 'administrador' || resData.datos?.codigo_estado === 5;
                const perfilAdminSection = document.getElementById('perfil-admin-section');
                if (perfilAdminSection) perfilAdminSection.style.display = tieneRol ? 'block' : 'none';
                if (tieneRol && adminGeneralNav) adminGeneralNav.style.display = 'list-item';
                if (tieneRol) document.dispatchEvent(new CustomEvent('smartbids:admin-ready'));

                if (esRutaPermitida) {
                    evaluarYMostrarModalPerfil(resData.datos);
                }
            }
        })
        .catch(err => {
            console.error('[SmartBids] Error en verificación en segundo plano:', err);
        });
    }
});



