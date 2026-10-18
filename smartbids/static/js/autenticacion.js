import { initializeApp, deleteApp } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js';
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut
} from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js';
import { firebaseConfig, auth } from './firebase-config.js';
import { AuthState } from './auth-state.js';
import {
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

const mensajeFlash = sessionStorage.getItem('flash_message');
if (mensajeFlash) {
    try {
        const flashData = JSON.parse(mensajeFlash);
        mostrarMensaje(flashData.texto, flashData.tipo, flashData.duracion || 14000);
    } catch (e) {
        console.error('Error parseando mensaje flash:', e);
    }
    sessionStorage.removeItem('flash_message');
}

const registeredEmail = sessionStorage.getItem('registered_email');
if (registeredEmail) {
    const emailInput = document.getElementById('email');
    if (emailInput && !emailInput.value) {
        emailInput.value = registeredEmail;
    }
    sessionStorage.removeItem('registered_email');
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
const btnReenviarOtp = document.getElementById('btn-reenviar-otp');
const otpMessage = document.getElementById('otp-message');
let temporizadorReenvioOtp = null;

function iniciarCooldownReenvio() {
    if (!btnReenviarOtp) return;

    let segundosRestantes = 60;
    btnReenviarOtp.disabled = true;
    btnReenviarOtp.textContent = `Reenviar código (${segundosRestantes}s)`;

    if (temporizadorReenvioOtp) {
        clearInterval(temporizadorReenvioOtp);
    }

    temporizadorReenvioOtp = setInterval(() => {
        segundosRestantes -= 1;

        if (segundosRestantes <= 0) {
            clearInterval(temporizadorReenvioOtp);
            temporizadorReenvioOtp = null;
            btnReenviarOtp.disabled = false;
            btnReenviarOtp.textContent = 'Reenviar código';
            return;
        }

        btnReenviarOtp.textContent = `Reenviar código (${segundosRestantes}s)`;
    }, 1000);
}

// Función auxiliar para auto-enviar si se completaron los 6 dígitos
function verificarSiEstaCompletoYEnviar() {
    const codigoIngresado = Array.from(otpInputs).map(input => input.value.trim()).join('');
    if (codigoIngresado.length === otpInputs.length && btnVerificarOtp && !btnVerificarOtp.disabled) {
        btnVerificarOtp.click();
    }
}

// Control de navegación, pegado y envío automático en los inputs OTP
otpInputs.forEach((input, index) => {
    // 1. Al pegar los dígitos (Ctrl+V / Pegar del menú)
    input.addEventListener('paste', (e) => {
        e.preventDefault();
        const textoPegado = (e.clipboardData || window.clipboardData).getData('text').trim();
        const digitos = textoPegado.replace(/\D/g, ''); // Deja solo números

        if (!digitos) return;

        // Distribuye un dígito por cada casillero
        digitos.split('').slice(0, otpInputs.length).forEach((char, i) => {
            if (otpInputs[i]) {
                otpInputs[i].value = char;
            }
        });

        // Lleva el foco al casillero correspondiente
        const siguienteFoco = Math.min(digitos.length, otpInputs.length) - 1;
        if (siguienteFoco >= 0) {
            otpInputs[Math.min(siguienteFoco + 1, otpInputs.length - 1)].focus();
        }

        // Si se pegaron los 6 dígitos completos, presiona el botón automáticamente
        verificarSiEstaCompletoYEnviar();
    });

    // 2. Al escribir dígito por dígito
    input.addEventListener('input', (e) => {
        e.target.value = e.target.value.replace(/\D/g, '');
        if (e.target.value.length === 1 && index < otpInputs.length - 1) {
            otpInputs[index + 1].focus();
        }

        // Si se llenó la última casilla o ya están todos completos, dispara la validación
        verificarSiEstaCompletoYEnviar();
    });

    // 3. Retroceso al borrar con Backspace
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && !input.value && index > 0) {
            otpInputs[index - 1].focus();
        }
    });
});

