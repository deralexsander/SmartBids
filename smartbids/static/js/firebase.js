import { initializeApp, deleteApp } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js';
import { 
    getAuth, 
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword, 
    sendEmailVerification, 
    signOut,
    onAuthStateChanged,
    EmailAuthProvider,         
    reauthenticateWithCredential,
    updatePassword               
} from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js';

import { 
    getFirestore, 
    doc, 
    getDoc,
    setDoc,
    updateDoc,          
    addDoc, 
    deleteDoc,
    collection,
    query,
    where,
    orderBy,
    onSnapshot,
    serverTimestamp,
    Timestamp 
} from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js';

import { 
    redirectIfAuthenticated, 
    hidePageLoader,         
    setupPasswordToggles,
    setButtonLoading,
    generateSessionId,  
    SessionManager,     
    abrirModal2FA,
    cerrarModal2FA  
} from './functions.js';

import { 
    mostrarMensaje, 
    limpiarMensaje, 
    getFriendlyErrorMessage,
    MENSAJES,
} from './mensaje.js';

// ==========================================================================
// 1. Cargar Configuración de Firebase desde el bloque JSON enviado por Django
// ==========================================================================
const configScript = document.getElementById('firebase-config');
let firebaseConfig = {};

if (configScript) {
    try {
        firebaseConfig = JSON.parse(configScript.textContent);
    } catch (e) {
        console.error('[SmartBids] Error parseando JSON de Firebase:', e);
    }
}

// Validar que apiKey exista antes de inicializar
if (!firebaseConfig || !firebaseConfig.apiKey) {
    console.error('[SmartBids] ❌ Error: No se encontraron las credenciales de Firebase. Verifica tu archivo .env y el servidor de Django.');
}


// 2. Inicialización de SDKs
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

export { app, auth, db };

// ==========================================================================
// 3. Inicialización de componentes UI
// ==========================================================================
setupPasswordToggles();

let isSubmittingAuth = false;

// Mostrar mensaje flash almacenado al redirigir entre páginas
const mensajeFlash = sessionStorage.getItem('flash_message');
if (mensajeFlash) {
    try {
        const flashData = JSON.parse(mensajeFlash);
        mostrarMensaje(flashData.texto, flashData.tipo);
    } catch (e) {
        console.error('Error parseando mensaje flash:', e);
    }
    sessionStorage.removeItem('flash_message');
}



// ==========================================================================
// 4. Control de Estado de Autenticación, Verificación Continua y Rutas
// ==========================================================================

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

// Variable para el temporizador de monitoreo continuo
let intervaloMonitoreoSesion = null;

