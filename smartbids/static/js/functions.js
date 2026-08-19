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

// 2. Control del Loader inicial de carga visual de página
export function setupPageLoader() {
    window.addEventListener('load', async () => {
        const loader = document.getElementById('page-loader');
        if (!loader) return;

        loader.classList.add('page-loader-done');
        await new Promise((resolve) => setTimeout(resolve, 800));
        document.documentElement.classList.remove('loading');
        loader.style.opacity = '0';
        setTimeout(() => loader.remove(), 400);
    });
}

// 3. Control de Spinner de Carga Giratorio dentro de los Botones
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

// 4. Alternar visibilidad de contraseña
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