function esEmailValido(email) {
    if (!email || typeof email !== 'string') return false;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

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

        if (!esEmailValido(email)) {
            mostrarMensaje('El formato del correo ingresado no es válido. Ingresa una dirección completa (ej: usuario@empresa.cl).', 'error', 12000);
            document.getElementById('email').focus();
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
                mostrarMensaje(
                    'Tu cuenta aún no está activada. Revisa tu bandeja de entrada o tu carpeta de SPAM. Si necesitas reenviar el correo de activación, usa el botón "Ayuda".',
                    'error',
                    15000
                );
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
                const error = new Error(resData.mensaje || 'Error al enviar el código de verificación.');
                error.status = response.status;
                throw error;
            }

            pendingEmail = email;
            pendingPassword = password;
            pendingUid = user.uid;

            await signOut(auth);

            abrirModal2FA();
            iniciarCooldownReenvio();

        } catch (error) {
            if (error.status === 429) {
                await signOut(auth);
                mostrarMensaje(error.message, 'error');
            } else {
                console.error('[SmartBids] ❌ Error en inicio de sesión:', error);
                mostrarMensaje(getFriendlyErrorMessage(error.code, error.message), 'error');
            }
        } finally {
            AuthState.isSubmittingAuth = false;
            setButtonLoading(submitBtn, false);
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
            const userCredential = await signInWithEmailAndPassword(auth, pendingEmail, pendingPassword);
            const user = userCredential?.user;

            // 4. Guardar token en LocalStorage y mostrarlo en la consola
            SessionManager.setLocalToken(tokenID);
            console.log(`tokenID: ${tokenID}`);

            if (user?.uid) {
                localStorage.setItem('smartbids_uid', user.uid);
                document.cookie = `sb_firebase_uid=${user.uid}; path=/; max-age=604800; SameSite=Lax`;
            }

            sessionStorage.setItem('flash_message', JSON.stringify({
                texto: '¡Bienvenido! Sesión iniciada con éxito.',
                tipo: 'exito'
            }));

            pendingEmail = null;
            pendingPassword = null;
            pendingUid = null;

            AuthState.isSubmittingAuth = false;
            window.location.href = '/resumen/';

        } catch (error) {
            AuthState.isSubmittingAuth = false;
            setButtonLoading(btnVerificarOtp, false);
            console.error('[SmartBids] ❌ Error al verificar código:', error);
            otpMessage.textContent = error.message || 'Error al validar el código.';
        }
    });
}

