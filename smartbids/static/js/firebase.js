import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js';
import { 
    getAuth, 
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword, 
    sendEmailVerification, 
    signOut,
    onAuthStateChanged 
} from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js';

// Módulo de Firestore para la creación del prospecto
import { 
    getFirestore, 
    doc, 
    setDoc, 
    serverTimestamp 
} from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js';

import { 
    redirectIfAuthenticated, 
    getFriendlyErrorMessage, 
    setupPageLoader, 
    setupPasswordToggles 
} from './functions.js';

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

if (document.getElementById('login-form') || document.getElementById('register-form')) {
    redirectIfAuthenticated(auth, '/');
}

// 4. Control de Estado de Autenticación de la Navbar y Perfil
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
        }
    });
}

// 6. Inicio de Sesión
const loginForm = document.getElementById('login-form');
const message = document.getElementById('message');

if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        try {
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;

            if (!user.emailVerified) {
                await signOut(auth);
                if (message) {
                    message.textContent = 'Por favor verifica tu correo electrónico antes de ingresar.';
                    message.style.color = 'red';
                }
                return;
            }

            if (message) {
                message.textContent = 'Ingreso exitoso.';
                message.style.color = '#1ec498';
            }
            window.location.replace('/');
        } catch (error) {
            console.error('Error al iniciar sesión:', error);
            if (message) {
                message.textContent = getFriendlyErrorMessage(error.code);
                message.style.color = 'red';
            }
        }
    });
}

// 7. Recuperación de Contraseña
const forgotPasswordLink = document.getElementById('forgot-password-link');
if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener('click', async (e) => {
        e.preventDefault();

        const emailInput = document.getElementById('email');
        const email = emailInput ? emailInput.value.trim() : '';

        if (!email) {
            if (message) {
                message.textContent = 'Ingresa tu correo en el campo superior para recuperar tu contraseña.';
                message.style.color = 'red';
            }
            return;
        }

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

            if (!response.ok) {
                if (data.error && data.error.message === 'EMAIL_NOT_FOUND') {
                    if (message) {
                        message.textContent = 'No existe una cuenta registrada con ese correo.';
                        message.style.color = 'red';
                    }
                } else if (data.error && data.error.message === 'INVALID_EMAIL') {
                    if (message) {
                        message.textContent = 'El formato del correo ingresado no es válido.';
                        message.style.color = 'red';
                    }
                } else {
                    throw new Error(data.error?.message || 'No se pudo enviar el correo.');
                }
                return;
            }

            if (message) {
                message.textContent = 'Se ha enviado un correo para restablecer tu contraseña.';
                message.style.color = '#1ec498';
            }
        } catch (error) {
            console.error(error);
            if (message) {
                message.textContent = 'No se pudo enviar el correo de recuperación. Inténtalo más tarde.';
                message.style.color = 'red';
            }
        }
    });
}

// 8. Registro de Nuevo Usuario y Creación de Prospecto en Firestore
const registerForm = document.getElementById('register-form');
if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('email').value.trim();
        const emailConfirm = document.getElementById('email-confirm').value.trim();
        const password = document.getElementById('password').value;
        const passwordConfirm = document.getElementById('password-confirm').value;

        if (message) {
            message.textContent = '';
            message.style.color = '';
        }

        if (email !== emailConfirm) {
            if (message) {
                message.textContent = 'Los correos no coinciden.';
                message.style.color = 'red';
            }
            return;
        }

        if (password !== passwordConfirm) {
            if (message) {
                message.textContent = 'Las contraseñas no coinciden.';
                message.style.color = 'red';
            }
            return;
        }

        if (password.length < 6) {
            if (message) {
                message.textContent = 'La contraseña debe tener al menos 6 caracteres.';
                message.style.color = 'red';
            }
            return;
        }

        try {
            // 1. Crear el usuario en Authentication
            const userCredential = await createUserWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;

            // 2. Crear automáticamente el registro en la colección "prospectos" de Firestore
            await setDoc(doc(db, "prospectos", user.uid), {
                uid: user.uid,
                email: user.email,
                estado: "prospecto",
                creadoEl: serverTimestamp()
            });

            // 3. Enviar correo de verificación y cerrar sesión
            await sendEmailVerification(user);
            await signOut(auth);

            if (message) {
                message.textContent = 'Registro exitoso. Se ha enviado un correo de verificación a tu email.';
                message.style.color = '#1ec498';
            }
            registerForm.reset();
        } catch (error) {
            console.error('Error durante el registro:', error);

            let friendlyMessage = 'No se pudo completar el registro.';
            if (error.code === 'auth/email-already-in-use') {
                friendlyMessage = 'Ese correo ya está registrado.';
            } else if (error.code === 'auth/invalid-email') {
                friendlyMessage = 'El correo no es válido.';
            } else if (error.code === 'auth/weak-password') {
                friendlyMessage = 'La contraseña debe tener al menos 6 caracteres.';
            } else if (error.code === 'auth/operation-not-allowed') {
                friendlyMessage = 'El método de correo/contraseña no está habilitado en Firebase Console.';
            }

            if (message) {
                message.textContent = friendlyMessage;
                message.style.color = 'red';
            }
        }
    });
}