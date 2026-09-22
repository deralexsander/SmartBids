import { onAuthStateChanged, signOut } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js';
import { auth } from './firebase-config.js';
import { AuthState } from './auth-state.js';
import { hidePageLoader, SessionManager } from './functions.js';
import { inicializarVistaPerfil } from './perfil.js';



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

const updateNavButtons = (user) => {
    if (loginButton) loginButton.style.display = user ? 'none' : 'inline-flex';
    if (profileButton) profileButton.style.display = user ? 'inline-flex' : 'none';
};

async function validarAccesoMensajeria(user, pageRule) {
    if (!pageRule?.requiredRole) return true;

    try {
        const response = await fetch('/api/obtener-perfil/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid: user.uid })
        });
        const data = await response.json();
        const nombreEstado = data.datos?.nombre_estado || '';
        const rolNormalizado = nombreEstado.trim().toLowerCase();
        const tieneRol = pageRule.requiredRole === 'admin'
            ? rolNormalizado === 'admin' || rolNormalizado === 'administrador'
            : rolNormalizado === pageRule.requiredRole;

        if (!tieneRol) {
            sessionStorage.setItem('flash_message', JSON.stringify({
                texto: pageRule.errorMsg,
                tipo: 'error'
            }));
            window.location.replace(pageRule.redirectFallback || '/');
            return false;
        }

        document.dispatchEvent(new CustomEvent('smartbids:admin-ready'));
        return true;
    } catch (error) {
        console.error('[SmartBids] Error verificando permisos de mensajería:', error);
        window.location.replace(pageRule.redirectFallback || '/');
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

    if (!(await validarAccesoMensajeria(user, pageRule))) return;

    // 3. Imprimir el token local actual en consola
    const tokenActual = SessionManager.getLocalToken();
    if (tokenActual) {
        console.log(`tokenID: ${tokenActual}`);
    }

    // 4. Validar token contra PostgreSQL de inmediato
    await validarSesionContraPostgres(user);

    // 5. Iniciar monitoreo en segundo plano cada 10 segundos
    if (!intervaloMonitoreoSesion) {
        intervaloMonitoreoSesion = setInterval(() => {
            validarSesionContraPostgres(user);
        }, 10000);
    }

    // 6. Cargar datos si está en perfil y apagar loader
    if (document.getElementById('profile-email') || document.getElementById('form-perfil-datos')) {
        await inicializarVistaPerfil(user);
    }

    updateNavButtons(user);
    hidePageLoader();
});