// Función de validación y deslogueo automático
async function validarSesionContraPostgres(user) {
    if (!user || isSubmittingAuth) return;

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
    if (pageRule?.guestOnly && !isSubmittingAuth) {
        window.location.replace('/');
        return;
    }

    if (isSubmittingAuth) return;

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


// ==========================================================================
// SECCIÓN PERFIL: Conectada a PostgreSQL (Sin llamadas a Firestore)
// ==========================================================================
function formatTimestamp(ts) {
    if (!ts) return 'No registrada';
    const date = new Date(ts);
    return date.toLocaleDateString('es-CL', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

async function inicializarVistaPerfil(user) {
    if (!user) return;

    try {
        const resp = await fetch('/api/obtener-perfil/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid: user.uid })
        });
        const resData = await resp.json();

        if (resData.status === 'ok') {
            const data = resData.datos;
            const emp = data.empresa || {};
            const pref = data.preferencias || {};

            // 1. Sidebar y Cabeceras
            const n1 = data.sus_nombre1 || '';
            const n2 = data.sus_nombre2 || '';
            const a1 = data.sus_apellido1 || '';
            const a2 = data.sus_apellido2 || '';
            const nombreCompleto = [n1, n2, a1, a2].filter(Boolean).join(' ') || 'Suscriptor';

            document.getElementById('profile-fullname-header').textContent = nombreCompleto;
            document.getElementById('profile-social-header').textContent = data.sus_nombre_social ? `@${data.sus_nombre_social}` : `@suscriptor_${data.id_suscriptor}`;
            document.getElementById('profile-role-badge').textContent = data.codigo_estado === 2 ? 'Habilitado' : 'Pendiente';
            document.getElementById('profile-initials').textContent = data.sus_iniciales || (n1 && a1 ? (n1[0] + a1[0]).toUpperCase() : 'SB');
            document.getElementById('profile-id-suscriptor').textContent = data.id_suscriptor || '--';
            document.getElementById('profile-uid-header').textContent = user.uid;
            document.getElementById('profile-created-at').textContent = formatTimestamp(data.fecha_registro);
            document.getElementById('profile-last-login').textContent = formatTimestamp(data.fecha_actualizacion);
            document.getElementById('profile-token-id').textContent = data.token_sesion || SessionManager.getLocalToken() || 'No asignado';
            document.getElementById('profile-email').value = user.email || '';

            // 2. Formulario Datos Personales
            document.getElementById('profile-nombre1').value = n1;
            document.getElementById('profile-nombre2').value = n2;
            document.getElementById('profile-apellido1').value = a1;
            document.getElementById('profile-apellido2').value = a2;
            document.getElementById('profile-nombre-social').value = data.sus_nombre_social || '';
            document.getElementById('profile-iniciales').value = data.sus_iniciales || '';

            // 3. Formulario Empresa
            document.getElementById('empresa-rut').value = emp.emp_rut || '';
            document.getElementById('empresa-fantasia').value = emp.emp_nombre_fantasia || '';
            document.getElementById('empresa-razon-social').value = emp.emp_razon_social || '';
            document.getElementById('empresa-correo').value = emp.emp_contacto_correo || '';
            document.getElementById('empresa-iniciales').value = emp.emp_iniciales || '';
            document.getElementById('empresa-telefono').value = emp.emp_contacto_telefono || '';
            document.getElementById('empresa-comuna').value = emp.emp_codigo_comuna || '';
            document.getElementById('empresa-direccion').value = emp.emp_direccion || '';

            // 4. Formulario Filtros de Licitación
            document.getElementById('pref-comunas').value = pref.pref_comunas || '';
            document.getElementById('pref-productos').value = pref.pref_productos || '';
            document.getElementById('pref-tipo-lic').value = pref.pref_tipo_licitacion || '';
            document.getElementById('pref-ucom').value = pref.pref_ucom || '';
            document.getElementById('pref-palabras').value = pref.pref_palabras_claves || '';
        }
    } catch (err) {
        console.error('[SmartBids] Error al cargar perfil desde PostgreSQL:', err);
    }

    // Submit: Datos Personales
    const formDatos = document.getElementById('form-perfil-datos');
    if (formDatos) {
        formDatos.onsubmit = async (e) => {
            e.preventDefault();
            const btn = formDatos.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Guardando...');
            try {
                const resp = await fetch('/api/actualizar-perfil/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        uid: user.uid,
                        sus_nombre1: document.getElementById('profile-nombre1').value,
                        sus_nombre2: document.getElementById('profile-nombre2').value,
                        sus_apellido1: document.getElementById('profile-apellido1').value,
                        sus_apellido2: document.getElementById('profile-apellido2').value,
                        sus_nombre_social: document.getElementById('profile-nombre-social').value,
                        sus_iniciales: document.getElementById('profile-iniciales').value,
                    })
                });
                const res = await resp.json();
                mostrarMensaje(res.mensaje, res.status === 'ok' ? 'exito' : 'error');
                await inicializarVistaPerfil(user);
            } finally {
                setButtonLoading(btn, false);
            }
        };
    }

    // Submit: Empresa
    const formEmpresa = document.getElementById('form-perfil-empresa');
    if (formEmpresa) {
        formEmpresa.onsubmit = async (e) => {
            e.preventDefault();
            const btn = formEmpresa.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Guardando...');
            try {
                const resp = await fetch('/api/actualizar-empresa/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        uid: user.uid,
                        emp_rut: document.getElementById('empresa-rut').value,
                        emp_nombre_fantasia: document.getElementById('empresa-fantasia').value,
                        emp_razon_social: document.getElementById('empresa-razon-social').value,
                        emp_contacto_correo: document.getElementById('empresa-correo').value,
                        emp_iniciales: document.getElementById('empresa-iniciales').value,
                        emp_contacto_telefono: document.getElementById('empresa-telefono').value,
                        emp_codigo_comuna: document.getElementById('empresa-comuna').value,
                        emp_direccion: document.getElementById('empresa-direccion').value,
                    })
                });
                const res = await resp.json();
                mostrarMensaje(res.mensaje, res.status === 'ok' ? 'exito' : 'error');
            } finally {
                setButtonLoading(btn, false);
            }
        };
    }

    // Submit: Filtros de Licitación
    const formFiltros = document.getElementById('form-perfil-preferencias');
    if (formFiltros) {
        formFiltros.onsubmit = async (e) => {
            e.preventDefault();
            const btn = formFiltros.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Guardando...');
            try {
                const resp = await fetch('/api/actualizar-preferencias/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        uid: user.uid,
                        pref_comunas: document.getElementById('pref-comunas').value,
                        pref_productos: document.getElementById('pref-productos').value,
                        pref_tipo_licitacion: document.getElementById('pref-tipo-lic').value,
                        pref_ucom: document.getElementById('pref-ucom').value,
                        pref_palabras_claves: document.getElementById('pref-palabras').value,
                    })
                });
                const res = await resp.json();
                mostrarMensaje(res.mensaje, res.status === 'ok' ? 'exito' : 'error');
            } finally {
                setButtonLoading(btn, false);
            }
        };
    }
}






