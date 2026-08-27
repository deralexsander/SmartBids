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

// firebase.js (Líneas 28 - 36 aprox.)

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
    renderizarAlerta
} from './mensaje.js';

// 1. Configuración de Firebase
const firebaseConfig = {
  apiKey: 'AIzaSyBlCZkRsr39TbPnL3fse3QH-W3oMIv7384',
  authDomain: 'smartbids-e0b99.firebaseapp.com',
  projectId: 'smartbids-e0b99',
  storageBucket: 'smartbids-e0b99.firebasestorage.app',
  messagingSenderId: '958415636156',
  appId: '1:958415636156:web:3859749919a9e9573ab2b9',
  measurementId: 'G-8JED2S96M0',
};

// 2. Inicialización de SDKs
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

export { app, auth, db };

/// ==========================================================================
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
// 4. Control de Estado de Autenticación y Protección Declarativa de Rutas
// ==========================================================================

const PAGES_CONFIG = [
    // 1. Solo para invitados (se bloquean si ya hay sesión iniciada)
    { elementId: 'login-form', guestOnly: true, redirectFallback: '/perfil' },
    { elementId: 'register-form', guestOnly: true, redirectFallback: '/perfil' },

    // 2. Requieren inicio de sesión (Cualquier usuario autenticado)
    { elementId: 'profile-email', requiresAuth: true, redirectFallback: '/perfil' },
    { elementId: 'form-perfil-datos', requiresAuth: true, redirectFallback: '/perfil' },
    { path: 'mis-licitaciones', requiresAuth: true, redirectFallback: '/ingreso' }, 
    { path: 'dashboard', requiresAuth: true, redirectFallback: '/ingreso' }, 

    // 3. Exclusivas de Administrador
    { 
        elementId: 'form-mensajeria', 
        requiresAuth: true, 
        requiredRole: 'admin', 
        redirectFallback: '/', 
        errorMsg: 'Acceso denegado: Se requieren permisos de administrador.' 
    }
];

// Función buscadora de reglas
const matchCurrentPageConfig = () => {
    const currentPath = window.location.pathname;
    return PAGES_CONFIG.find(page => {
        if (page.elementId && document.getElementById(page.elementId)) return true;
        if (page.path && currentPath.includes(page.path)) return true;
        return false;
    });
};

const loginButton = document.getElementById('btn-login');
const profileButton = document.getElementById('btn-profile');

const updateNavButtons = (user) => {
    if (loginButton) loginButton.style.display = user ? 'none' : 'inline-flex';
    if (profileButton) profileButton.style.display = user ? 'inline-flex' : 'none';
};

onAuthStateChanged(auth, async (user) => {
    const pageRule = matchCurrentPageConfig();

    // CASO 1: No hay usuario autenticado
    if (!user) {
        SessionManager.clearLocalToken();

        // Si la página requiere login, lo expulsa a /ingreso
        if (pageRule?.requiresAuth) {
            window.location.replace(pageRule.redirectFallback || '/ingreso');
            return;
        }

        updateNavButtons(null);
        hidePageLoader();
        return;
    }

    // CASO 2: Usuario autenticado intentando entrar a Login o Registro
    if (pageRule?.guestOnly && !isSubmittingAuth) {
        window.location.replace(pageRule.redirectFallback || '/');
        return;
    }

    if (isSubmittingAuth) return;

    // CASO 3: Usuario autenticado -> Validar Sesión Única y Roles
    const tokenLocal = SessionManager.getLocalToken();

    try {
        const userDocRef = doc(db, "prospectos", user.uid);
        const userDocSnap = await getDoc(userDocRef);

        if (userDocSnap.exists()) {
            const userData = userDocSnap.data();
            const tokenRemoto = userData.tokenID || userData.session_id;

            if (tokenRemoto && tokenLocal && tokenLocal !== tokenRemoto) {
                console.warn('[SmartBids] ⚠️ Sesión caducada.');
                SessionManager.clearLocalToken();
                await signOut(auth);

                sessionStorage.setItem('flash_message', JSON.stringify({
                    texto: 'Tu sesión ha caducado porque se inició sesión desde otro dispositivo.',
                    tipo: 'error'
                }));

                window.location.replace('/ingreso');
                return;
            }

            if (pageRule?.requiredRole && userData.estado !== pageRule.requiredRole) {
                sessionStorage.setItem('flash_message', JSON.stringify({
                    texto: pageRule.errorMsg || 'Acceso denegado.',
                    tipo: 'error'
                }));
                window.location.replace(pageRule.redirectFallback || '/');
                return;
            }
        }
    } catch (error) {
        console.error('[SmartBids] ❌ Error validando permisos:', error);
    }

    // Inicializar perfil si está en la vista correspondiente
    if (document.getElementById('profile-email')) {
        inicializarVistaPerfil(user);
    }

    updateNavButtons(user);
    hidePageLoader();
});

