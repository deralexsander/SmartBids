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
    setupPageLoader, 
    setupPasswordToggles,
    setButtonLoading 
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

// 3. Inicialización de componentes UI
setupPageLoader();
setupPasswordToggles();

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

if (document.getElementById('login-form') || document.getElementById('register-form')) {
    redirectIfAuthenticated(auth, '/');
}

// 4. Control de Estado de Autenticación y Protección de Vistas
const loginButton = document.getElementById('btn-login');
const profileButton = document.getElementById('btn-profile');

const updateNavButtons = (user) => {
    if (loginButton) loginButton.style.display = user ? 'none' : 'inline-flex';
    if (profileButton) profileButton.style.display = user ? 'inline-flex' : 'none';
};

onAuthStateChanged(auth, async (user) => {
    updateNavButtons(user);

    const profileEmail = document.getElementById('profile-email');
    const profileStatus = document.getElementById('profile-status');
    const isProfilePage = !!(profileEmail || profileStatus);
    const isMensajeriaAdminPage = !!document.getElementById('form-mensajeria');

    // Validación 1: Si no hay usuario autenticado
    if (!user) {
        if (isProfilePage || isMensajeriaAdminPage) {
            window.location.href = '/ingreso';
        }
        return;
    }

    // Si está autenticado, pintar datos en perfil
    if (profileEmail) profileEmail.textContent = user.email || 'No disponible';
    if (profileStatus) profileStatus.textContent = user.emailVerified ? 'Verificado' : 'No verificado';

    // Validación 2: Si está en mensajería, verificar que tenga estado "admin"
    if (isMensajeriaAdminPage) {
        try {
            const userDocSnap = await getDoc(doc(db, "prospectos", user.uid));

            if (!userDocSnap.exists() || userDocSnap.data().estado !== 'admin') {
                sessionStorage.setItem('flash_message', JSON.stringify({
                    texto: 'Acceso denegado: Se requieren permisos de administrador.',
                    tipo: 'error'
                }));
                window.location.href = '/';
            }
        } catch (error) {
            console.error('Error validando permisos de administrador:', error);
            window.location.href = '/';
        }
    }
});

// 5. Cierre de Sesión
const logoutButton = document.getElementById('logout-button');
if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
        try {
            await signOut(auth);
            window.location.href = '/';
        } catch (error) {
            console.error('Error al cerrar sesión:', error);
            mostrarMensaje(MENSAJES.auth.logoutError, 'error');
        }
    });
}

// 6. Inicio de Sesión
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
        setButtonLoading(submitBtn, true, 'Entrando...');

        try {
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;

            if (!user.emailVerified) {
                await signOut(auth);
                setButtonLoading(submitBtn, false);
                mostrarMensaje(MENSAJES.auth.emailNoVerificado, 'error');
                return;
            }

            mostrarMensaje(MENSAJES.auth.loginExitoso, 'exito');
            window.location.replace('/');
        } catch (error) {
            setButtonLoading(submitBtn, false);
            console.error('Error al iniciar sesión:', error);
            mostrarMensaje(getFriendlyErrorMessage(error.code, error.message), 'error');
        }
    });
}

// 7. Recuperación de Contraseña
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

// 8. Registro de Nuevo Usuario y Creación de Prospecto en Firestore
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
                estado: "prospecto",
                creadoEl: serverTimestamp()
            });

            await sendEmailVerification(user);

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
            listaAlertasAdmin.innerHTML = '<p style="color:#666; padding: 10px;">No hay alertas registradas.</p>';
            return;
        }

        snapshot.forEach((docSnap) => {
            const data = docSnap.data();
            const id = docSnap.id;

            const esActivo = data.estado === 'activo';
            const badgeColor = esActivo ? '#28a745' : '#6c757d';
            const estadoTexto = esActivo ? 'Activo' : 'Inactivo';

            const item = document.createElement('div');
            item.style.cssText = "background: #fff; border: 1px solid #e0e0e0; padding: 14px; margin-bottom: 12px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);";

            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #11634e; font-size: 1.05rem;"><strong>${data.asunto || 'Sin Asunto'}</strong></h4>
                    <span style="background: ${badgeColor}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; text-transform: uppercase; font-weight: bold;">
                        ${estadoTexto}
                    </span>
                </div>
                <p style="margin: 8px 0; color: #444; font-size: 0.95rem;">${data.cuerpo || ''}</p>
                <div style="font-size: 0.85rem; color: #777; margin-bottom: 10px;">
                    Tipo: <strong style="text-transform: capitalize;">${data.tipoAlerta || 'alerta'}</strong>
                </div>
                <div style="display: flex; gap: 8px;">
                    <button type="button" class="btn-edit btn" style="padding: 6px 14px; font-size: 0.85rem; background: #1ec498; color: #0b3831; font-weight: bold; cursor: pointer; border: none; border-radius: 6px;">Editar</button>
                    <button type="button" class="btn-delete btn" style="padding: 6px 14px; font-size: 0.85rem; background: #dc3545; color: white; font-weight: bold; cursor: pointer; border: none; border-radius: 6px;">Eliminar</button>
                </div>
            `;

            // Botón Editar
            item.querySelector('.btn-edit').addEventListener('click', () => {
                inputMsgId.value = id;
                document.getElementById('msg-asunto').value = data.asunto || '';
                document.getElementById('msg-cuerpo').value = data.cuerpo || '';
                if (selectEstado) selectEstado.value = data.estado || 'activo';
                if (selectTipo) selectTipo.value = data.tipoAlerta || 'alerta';

                if (btnCancelar) btnCancelar.style.display = 'inline-block';
                formMensajeria.scrollIntoView({ behavior: 'smooth' });
            });

            // Botón Eliminar con confirmación visual integrada
            const btnDelete = item.querySelector('.btn-delete');
            btnDelete.addEventListener('click', async (e) => {
                e.preventDefault();

                if (!btnDelete.dataset.confirming) {
                    btnDelete.dataset.confirming = "true";
                    btnDelete.textContent = "¿Eliminar?";
                    btnDelete.style.background = "#bd2130";

                    setTimeout(() => {
                        btnDelete.dataset.confirming = "";
                        btnDelete.textContent = "Eliminar";
                        btnDelete.style.background = "#dc3545";
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
            statusFeedback.style.color = '#333';
            statusFeedback.textContent = ' Guardando...';
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

            if (btnCancelar) btnCancelar.style.display = 'none';

            if (statusFeedback) {
                statusFeedback.style.color = 'green';
                statusFeedback.textContent = ' ¡Guardado con éxito!';
                setTimeout(() => { statusFeedback.textContent = ''; }, 3000);
            }
            mostrarMensaje('Mensaje guardado correctamente.', 'exito');
        } catch (error) {
            console.error('Error al guardar mensaje en Firestore:', error);
            if (statusFeedback) {
                statusFeedback.style.color = 'red';
                statusFeedback.textContent = ' Error al guardar.';
            }
            mostrarMensaje('Error al guardar el mensaje.', 'error');
        }
    });

    // Botón Cancelar
    if (btnCancelar) {
        btnCancelar.addEventListener('click', () => {
            formMensajeria.reset();
            inputMsgId.value = '';
            btnCancelar.style.display = 'none';
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