// Variable temporal para retener credenciales mientras valida el OTP
let pendingEmail = null;
let pendingPassword = null;
let pendingUid = null;

// ==========================================================================
// 5. Inicio de Sesión y Verificación OTP (2FA) - Sin Firestore
// ==========================================================================
const loginForm = document.getElementById('login-form');
const otpInputs = document.querySelectorAll('.otp-digit-input, .otp-input');
const btnVerificarOtp = document.getElementById('btn-verificar-otp');
const btnCancelarOtp = document.getElementById('btn-cancelar-otp');
const otpMessage = document.getElementById('otp-message');

// Control de navegación entre los 6 inputs OTP
otpInputs.forEach((input, index) => {
    input.addEventListener('input', (e) => {
        if (e.target.value.length === 1 && index < otpInputs.length - 1) {
            otpInputs[index + 1].focus();
        }
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && !input.value && index > 0) {
            otpInputs[index - 1].focus();
        }
    });
});



if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        limpiarMensaje();

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        if (!email || !password) {
            mostrarMensaje(MENSAJES.validacion.camposRequeridos, 'error');
            return;
        }

        const submitBtn = loginForm.querySelector('button[type="submit"]');
        setButtonLoading(submitBtn, true, 'Validando credenciales...');
        isSubmittingAuth = true;

        try {
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;

            if (!user.emailVerified) {
                await signOut(auth);
                isSubmittingAuth = false;
                setButtonLoading(submitBtn, false);
                mostrarMensaje(MENSAJES.auth.emailNoVerificado, 'error');
                return;
            }

            // Enviar código por correo
            const response = await fetch('/api/enviar-codigo-login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: user.email })
            });

            const resData = await response.json();
            if (!response.ok || resData.status !== 'ok') {
                throw new Error(resData.mensaje || 'Error al enviar el código de verificación.');
            }

            pendingEmail = email;
            pendingPassword = password;
            pendingUid = user.uid;

            await signOut(auth);

            isSubmittingAuth = false;
            setButtonLoading(submitBtn, false);
            abrirModal2FA();

        } catch (error) {
            isSubmittingAuth = false;
            setButtonLoading(submitBtn, false);
            console.error('[SmartBids] ❌ Error en inicio de sesión:', error);
            mostrarMensaje(getFriendlyErrorMessage(error.code, error.message), 'error');
        }
    });
}