// Variable temporal para retener las credenciales/datos mientras valida el OTP
let pendingEmail = null;
let pendingPassword = null;
let pendingUid = null;

// ==========================================================================
// 5. Inicio de Sesión y Verificación OTP (2FA)
// ==========================================================================
const loginForm = document.getElementById('login-form');
const otpInputs = document.querySelectorAll('.otp-digit-input, .otp-input');
const btnVerificarOtp = document.getElementById('btn-verificar-otp');
const btnCancelarOtp = document.getElementById('btn-cancelar-otp');
const otpMessage = document.getElementById('otp-message');

// Configurar comportamiento de los 6 inputs OTP
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
            // 1. Validar credenciales temporalmente
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;

            if (!user.emailVerified) {
                await signOut(auth);
                isSubmittingAuth = false;
                setButtonLoading(submitBtn, false);
                mostrarMensaje(MENSAJES.auth.emailNoVerificado, 'error');
                return;
            }

            // 2. Solicitar envío de código al backend Django
            const response = await fetch('/api/enviar-codigo-login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: user.email })
            });

            const resData = await response.json();
            if (!response.ok || resData.status !== 'ok') {
                throw new Error(resData.mensaje || 'Error al enviar el código de verificación.');
            }

            // 3. Guardar código en Firestore mientras aún tiene permiso
            const userRef = doc(db, "prospectos", user.uid);
            await setDoc(userRef, {
                login_code: String(resData.codigo),
                code_created_at: serverTimestamp()
            }, { merge: true });

            // 4. Guardar datos temporales y CERRAR la sesión de Firebase de inmediato
            // (Así, si el usuario refresca la página, Firebase no lo detectará como logueado)
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

