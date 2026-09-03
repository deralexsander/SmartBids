// ==========================================================================
// 1. Redirección condicional según estado de autenticación
// ==========================================================================
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

// ==========================================================================
// 2. Control manual para ocultar el Loader de carga
// ==========================================================================
export async function hidePageLoader() {
    const loader = document.getElementById('page-loader');
    if (!loader) return;

    loader.classList.add('page-loader-done');
    await new Promise((resolve) => setTimeout(resolve, 300));
    document.documentElement.classList.remove('loading');
    loader.style.opacity = '0';
    setTimeout(() => {
        if (loader.parentNode) loader.remove();
    }, 400);
}

// ==========================================================================
// 3. Control de Spinner de Carga dentro de Botones
// ==========================================================================
export function setButtonLoading(button, isLoading, loadingText = 'Cargando...') {
    if (!button) return;

    if (isLoading) {
        button.dataset.originalContent = button.innerHTML;
        button.disabled = true;
        button.style.pointerEvents = 'none';
        button.style.opacity = '0.85';
        button.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin" style="margin-right: 8px;"></i> ${loadingText}`;
    } else {
        if (button.dataset.originalContent) {
            button.innerHTML = button.dataset.originalContent;
        }
        button.disabled = false;
        button.style.pointerEvents = 'auto';
        button.style.opacity = '1';
    }
}

// ==========================================================================
// 4. Alternar visibilidad de contraseñas
// ==========================================================================
export function setupPasswordToggles() {
    const bindToggle = (btnId, inputId, iconId) => {
        const btn = document.getElementById(btnId);
        const input = document.getElementById(inputId);
        const icon = document.getElementById(iconId);

        if (btn && input && icon) {
            btn.addEventListener('click', () => {
                const isHidden = input.type === 'password';
                input.type = isHidden ? 'text' : 'password';
                icon.classList.toggle('fa-eye');
                icon.classList.toggle('fa-eye-slash');
            });
        }
    };

    // 1. Formulario estándar (Ingreso / Login y Registro)
    bindToggle('toggle-password', 'password', 'toggle-password-icon');
    bindToggle('toggle-password-confirm', 'password-confirm', 'toggle-password-confirm-icon');

    // 2. Formulario de Cambio de Contraseña (Perfil)
    bindToggle('toggle-profile-current-pass', 'profile-current-pass', 'toggle-profile-current-icon');
    bindToggle('toggle-profile-new-pass', 'profile-new-pass', 'toggle-profile-new-icon');
    bindToggle('toggle-profile-confirm-pass', 'profile-confirm-pass', 'toggle-profile-confirm-icon');
}

// ==========================================================================
// 5. Generación y Manejo de Sesión / Token Local
// ==========================================================================
export function generateSessionId() {
    return crypto.randomUUID();
}

export const SessionManager = {
    setLocalToken(token) {
        localStorage.setItem('smartbids_session_token', token);
    },
    getLocalToken() {
        return localStorage.getItem('smartbids_session_token');
    },
    clearLocalToken() {
        localStorage.removeItem('smartbids_session_token');
    }
};

// ==========================================================================
// 6. Control de Pestañas del Perfil
// ==========================================================================
export function cambiarPestana(event, tabId) {
    document.querySelectorAll('.profile-menu-btn').forEach((btn) => {
        btn.classList.remove('active');
    });

    document.querySelectorAll('.tab-content-panel').forEach((panel) => {
        panel.classList.remove('active');
    });

    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }

    const target = document.getElementById(tabId);
    if (target) {
        target.classList.add('active');
    }
}

window.cambiarPestana = cambiarPestana;



// ==========================================================================
// 7. Control de Modal de Autenticación de Dos Factores (2FA)
// ==========================================================================

// Función para abrir con animación de entrada
export function abrirModal2FA() {
    const modal2FA = document.getElementById('modal-2fa');
    const otpInputs = document.querySelectorAll('.otp-digit-input');

    if (!modal2FA) return;

    modal2FA.classList.remove('closing');
    modal2FA.classList.add('active');

    if (otpInputs.length > 0) {
        otpInputs[0].focus();
    }
}

// Función para cerrar con animación de salida
export function cerrarModal2FA() {
    const modal2FA = document.getElementById('modal-2fa');
    const otpInputs = document.querySelectorAll('.otp-digit-input');

    if (!modal2FA) return;

    modal2FA.classList.add('closing');

    setTimeout(() => {
        modal2FA.classList.remove('active', 'closing');
        otpInputs.forEach((input) => (input.value = ''));
        const otpMsg = document.getElementById('otp-message');
        if (otpMsg) otpMsg.textContent = '';
    }, 400); // 400ms para permitir que la animación culmine
}

window.abrirModal2FA = abrirModal2FA;
window.cerrarModal2FA = cerrarModal2FA;