// Validar código OTP del Modal y fijar el Token
if (btnVerificarOtp) {
    btnVerificarOtp.addEventListener('click', async () => {
        if (!pendingEmail || !pendingPassword || !pendingUid) {
            otpMessage.textContent = 'Sesión expirada. Por favor, ingresa nuevamente.';
            return;
        }

        otpMessage.textContent = '';
        const codigoIngresado = Array.from(otpInputs).map(input => input.value.trim()).join('');

        if (codigoIngresado.length !== 6) {
            otpMessage.textContent = 'Por favor, ingresa los 6 dígitos del código.';
            return;
        }

        setButtonLoading(btnVerificarOtp, true, 'Verificando...');

        try {
            // 1. Generar nuevo TokenID con generateSessionId()
            const tokenID = generateSessionId();

            // 2. Enviar el código y el tokenID al backend de Django
            const response = await fetch('/api/validar-codigo-login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: pendingEmail,
                    uid: pendingUid,
                    codigo: codigoIngresado,
                    session_token: tokenID
                })
            });

            const resData = await response.json();
            if (!response.ok || resData.status !== 'ok') {
                setButtonLoading(btnVerificarOtp, false);
                otpMessage.textContent = resData.mensaje || 'Código incorrecto. Inténtalo de nuevo.';
                return;
            }

            // 3. Autenticar en Firebase Auth
            isSubmittingAuth = true;
            await signInWithEmailAndPassword(auth, pendingEmail, pendingPassword);

            // 4. Guardar token en LocalStorage y mostrarlo en la consola
            SessionManager.setLocalToken(tokenID);
            console.log(`tokenID: ${tokenID}`);

            sessionStorage.setItem('flash_message', JSON.stringify({
                texto: '¡Bienvenido! Sesión iniciada con éxito.',
                tipo: 'exito'
            }));

            pendingEmail = null;
            pendingPassword = null;
            pendingUid = null;

            isSubmittingAuth = false;
            window.location.href = '/mis-licitaciones/';

        } catch (error) {
            isSubmittingAuth = false;
            setButtonLoading(btnVerificarOtp, false);
            console.error('[SmartBids] ❌ Error al verificar código:', error);
            otpMessage.textContent = error.message || 'Error al validar el código.';
        }
    });
}

// Cancelar proceso de autenticación
if (btnCancelarOtp) {
    btnCancelarOtp.addEventListener('click', async () => {
        cerrarModal2FA();
        isSubmittingAuth = false;
        pendingEmail = null;
        pendingPassword = null;
        pendingUid = null;
        await signOut(auth);
    });
}

// ==========================================================================
// 6. Cierre de Sesión
// ==========================================================================
const logoutButton = document.getElementById('logout-button');
if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
        try {
            await signOut(auth);
            SessionManager.clearLocalToken();
            window.location.href = '/';
        } catch (error) {
            console.error('Error al cerrar sesión:', error);
            mostrarMensaje(MENSAJES.auth.logoutError, 'error');
        }
    });
}