// Validar código ingresado en el Modal
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
            // 1. Reautenticar para validar y escribir sesión definitiva
            isSubmittingAuth = true;
            const userCredential = await signInWithEmailAndPassword(auth, pendingEmail, pendingPassword);
            const user = userCredential.user;

            const userDocRef = doc(db, "prospectos", user.uid);
            const userDocSnap = await getDoc(userDocRef);

            if (!userDocSnap.exists()) {
                throw new Error('No se encontró información del usuario.');
            }

            const data = userDocSnap.data();

            // 2. Validar coincidencia del código
            if (String(data.login_code) !== codigoIngresado) {
                await signOut(auth); // Desloguear si el código fue erróneo
                isSubmittingAuth = false;
                setButtonLoading(btnVerificarOtp, false);
                otpMessage.textContent = 'Código incorrecto. Inténtalo de nuevo.';
                return;
            }

            // 3. Generar token de sesión y confirmar Firestore
            const tokenID = generateSessionId();
            SessionManager.setLocalToken(tokenID);

            await setDoc(userDocRef, {
                tokenID: tokenID,
                session_id: tokenID,
                login_code: null, // Limpiar código utilizado
                ultima_conexion: serverTimestamp()
            }, { merge: true });

            sessionStorage.setItem('flash_message', JSON.stringify({
                texto: '¡Bienvenido! Sesión iniciada con éxito.',
                tipo: 'exito'
            }));

            // Limpiar memoria temporal
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
            const response = await fetch('https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key=AIzaSyBlCZkRsr39TbPnL3fse3QH-W3oMIv7384', {
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
// 8. Registro de Nuevo Usuario y Creación de Prospecto en Firestore
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

        const secondaryApp = initializeApp(firebaseConfig, `SecondaryApp_${Date.now()}`);
        const secondaryAuth = getAuth(secondaryApp);
        const secondaryDb = getFirestore(secondaryApp);

        try {
            const userCredential = await createUserWithEmailAndPassword(secondaryAuth, email, password);
            const user = userCredential.user;

            // 1. Guardar documento en Firestore
            await setDoc(doc(secondaryDb, "prospectos", user.uid), {
                uid: user.uid,
                email: user.email,
                telefono: "",
                fecha_creacion: serverTimestamp(),
                username: "",
                pnombre: "",
                snombre: "",
                appaterno: "",
                apmaterno: "",
                tokenID: "",
                estado: "prospecto",
                creadoEl: serverTimestamp()
            });

            // 2. Correo de verificación de Firebase Auth
            await sendEmailVerification(user);

            // 3. Enviar correo de bienvenida mediante el servidor SMTP Django
            try {
                await fetch('/api/enviar-correo-bienvenida/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: user.email })
                });
            } catch (mailErr) {
                console.warn('[SmartBids] No se pudo enviar correo de bienvenida:', mailErr);
            }

            // 4. Mensaje temporal y redirección a ingreso
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
// 9. GESTIÓN DE ALERTAS (PANEL ADMIN)
// ==========================================================================
const formMensajeria = document.getElementById('form-mensajeria');
const listaAlertasAdmin = document.getElementById('lista-alertas-admin');
const inputMsgId = document.getElementById('msg-id');
const selectEstado = document.getElementById('msg-estado');
const selectTipo = document.getElementById('msg-tipo');
const btnCancelar = document.getElementById('btn-cancelar-edicion');
const statusFeedback = document.getElementById('mensaje-status-feedback');

if (formMensajeria) {
    const colMensajeria = collection(db, "mensajeria");

    // Escuchar alertas en tiempo real
    const qAdmin = query(colMensajeria, orderBy("creadoEl", "desc"));
    onSnapshot(qAdmin, (snapshot) => {
        if (!listaAlertasAdmin) return;
        listaAlertasAdmin.innerHTML = '';

        if (snapshot.empty) {
            listaAlertasAdmin.innerHTML = `
                <div class="mockup-item" style="justify-content: center; padding: 2rem; color: var(--gray-text);">
                    <p style="margin: 0; font-size: 0.95rem;">No hay alertas registradas actualmente.</p>
                </div>
            `;
            return;
        }

        snapshot.forEach((docSnap) => {
            const data = docSnap.data();
            const id = docSnap.id;

            const esActivo = data.estado === 'activo';
            const estadoTexto = esActivo ? 'Activo' : 'Inactivo';
            const tipoAlerta = data.tipoAlerta || 'alerta';

            // Estilos de badge según el tipo de alerta definido en style.css
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

            // Botón Eliminar con confirmación integrada
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
                    await deleteDoc(doc(db, "mensajeria", id));
                    mostrarMensaje('Alerta eliminada correctamente.', 'exito');
                } catch (error) {
                    console.error('Error al eliminar mensaje en Firestore:', error);
                    mostrarMensaje('No se pudo eliminar el mensaje.', 'error');
                    btnDelete.disabled = false;
                    btnDelete.textContent = "Eliminar";
                    btnDelete.style.background = "#fff5f5";
                    btnDelete.style.color = "#e53e3e";
                }
            });

            listaAlertasAdmin.appendChild(item);
        });
    }, (error) => {
        console.error('Error al escuchar mensajes en panel admin:', error);
    });

    // Guardar Alerta (Crear o Modificar)
    formMensajeria.addEventListener('submit', async (e) => {
        e.preventDefault();

        const idActual = inputMsgId.value;
        const asunto = document.getElementById('msg-asunto').value.trim();
        const cuerpo = document.getElementById('msg-cuerpo').value.trim();
        const estado = selectEstado ? selectEstado.value : 'activo';
        const tipoAlerta = selectTipo ? selectTipo.value : 'alerta';

        const docData = {
            asunto: asunto,
            cuerpo: cuerpo,
            estado: estado,
            tipoAlerta: tipoAlerta,
            actualizadoEl: serverTimestamp()
        };

        if (statusFeedback) {
            statusFeedback.style.display = 'inline-flex';
            statusFeedback.textContent = 'Guardando...';
        }

        try {
            if (idActual) {
                await setDoc(doc(db, "mensajeria", idActual), docData, { merge: true });
            } else {
                docData.creadoEl = serverTimestamp();
                await addDoc(colMensajeria, docData);
            }

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
            mostrarMensaje('Mensaje guardado correctamente.', 'exito');
        } catch (error) {
            console.error('Error al guardar mensaje en Firestore:', error);
            if (statusFeedback) {
                statusFeedback.textContent = 'Error al guardar.';
            }
            mostrarMensaje('Error al guardar el mensaje.', 'error');
        }
    });

    // Botón Cancelar
    if (btnCancelar) {
        btnCancelar.addEventListener('click', () => {
            formMensajeria.reset();
            inputMsgId.value = '';
            btnCancelar.hidden = true;
        });
    }
}

// ==========================================================================
// 10. ESCUCHA Y DESPLIEGUE PÚBLICO DE ALERTAS
// ==========================================================================
const colMensajes = collection(db, "mensajeria");
const qMensajesActivos = query(colMensajes, where("estado", "==", "activo"));

