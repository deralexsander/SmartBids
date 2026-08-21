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
// 6. Control de Pestañas del Perfil (Accesible globalmente)
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