if (btnReenviarOtp) {
    btnReenviarOtp.addEventListener('click', async () => {
        if (!pendingEmail || btnReenviarOtp.disabled) return;

        btnReenviarOtp.disabled = true;
        btnReenviarOtp.textContent = 'Enviando...';
        otpMessage.textContent = '';

        try {
            const response = await fetch('/api/enviar-codigo-login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: pendingEmail, reenvio: true })
            });
            const data = await response.json();

            if (!response.ok || data.status !== 'ok') {
                throw new Error(data.mensaje || 'No se pudo reenviar el código.');
            }

            otpInputs.forEach((input) => (input.value = ''));
            otpInputs[0]?.focus();
            otpMessage.textContent = 'Se envió un nuevo código a tu correo.';
            iniciarCooldownReenvio();
        } catch (error) {
            btnReenviarOtp.disabled = false;
            btnReenviarOtp.textContent = 'Reenviar código';
            otpMessage.textContent = error.message;
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
// 5.1 Reenvío de Correo de Activación
// ==========================================================================
async function solicitarReenvioActivacion(targetBtn = null) {
    limpiarMensaje();
    const emailInput = document.getElementById('email');
    const email = emailInput ? emailInput.value.trim() : '';

    if (!email) {
        mostrarMensaje('Ingresa tu correo electrónico en el campo superior para reenviar la activación.', 'error', 12000);
        if (emailInput) emailInput.focus();
        return;
    }

    if (!esEmailValido(email)) {
        mostrarMensaje('El formato del correo ingresado no es válido. Ingresa una dirección completa (ej: usuario@empresa.cl).', 'error', 12000);
        if (emailInput) emailInput.focus();
        return;
    }

    const resendBtn = targetBtn || document.getElementById('btn-reenviar-activacion');
    if (resendBtn) {
        setButtonLoading(resendBtn, true, 'Enviando correo...');
    }

    try {
        const response = await fetch('/api/reenviar-correo-activacion/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });

        const data = await response.json();

        if (response.status === 429) {
            mostrarMensaje(data.mensaje || 'Espera un momento antes de volver a solicitar el correo.', 'error', 12000);
            return;
        }

        if (response.status === 404) {
            mostrarMensaje(data.mensaje || 'No existe una cuenta registrada con este correo.', 'error', 12000);
            return;
        }

        if (response.status === 400) {
            mostrarMensaje(data.mensaje || 'El formato del correo no es válido.', 'error', 12000);
            return;
        }

        if (!response.ok || data.status !== 'ok') {
            throw new Error(data.mensaje || 'No se pudo reenviar el correo de activación.');
        }

        mostrarMensaje(
            '¡Correo de activación reenviado! Por favor revisa tu bandeja de entrada o tu carpeta de SPAM / correo no deseado.',
            'exito',
            16000
        );

    } catch (error) {
        console.error('[SmartBids] Error al reenviar correo de activación:', error);
        mostrarMensaje(error.message || 'Error al reenviar el correo. Inténtalo más tarde.', 'error', 12000);
    } finally {
        if (resendBtn) {
            setButtonLoading(resendBtn, false);
        }
    }
}

const btnReenviarActivacion = document.getElementById('btn-reenviar-activacion');
if (btnReenviarActivacion) {
    btnReenviarActivacion.addEventListener('click', (e) => {
        e.preventDefault();
        solicitarReenvioActivacion(btnReenviarActivacion);
    });
}

// Botón de ayuda para desplegar opciones en el login
const btnAyudaLogin = document.getElementById('btn-ayuda-login');
const ayudaLoginPanel = document.getElementById('ayuda-login-panel');
if (btnAyudaLogin && ayudaLoginPanel) {
    btnAyudaLogin.addEventListener('click', (e) => {
        e.preventDefault();
        const estaAbierto = ayudaLoginPanel.style.display === 'block';
        if (estaAbierto) {
            ayudaLoginPanel.style.display = 'none';
            btnAyudaLogin.setAttribute('aria-expanded', 'false');
            btnAyudaLogin.classList.remove('active');
        } else {
            ayudaLoginPanel.style.display = 'block';
            btnAyudaLogin.setAttribute('aria-expanded', 'true');
            btnAyudaLogin.classList.add('active');
        }
    });
}

const linkAbrirReenvio = document.getElementById('link-abrir-reenvio-activacion');
if (linkAbrirReenvio) {
    linkAbrirReenvio.addEventListener('click', (e) => {
        e.preventDefault();
        if (ayudaLoginPanel) ayudaLoginPanel.style.display = 'block';
        solicitarReenvioActivacion();
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
            if (emailInput) emailInput.focus();
            return;
        }

        if (!esEmailValido(email)) {
            mostrarMensaje('El formato del correo ingresado no es válido. Ingresa una dirección completa (ej: usuario@empresa.cl).', 'error', 12000);
            if (emailInput) emailInput.focus();
            return;
        }

        const originalHtml = forgotPasswordLink.innerHTML;
        forgotPasswordLink.style.pointerEvents = 'none';
        forgotPasswordLink.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Enviando...`;

        try {
            const response = await fetch('/api/solicitar-recuperacion-password/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email })
            });

            const data = await response.json();
            forgotPasswordLink.style.pointerEvents = 'auto';
            forgotPasswordLink.innerHTML = originalHtml;

            if (!response.ok || data.status !== 'ok') {
                mostrarMensaje(data.mensaje || MENSAJES.auth.resetPasswordError, 'error');
                return;
            }

            mostrarMensaje(data.mensaje || MENSAJES.auth.resetPasswordEnviado, 'exito', 16000);
        } catch (error) {
            forgotPasswordLink.style.pointerEvents = 'auto';
            forgotPasswordLink.innerHTML = originalHtml;
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

        const firstName = document.getElementById('register-first-name').value.trim();
        const lastName = document.getElementById('register-last-name').value.trim();
        const email = document.getElementById('email').value.trim();
        const emailConfirm = document.getElementById('email-confirm').value.trim();
        const password = document.getElementById('password').value;
        const passwordConfirm = document.getElementById('password-confirm').value;

        if (!firstName || !lastName || !email || !emailConfirm || !password || !passwordConfirm) {
            mostrarMensaje(MENSAJES.validacion.camposRequeridos, 'error');
            return;
        }

        if (firstName.length > 100 || lastName.length > 100) {
            mostrarMensaje('El nombre y el apellido no pueden superar los 100 caracteres.', 'error');
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
        setButtonLoading(submitBtn, true, 'Verificando correo...');

        let secondaryApp = null;
        try {
            // 1. Validar que el correo exista en Gmail y no esté ya registrado
            const resValidacion = await fetch('/api/validar-email-registro/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email })
            });

            const dataValidacion = await resValidacion.json();
            if (!resValidacion.ok || dataValidacion.status !== 'ok') {
                setButtonLoading(submitBtn, false);
                mostrarMensaje(dataValidacion.mensaje || 'El correo ingresado no es válido para el registro.', 'error', 12000);
                return;
            }

            setButtonLoading(submitBtn, true, 'Registrando...');

            secondaryApp = initializeApp(firebaseConfig, `SecondaryApp_${Date.now()}`);
            const secondaryAuth = getAuth(secondaryApp);

            const userCredential = await createUserWithEmailAndPassword(secondaryAuth, email, password);
            const user = userCredential.user;

            const resDb = await fetch('/api/registrar-prospecto/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    uid: user.uid,
                    sus_nombre1: firstName,
                    sus_apellido1: lastName
                })
            });

            const resultadoDb = await resDb.json();
            if (!resDb.ok || resultadoDb.status !== 'ok') {
                throw new Error(resultadoDb.mensaje || 'No se pudieron guardar tus datos en PostgreSQL.');
            }

            try {
                const response = await fetch('/api/enviar-correo-bienvenida/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ idToken: await user.getIdToken() })
                });
                const resultadoCorreo = await response.json();
                if (!response.ok || resultadoCorreo.status !== 'ok') {
                    throw new Error(resultadoCorreo.mensaje || 'No se pudo enviar el correo de activación.');
                }
            } catch (mailErr) {
                console.error('[SmartBids] No se pudo enviar correo de bienvenida y activación:', mailErr);
                throw mailErr;
            }

            sessionStorage.setItem('flash_message', JSON.stringify({
                texto: MENSAJES.auth.registroExitoso,
                tipo: 'exito',
                duracion: 16000
            }));
            sessionStorage.setItem('registered_email', email);

            window.location.href = '/ingreso';
        } catch (error) {
            setButtonLoading(submitBtn, false);
            console.error('Error durante el registro:', error);
            mostrarMensaje(
                error.code ? getFriendlyErrorMessage(error.code, error.message) : (error.message || 'No se pudieron guardar tus datos.'),
                'error'
            );
        } finally {
            if (secondaryApp) {
                await deleteApp(secondaryApp);
            }
        }
    });
}