// 1. Redirección condicional según estado de autenticación
export function redirectIfAuthenticated(auth, redirectPath = '/') {
    const currentPath = window.location.pathname;

    auth.onAuthStateChanged((user) => {
        const shouldRedirect = Boolean(user && user.emailVerified && (
            currentPath.includes('/ingreso') || currentPath.includes('/registro')
        ));

        if (shouldRedirect) {
            window.location.replace(redirectPath);
        }
    });
}

// 2. Diccionario de mensajes de error personalizados en español
export function getFriendlyErrorMessage(errorCode) {
    switch (errorCode) {
        case 'auth/invalid-credential':
        case 'auth/user-not-found':
        case 'auth/wrong-password':
            return 'Correo o contraseña incorrectos. Por favor, verifica tus datos.';
        case 'auth/invalid-email':
            return 'El formato del correo electrónico no es válido.';
        case 'auth/user-disabled':
            return 'Esta cuenta ha sido deshabilitada. Contacta al soporte.';
        case 'auth/too-many-requests':
            return 'Demasiados intentos fallidos. Por favor, reintenta más tarde o restablece tu contraseña.';
        case 'auth/network-request-failed':
            return 'Error de red. Verifica tu conexión a internet.';
        default:
            return 'Ocurrió un error inesperado. Inténtalo nuevamente.';
    }
}

// 3. Control del Loader de carga visual de página
export function setupPageLoader() {
    window.addEventListener('load', async () => {
        const loader = document.getElementById('page-loader');
        if (!loader) return;

        loader.classList.add('page-loader-done');
        await new Promise((resolve) => setTimeout(resolve, 1000));
        document.documentElement.classList.remove('loading');
        loader.style.opacity = '0';
        setTimeout(() => loader.remove(), 400);
    });
}

// 4. Alternar visibilidad de contraseña (Iconos de Ojo)
export function setupPasswordToggles() {
    const togglePasswordButton = document.getElementById('toggle-password');
    const togglePasswordIcon = document.getElementById('toggle-password-icon');
    const togglePasswordConfirmButton = document.getElementById('toggle-password-confirm');
    const togglePasswordConfirmIcon = document.getElementById('toggle-password-confirm-icon');

    if (togglePasswordButton && togglePasswordIcon) {
        togglePasswordButton.addEventListener('click', () => {
            const pwd = document.getElementById('password');
            if (pwd) {
                const isHidden = pwd.type === 'password';
                pwd.type = isHidden ? 'text' : 'password';
                togglePasswordIcon.classList.toggle('fa-eye');
                togglePasswordIcon.classList.toggle('fa-eye-slash');
            }
        });
    }

    if (togglePasswordConfirmButton && togglePasswordConfirmIcon) {
        togglePasswordConfirmButton.addEventListener('click', () => {
            const pwdConf = document.getElementById('password-confirm');
            if (pwdConf) {
                const isHidden = pwdConf.type === 'password';
                pwdConf.type = isHidden ? 'text' : 'password';
                togglePasswordConfirmIcon.classList.toggle('fa-eye');
                togglePasswordConfirmIcon.classList.toggle('fa-eye-slash');
            }
        });
    }
}