// ==========================================================================
// 7. Recuperación de Contraseña
// ==========================================================================
const forgotPasswordLink = document.getElementById('forgot-password-link');
if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener('click', async (e) => {
        e.preventDefault();
        limpiarMensaje();

        const emailInput = document.getElementById('email');
        const email = emailInput ? emailInput.value.trim() : '';

        if (!email) {
            mostrarMensaje(MENSAJES.auth.resetPasswordSinEmail, 'error');
            return;
        }

        const originalText = forgotPasswordLink.textContent;
        forgotPasswordLink.style.pointerEvents = 'none';
        forgotPasswordLink.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Enviando...`;

        try {
            // Se actualiza la llamada utilizando la apiKey obtenida dinámicamente desde la configuración
            const response = await fetch(`https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key=${firebaseConfig.apiKey}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    requestType: 'PASSWORD_RESET',
                    email: email
                })
            });

            const data = await response.json();
            forgotPasswordLink.style.pointerEvents = 'auto';
            forgotPasswordLink.textContent = originalText;

            if (!response.ok) {
                if (data.error && data.error.message === 'EMAIL_NOT_FOUND') {
                    mostrarMensaje(MENSAJES.validacion.cuentaNoExiste, 'error');
                } else if (data.error && data.error.message === 'INVALID_EMAIL') {
                    mostrarMensaje(MENSAJES.validacion.emailInvalido, 'error');
                } else {
                    mostrarMensaje(MENSAJES.auth.resetPasswordError, 'error');
                }
                return;
            }

            mostrarMensaje(MENSAJES.auth.resetPasswordEnviado, 'exito');
        } catch (error) {
            forgotPasswordLink.style.pointerEvents = 'auto';
            forgotPasswordLink.textContent = originalText;
            console.error(error);
            mostrarMensaje(MENSAJES.auth.resetPasswordError, 'error');
        }
    });
}

// ==========================================================================
// 8. Registro de Nuevo Usuario y Creación en PostgreSQL (Estado Habilitado = 2)
// ==========================================================================
const registerForm = document.getElementById('register-form');
if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        limpiarMensaje();

        const email = document.getElementById('email').value.trim();
        const emailConfirm = document.getElementById('email-confirm').value.trim();
        const password = document.getElementById('password').value;
        const passwordConfirm = document.getElementById('password-confirm').value;

        if (!email || !emailConfirm || !password || !passwordConfirm) {
            mostrarMensaje(MENSAJES.validacion.camposRequeridos, 'error');
            return;
        }

        if (email !== emailConfirm) {
            mostrarMensaje(MENSAJES.validacion.emailsNoCoinciden, 'error');
            return;
        }

        if (password !== passwordConfirm) {
            mostrarMensaje(MENSAJES.validacion.passwordsNoCoinciden, 'error');
            return;
        }

        const submitBtn = registerForm.querySelector('button[type="submit"]');
        setButtonLoading(submitBtn, true, 'Registrando...');

        // Instancia aislada para registrar en background sin alterar la sesión local
        const secondaryApp = initializeApp(firebaseConfig, `SecondaryApp_${Date.now()}`);
        const secondaryAuth = getAuth(secondaryApp);

        try {
            // 1. Crear la cuenta en Firebase Authentication
            const userCredential = await createUserWithEmailAndPassword(secondaryAuth, email, password);
            const user = userCredential.user;

            // 2. Guardar en PostgreSQL conectando el UID (Estado 2 = Habilitado)
            const resDb = await fetch('/api/registrar-prospecto/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ uid: user.uid })
            });

            if (!resDb.ok) {
                console.warn('[SmartBids] Error al persistir el suscriptor en PostgreSQL.');
            }

            // 3. Correo de verificación de Firebase Auth
            await sendEmailVerification(user);

            // 4. Enviar correo de bienvenida mediante el servidor SMTP Django
            try {
                await fetch('/api/enviar-correo-bienvenida/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: user.email })
                });
            } catch (mailErr) {
                console.warn('[SmartBids] No se pudo enviar correo de bienvenida:', mailErr);
            }

            // 5. Mensaje temporal y redirección a ingreso
            sessionStorage.setItem('flash_message', JSON.stringify({
                texto: MENSAJES.auth.registroExitoso,
                tipo: 'exito'
            }));

            window.location.href = '/ingreso';
        } catch (error) {
            setButtonLoading(submitBtn, false);
            console.error('Error durante el registro:', error);
            mostrarMensaje(getFriendlyErrorMessage(error.code, error.message), 'error');
        } finally {
            await deleteApp(secondaryApp);
        }
    });
}

