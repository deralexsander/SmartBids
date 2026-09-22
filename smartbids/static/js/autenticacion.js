import { initializeApp, deleteApp } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js';
import {
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    sendEmailVerification,
    signOut
} from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js';
import { firebaseConfig, auth } from './firebase-config.js';
import { AuthState } from './auth-state.js';
import {
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
    MENSAJES
} from './mensaje.js';

setupPasswordToggles();

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
        AuthState.isSubmittingAuth = true;

        try {
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;

            if (!user.emailVerified) {
                await signOut(auth);
                AuthState.isSubmittingAuth = false;
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

            AuthState.isSubmittingAuth = false;
            setButtonLoading(submitBtn, false);
            abrirModal2FA();

        } catch (error) {
            AuthState.isSubmittingAuth = false;
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
            AuthState.isSubmittingAuth = true;
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

            AuthState.isSubmittingAuth = false;
            window.location.href = '/mis-licitaciones/';

        } catch (error) {
            AuthState.isSubmittingAuth = false;
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
        AuthState.isSubmittingAuth = false;
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


