// ==========================================================================
// CONTROLES DE INTERFAZ REUTILIZABLES
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

    bindToggle('toggle-password', 'password', 'toggle-password-icon');
    bindToggle('toggle-password-confirm', 'password-confirm', 'toggle-password-confirm-icon');
    bindToggle('toggle-profile-current-pass', 'profile-current-pass', 'toggle-profile-current-icon');
    bindToggle('toggle-profile-new-pass', 'profile-new-pass', 'toggle-profile-new-icon');
    bindToggle('toggle-profile-confirm-pass', 'profile-confirm-pass', 'toggle-profile-confirm-icon');
}