onSnapshot(qMensajesActivos, (snapshot) => {
    snapshot.forEach((docSnap) => {
        renderizarAlerta(docSnap.id, docSnap.data());
    });
});

// ==========================================================================
// SECCIÓN PERFIL: Lectura y Actualización en Tiempo Real desde Firestore
// ==========================================================================

function formatTimestamp(ts) {
    if (!ts) return 'No registrada';
    const date = ts.toDate ? ts.toDate() : new Date(ts);
    return date.toLocaleDateString('es-CL', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function inicializarVistaPerfil(user) {
    if (!user) return;
    const userDocRef = doc(db, "prospectos", user.uid);

    // 1. Lectura en tiempo real del documento de Firestore
    onSnapshot(userDocRef, (docSnap) => {
        if (!docSnap.exists()) return;
        const data = docSnap.data();

        // Control de visibilidad para el apartado exclusivo de Administrador
        const adminSection = document.getElementById('admin-services-section');
        if (adminSection) {
            adminSection.style.display = (data.estado === 'admin') ? 'block' : 'none';
        }

        // Header / Lateral
        const pnombre = data.pnombre || '';
        const appaterno = data.appaterno || '';
        const snombre = data.snombre || '';
        const apmaterno = data.apmaterno || '';
        const nombreCompleto = [pnombre, snombre, appaterno, apmaterno].filter(Boolean).join(' ') || 'Usuario';
        
        const elFullName = document.getElementById('profile-fullname-header');
        if (elFullName) elFullName.textContent = nombreCompleto;

        const elUsernameHeader = document.getElementById('profile-username-header');
        if (elUsernameHeader) elUsernameHeader.textContent = `@${data.username || 'sin_usuario'}`;

        const elBadgeRole = document.getElementById('profile-role-badge');
        if (elBadgeRole) elBadgeRole.textContent = data.estado || 'prospecto';

        const elRole = document.getElementById('profile-estado');
        if (elRole) elRole.textContent = data.estado || 'prospecto';

        // Iniciales para el avatar
        const elInitials = document.getElementById('profile-initials');
        if (elInitials) {
            const iniP = pnombre ? pnombre[0] : '';
            const iniA = appaterno ? appaterno[0] : '';
            elInitials.textContent = (iniP + iniA).toUpperCase() || 'SB';
        }

        // Metadatos
        const elUid = document.getElementById('profile-uid-header');
        if (elUid) elUid.textContent = user.uid;

        const elCreated = document.getElementById('profile-created-at');
        if (elCreated) elCreated.textContent = formatTimestamp(data.creadoEl || data.fecha_creacion);

        const elLastLogin = document.getElementById('profile-last-login');
        if (elLastLogin) elLastLogin.textContent = formatTimestamp(data.ultima_conexion);

        // Inputs del Formulario Datos Personales
        const inPnombre = document.getElementById('profile-pnombre');
        const inSnombre = document.getElementById('profile-snombre');
        const inAppaterno = document.getElementById('profile-appaterno');
        const inApmaterno = document.getElementById('profile-apmaterno');
        const inUsername = document.getElementById('profile-username');
        const inTelefono = document.getElementById('profile-telefono');
        const inEmail = document.getElementById('profile-email');

        if (inPnombre && document.activeElement !== inPnombre) inPnombre.value = data.pnombre || '';
        if (inSnombre && document.activeElement !== inSnombre) inSnombre.value = data.snombre || '';
        if (inAppaterno && document.activeElement !== inAppaterno) inAppaterno.value = data.appaterno || '';
        if (inApmaterno && document.activeElement !== inApmaterno) inApmaterno.value = data.apmaterno || '';
        if (inUsername && document.activeElement !== inUsername) inUsername.value = data.username || '';
        if (inTelefono && document.activeElement !== inTelefono) inTelefono.value = data.telefono || '';
        if (inEmail) inEmail.value = user.email || data.email || '';

        // Tokens y Sesiones
        const elSessionId = document.getElementById('profile-session-id');
        const elTokenId = document.getElementById('profile-token-id');
        const tokenActivo = data.tokenID || data.session_id || 'No asignado';
        
        if (elSessionId) elSessionId.textContent = tokenActivo;
        if (elTokenId) elTokenId.textContent = tokenActivo;

        // Estado de verificación
        const elStatus = document.getElementById('profile-status');
        if (elStatus) elStatus.textContent = user.emailVerified ? 'Verificado' : 'No verificado';
    });

    // 2. Guardar cambios en Firestore al enviar formulario de datos
    const formDatos = document.getElementById('form-perfil-datos');
    if (formDatos) {
        formDatos.addEventListener('submit', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const submitBtn = formDatos.querySelector('button[type="submit"]');
            setButtonLoading(submitBtn, true, 'Guardando...');

            try {
                await updateDoc(userDocRef, {
                    pnombre: document.getElementById('profile-pnombre')?.value.trim() || '',
                    snombre: document.getElementById('profile-snombre')?.value.trim() || '',
                    appaterno: document.getElementById('profile-appaterno')?.value.trim() || '',
                    apmaterno: document.getElementById('profile-apmaterno')?.value.trim() || '',
                    username: document.getElementById('profile-username')?.value.trim() || '',
                    telefono: document.getElementById('profile-telefono')?.value.trim() || '',
                    actualizadoEl: serverTimestamp()
                });
                mostrarMensaje('Información personal actualizada con éxito.', 'exito');
            } catch (err) {
                console.error('Error actualizando perfil:', err);
                mostrarMensaje('Error al actualizar los datos en Firestore.', 'error');
            } finally {
                setButtonLoading(submitBtn, false);
            }
        });
    }

    // 3. Formulario de Cambio de Contraseña
    const formPass = document.getElementById('form-perfil-password') || document.getElementById('form-change-password');
    if (formPass) {
        formPass.addEventListener('submit', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            limpiarMensaje();

            const currentPass = document.getElementById('profile-current-pass')?.value || document.getElementById('current-password')?.value || '';
            const newPass = document.getElementById('profile-new-pass')?.value || document.getElementById('new-password')?.value || '';
            const confirmPass = document.getElementById('profile-confirm-pass')?.value || document.getElementById('confirm-password')?.value || '';

            if (!currentPass || !newPass || !confirmPass) {
                mostrarMensaje(MENSAJES?.validacion?.camposRequeridos || 'Por favor, completa todos los campos requeridos.', 'error');
                return;
            }

            if (newPass !== confirmPass) {
                mostrarMensaje(MENSAJES?.validacion?.passwordsNoCoinciden || 'Las contraseñas no coinciden.', 'error');
                return;
            }

            if (newPass.length < 6) {
                mostrarMensaje('La nueva contraseña debe tener al menos 6 caracteres.', 'error');
                return;
            }

            const submitBtn = formPass.querySelector('button[type="submit"]');
            setButtonLoading(submitBtn, true, 'Actualizando...');

            try {
                // 1. Reautenticar usuario antes de cambiar credenciales
                const cred = EmailAuthProvider.credential(user.email, currentPass);
                await reauthenticateWithCredential(user, cred);
                
                // 2. Actualizar contraseña en Firebase Auth
                await updatePassword(user, newPass);

                // 3. Notificar por correo mediante la API de Django
                try {
                    await fetch('/api/enviar-correo-cambio-password/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email: user.email })
                    });
                } catch (mailErr) {
                    console.warn('[SmartBids] No se pudo enviar el correo de cambio de contraseña:', mailErr);
                }

                // 4. Guardar mensaje flash para mostrarlo al llegar a la vista de login
                sessionStorage.setItem('flash_message', JSON.stringify({
                    texto: 'Contraseña actualizada correctamente. Por favor, inicia sesión con tu nueva clave.',
                    tipo: 'exito'
                }));

                // 5. Limpiar token local y cerrar sesión
                if (typeof SessionManager !== 'undefined' && SessionManager.clearLocalToken) {
                    SessionManager.clearLocalToken();
                }
                await signOut(auth);

                // 6. Redirigir a la vista de ingreso
                window.location.href = '/ingreso';

            } catch (err) {
                setButtonLoading(submitBtn, false);
                console.error('[SmartBids] Error al cambiar contraseña:', err);
                mostrarMensaje(getFriendlyErrorMessage(err.code, err.message), 'error');
            }
        });
    }

    // 4. Copiado de Tokens
    const setupCopyBtn = (btnId, textSpanId, msg) => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const text = document.getElementById(textSpanId)?.textContent;
                if (text && text !== '--' && text !== 'No asignado') {
                    navigator.clipboard.writeText(text).then(() => mostrarMensaje(msg, 'exito'));
                }
            });
        }
    };
    setupCopyBtn('copy-session-id', 'profile-session-id', 'Session ID copiado al portapapeles.');
    setupCopyBtn('copy-token-id', 'profile-token-id', 'Token ID copiado al portapapeles.');
}