// ==========================================================================
// 9. GESTIÓN DE ALERTAS (PANEL ADMIN CONECTADO A POSTGRESQL)
// ==========================================================================
const formMensajeria = document.getElementById('form-mensajeria');
const listaAlertasAdmin = document.getElementById('lista-alertas-admin');
const inputMsgId = document.getElementById('msg-id');
const selectEstado = document.getElementById('msg-estado');
const selectTipo = document.getElementById('msg-tipo');
const btnCancelar = document.getElementById('btn-cancelar-edicion');
const statusFeedback = document.getElementById('mensaje-status-feedback');

if (formMensajeria) {
    async function cargarListaAlertasAdmin() {
        if (!listaAlertasAdmin) return;

        try {
            const res = await fetch('/api/mensajeria/');
            if (!res.ok) throw new Error('Error al consultar alertas');
            const dataList = await res.json();

            listaAlertasAdmin.innerHTML = '';

            if (dataList.length === 0) {
                listaAlertasAdmin.innerHTML = `
                    <div class="mockup-item" style="justify-content: center; padding: 2rem; color: var(--gray-text);">
                        <p style="margin: 0; font-size: 0.95rem;">No hay alertas registradas actualmente en PostgreSQL.</p>
                    </div>
                `;
                return;
            }

            dataList.forEach((data) => {
                const id = data.id;
                const esActivo = data.estado === 'activo';
                const estadoTexto = esActivo ? 'Activo' : 'Inactivo';
                const tipoAlerta = data.tipoAlerta || 'alerta';

                let colorTipo = 'var(--muted-teal)';
                let bgTipo = 'rgba(92, 150, 136, 0.12)';
                if (tipoAlerta === 'precaucion') {
                    colorTipo = '#e53e3e';
                    bgTipo = '#fff5f5';
                } else if (tipoAlerta === 'alerta') {
                    colorTipo = '#d97706';
                    bgTipo = '#fffbeb';
                } else if (tipoAlerta === 'exito') {
                    colorTipo = 'var(--accent-green)';
                    bgTipo = 'rgba(30, 196, 152, 0.15)';
                }

                const item = document.createElement('div');
                item.className = 'mockup-item';
                item.style.cssText = 'display: flex; flex-direction: column; align-items: stretch; gap: 0.75rem; margin-bottom: 1rem; border-radius: 14px;';

                item.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;">
                        <div style="display: flex; align-items: center; gap: 0.6rem;">
                            <h4 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: var(--dark-green);">
                                ${data.asunto || 'Sin Asunto'}
                            </h4>
                            <span class="dash-badge" style="background: ${bgTipo}; color: ${colorTipo}; text-transform: uppercase; font-size: 0.75rem;">
                                ${tipoAlerta}
                            </span>
                        </div>
                        <span class="mockup-status" style="${esActivo ? 'background: rgba(30, 196, 152, 0.15); color: var(--dark-green);' : 'background: #edf2f7; color: var(--gray-text);'}">
                            ${estadoTexto}
                        </span>
                    </div>

                    <div class="mockup-info" style="margin: 0;">
                        <p style="color: var(--gray-text); font-size: 0.92rem; line-height: 1.5; margin: 0; word-break: break-word;">
                            ${data.cuerpo || ''}
                        </p>
                    </div>

                    <div style="display: flex; justify-content: flex-end; gap: 0.6rem; padding-top: 0.5rem; border-top: 1px solid var(--border-color);">
                        <button type="button" class="btn btn-outline btn-edit" style="padding: 0.4rem 0.9rem; font-size: 0.85rem;">
                            Editar
                        </button>
                        <button type="button" class="btn btn-delete" style="padding: 0.4rem 0.9rem; font-size: 0.85rem; background: #fff5f5; color: #e53e3e; border: 1.5px solid #feb2b2;">
                            Eliminar
                        </button>
                    </div>
                `;

                // Botón Editar
                item.querySelector('.btn-edit').addEventListener('click', () => {
                    inputMsgId.value = id;
                    document.getElementById('msg-asunto').value = data.asunto || '';
                    document.getElementById('msg-cuerpo').value = data.cuerpo || '';
                    if (selectEstado) selectEstado.value = data.estado || 'activo';
                    if (selectTipo) selectTipo.value = data.tipoAlerta || 'alerta';

                    if (btnCancelar) btnCancelar.hidden = false;
                    formMensajeria.scrollIntoView({ behavior: 'smooth' });
                });

                // Botón Eliminar
                const btnDelete = item.querySelector('.btn-delete');
                btnDelete.addEventListener('click', async (e) => {
                    e.preventDefault();

                    if (!btnDelete.dataset.confirming) {
                        btnDelete.dataset.confirming = "true";
                        btnDelete.textContent = "¿Confirmar?";
                        btnDelete.style.background = "#e53e3e";
                        btnDelete.style.color = "var(--white)";

                        setTimeout(() => {
                            btnDelete.dataset.confirming = "";
                            btnDelete.textContent = "Eliminar";
                            btnDelete.style.background = "#fff5f5";
                            btnDelete.style.color = "#e53e3e";
                        }, 4000);
                        return;
                    }

                    try {
                        btnDelete.disabled = true;
                        btnDelete.textContent = "Borrando...";

                        const res = await fetch(`/api/mensajeria/${id}/`, { method: 'DELETE' });
                        if (!res.ok) throw new Error('Error al borrar');

                        mostrarMensaje('Alerta eliminada correctamente.', 'exito');
                        cargarListaAlertasAdmin();
                    } catch (error) {
                        console.error('Error al eliminar mensaje en PostgreSQL:', error);
                        mostrarMensaje('No se pudo eliminar el mensaje.', 'error');
                        btnDelete.disabled = false;
                        btnDelete.textContent = "Eliminar";
                        btnDelete.style.background = "#fff5f5";
                        btnDelete.style.color = "#e53e3e";
                    }
                });

                listaAlertasAdmin.appendChild(item);
            });
        } catch (error) {
            console.error('Error al listar mensajes desde PostgreSQL:', error);
            listaAlertasAdmin.innerHTML = '<p style="color: #e53e3e; padding: 1rem;">Error al cargar alertas desde el servidor.</p>';
        }
    }

    formMensajeria.addEventListener('submit', async (e) => {
        e.preventDefault();

        const idActual = inputMsgId.value;
        const asunto = document.getElementById('msg-asunto').value.trim();
        const cuerpo = document.getElementById('msg-cuerpo').value.trim();
        const estado = selectEstado ? selectEstado.value : 'activo';
        const tipoAlerta = selectTipo ? selectTipo.value : 'alerta';

        const payload = {
            asunto: asunto,
            cuerpo: cuerpo,
            estado: estado,
            tipoAlerta: tipoAlerta
        };

        if (statusFeedback) {
            statusFeedback.style.display = 'inline-flex';
            statusFeedback.textContent = 'Guardando...';
        }

        try {
            const url = idActual ? `/api/mensajeria/${idActual}/` : '/api/mensajeria/';
            const metodo = idActual ? 'PUT' : 'POST';

            const res = await fetch(url, {
                method: metodo,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error('Error en el guardado');

            formMensajeria.reset();
            inputMsgId.value = '';

            if (btnCancelar) btnCancelar.hidden = true;

            if (statusFeedback) {
                statusFeedback.textContent = '¡Guardado con éxito!';
                setTimeout(() => { 
                    statusFeedback.textContent = ''; 
                    statusFeedback.style.display = 'none';
                }, 3000);
            }
            mostrarMensaje('Mensaje guardado correctamente en la base de datos.', 'exito');
            cargarListaAlertasAdmin();
        } catch (error) {
            console.error('Error al guardar mensaje en PostgreSQL:', error);
            if (statusFeedback) {
                statusFeedback.textContent = 'Error al guardar.';
            }
            mostrarMensaje('Error al guardar el mensaje.', 'error');
        }
    });

    if (btnCancelar) {
        btnCancelar.addEventListener('click', () => {
            formMensajeria.reset();
            inputMsgId.value = '';
            btnCancelar.hidden = true;
        });
    }

    cargarListaAlertasAdmin();
}

