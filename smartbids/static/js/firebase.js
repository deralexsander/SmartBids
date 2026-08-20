import { initializeApp, deleteApp } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js';
import { 
    getAuth, 
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword, 
    sendEmailVerification, 
    signOut,
    onAuthStateChanged 
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
    SessionManager       
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
// Ya NO ejecutamos setupPageLoader() automáticamente aquí
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
// 4. Control de Estado de Autenticación, Seguridad y Cierre del Loader
// ==========================================================================
const loginButton = document.getElementById('btn-login');
const profileButton = document.getElementById('btn-profile');

const updateNavButtons = (user) => {
    if (loginButton) loginButton.style.display = user ? 'none' : 'inline-flex';
    if (profileButton) profileButton.style.display = user ? 'inline-flex' : 'none';
};

onAuthStateChanged(auth, async (user) => {
    const isAuthPage = !!(document.getElementById('login-form') || document.getElementById('register-form'));
    const profileEmail = document.getElementById('profile-email');
    const profileStatus = document.getElementById('profile-status');
    const isProfilePage = !!(profileEmail || profileStatus);
    const isMensajeriaAdminPage = !!document.getElementById('form-mensajeria');

    // 1. Si NO hay usuario autenticado
    if (!user) {
        SessionManager.clearLocalToken();

        // Si intenta entrar a páginas protegidas, redirigir (el loader cubre la transición)
        if (isProfilePage || isMensajeriaAdminPage) {
            window.location.replace('/ingreso');
            return;
        }

        // Si es una página pública o de login/registro, aplicamos UI y mostramos el contenido
        updateNavButtons(null);
        hidePageLoader();
        return;
    }

    // 2. Si hay usuario y está intentando ver login o registro
    if (isAuthPage && !isSubmittingAuth) {
        window.location.replace('/');
        return;
    }

    if (isSubmittingAuth) return;

    // 3. Validar sesión única y roles en Firestore
    const tokenLocal = SessionManager.getLocalToken();

    try {
        const userDocRef = doc(db, "prospectos", user.uid);
        const userDocSnap = await getDoc(userDocRef);

        if (userDocSnap.exists()) {
            const userData = userDocSnap.data();
            const tokenRemoto = userData.tokenID || userData.session_id;

            // Validación de sesión simultánea
            if (tokenRemoto && tokenLocal !== tokenRemoto) {
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

            // Validación de permisos de Administrador
            if (isMensajeriaAdminPage && userData.estado !== 'admin') {
                sessionStorage.setItem('flash_message', JSON.stringify({
                    texto: 'Acceso denegado: Se requieren permisos de administrador.',
                    tipo: 'error'
                }));
                window.location.replace('/');
                return;
            }
        } else if (isMensajeriaAdminPage) {
            // Si no existe documento y está en admin, bloquear acceso
            window.location.replace('/');
            return;
        }
    } catch (error) {
        console.error('[SmartBids] ❌ Error validando permisos:', error);
    }

    // Pintar datos en perfil si corresponde
    if (profileEmail) profileEmail.textContent = user.email || 'No disponible';
    if (profileStatus) profileStatus.textContent = user.emailVerified ? 'Verificado' : 'No verificado';

    // 4. Todo validado correctamente: Aplicamos estado visual a los botones y cerramos el loader
    updateNavButtons(user);
    hidePageLoader();
});
// ==========================================================================
// 5. Cierre de Sesión
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
// 6. Inicio de Sesión
// ==========================================================================
const loginForm = document.getElementById('login-form');
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
        setButtonLoading(submitBtn, true, 'Verificando y guardando sesión...');
        
        // Bloquea verificaciones intermedias durante el inicio
        isSubmittingAuth = true;

        try {
            // 1. Autenticar credenciales
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;

            // 2. Verificar que el correo esté confirmado
            if (!user.emailVerified) {
                await signOut(auth);
                isSubmittingAuth = false;
                setButtonLoading(submitBtn, false);
                mostrarMensaje(MENSAJES.auth.emailNoVerificado, 'error');
                return;
            }

            // 3. Generar token único de la sesión
            const tokenID = generateSessionId();

            // 4. Guardar en almacenamiento local y mostrar en consola
            SessionManager.setLocalToken(tokenID);
            console.log(`[SmartBids] 🔑 Token generado: ${tokenID}`);

            // 5. Guardar en Firestore y esperar confirmación obligatoria
            const userRef = doc(db, "prospectos", user.uid);
            await setDoc(userRef, {
                tokenID: tokenID,
                session_id: tokenID,
                ultima_conexion: serverTimestamp()
            }, { merge: true });

            console.log(`[SmartBids] 💾 Token guardado con éxito en Firestore para UID: ${user.uid}`);

            // 6. Mensaje temporal de confirmación
            sessionStorage.setItem('flash_message', JSON.stringify({
                texto: MENSAJES.auth.loginExitoso,
                tipo: 'exito'
            }));

            // 7. Redirigir al inicio SOLO después de haber guardado todo
            window.location.href = '/';

        } catch (error) {
            isSubmittingAuth = false;
            setButtonLoading(submitBtn, false);
            console.error('[SmartBids] ❌ Error en inicio de sesión o guardado en Firestore:', error);
            mostrarMensaje(getFriendlyErrorMessage(error.code, error.message), 'error');
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