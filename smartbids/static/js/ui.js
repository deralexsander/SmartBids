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

        if (btn && input && icon && btn.dataset.passwordToggleBound !== 'true') {
            btn.dataset.passwordToggleBound = 'true';
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

export function setupExportModal() {
    const modal = document.getElementById('modal-exportar-reporte');
    if (!modal) return;

    const btnCerrar = document.getElementById('btn-cerrar-modal-exportar');
    const btnCancelar = document.getElementById('btn-cancelar-modal-exportar');
    const btnCsv = document.getElementById('btn-exportar-formato-csv');
    const btnExcel = document.getElementById('btn-exportar-formato-excel');

    let currentExportUrl = '';

    const cerrarModal = () => {
        modal.classList.remove('active');
        modal.classList.add('closing');
        modal.setAttribute('aria-hidden', 'true');
        setTimeout(() => {
            modal.classList.remove('closing');
        }, 400);
    };

    const abrirModal = (targetUrl) => {
        currentExportUrl = targetUrl;
        modal.classList.remove('closing');
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
    };
    window.abrirModalExportar = abrirModal;

    const descargar = (formato) => {
        if (!currentExportUrl) return;
        try {
            const urlObj = new URL(currentExportUrl, window.location.origin);
            urlObj.searchParams.set('formato', formato);
            window.location.assign(urlObj.toString());
        } catch {
            const sep = currentExportUrl.includes('?') ? '&' : '?';
            window.location.assign(`${currentExportUrl}${sep}formato=${formato}`);
        }
        cerrarModal();
    };

    if (btnCerrar) btnCerrar.addEventListener('click', cerrarModal);
    if (btnCancelar) btnCancelar.addEventListener('click', cerrarModal);

    modal.addEventListener('click', (e) => {
        if (e.target === modal) cerrarModal();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            cerrarModal();
        }
    });

    if (btnCsv) {
        btnCsv.addEventListener('click', (e) => {
            e.preventDefault();
            descargar('csv');
        });
    }

    if (btnExcel) {
        btnExcel.addEventListener('click', (e) => {
            e.preventDefault();
            descargar('xlsx');
        });
    }

    document.addEventListener('click', (e) => {
        const trigger = e.target.closest('[data-export-url]');
        if (trigger) {
            e.preventDefault();
            let targetUrl = trigger.dataset.exportUrl;
            const periodoSelect = document.getElementById('filtro-periodo');
            if (periodoSelect && targetUrl.includes('/dashboard/exportar/')) {
                try {
                    const urlObj = new URL(targetUrl, window.location.origin);
                    urlObj.searchParams.set('dias', periodoSelect.value);
                    targetUrl = urlObj.pathname + urlObj.search;
                } catch {
                    // Fallback sin procesar
                }
            }
            abrirModal(targetUrl);
        }
    });
}

function inicializarControlesUI() {
    setupPasswordToggles();
    setupExportModal();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarControlesUI, { once: true });
} else {
    inicializarControlesUI();
}