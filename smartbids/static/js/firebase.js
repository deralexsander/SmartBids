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
    setDoc, 
    serverTimestamp 
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
    MENSAJES 
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

// 4. Control de Estado de Autenticación
const loginButton = document.getElementById('btn-login');
const profileButton = document.getElementById('btn-profile');

const updateNavButtons = (user) => {
    if (loginButton) loginButton.style.display = user ? 'none' : 'inline-flex';
    if (profileButton) profileButton.style.display = user ? 'inline-flex' : 'none';
};

onAuthStateChanged(auth, (user) => {
    updateNavButtons(user);

    const profileEmail = document.getElementById('profile-email');
    const profileStatus = document.getElementById('profile-status');
    const isProfilePage = !!(profileEmail || profileStatus);

    if (user) {
        if (profileEmail) profileEmail.textContent = user.email || 'No disponible';
        if (profileStatus) profileStatus.textContent = user.emailVerified ? 'Verificado' : 'No verificado';
    } else if (isProfilePage) {
        window.location.href = '/';
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