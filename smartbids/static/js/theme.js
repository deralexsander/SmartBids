// ==============================================================================
// SMARTBIDS - CONTROLADOR DE TEMA (MODO OSCURO / CLARO)
// Persistencia en localStorage, sincronización de controles y soporte reactivo.
// ==============================================================================

export const THEME_KEY = 'smartbids_theme';

/**
 * Obtiene el tema almacenado en el navegador.
 * Por defecto retorna 'light' salvo que el usuario lo haya establecido explícitamente en 'dark'.
 */
export function getSavedTheme() {
    try {
        const saved = localStorage.getItem(THEME_KEY);
        if (saved === 'dark' || saved === 'light') {
            return saved;
        }
    } catch (e) {
        // En caso de modo incógnito o restricciones de storage
    }
    return 'light';
}

/**
 * Aplica el tema seleccionado a nivel global en el documento.
 * @param {'dark'|'light'} theme
 * @param {boolean} persist Si debe guardarse en el localStorage del navegador
 */
export function applyTheme(theme, persist = true) {
    const isDark = theme === 'dark';
    const root = document.documentElement;

    if (isDark) {
        root.classList.add('dark-mode');
        root.setAttribute('data-theme', 'dark');
    } else {
        root.classList.remove('dark-mode');
        root.setAttribute('data-theme', 'light');
    }

    if (persist) {
        try {
            localStorage.setItem(THEME_KEY, isDark ? 'dark' : 'light');
        } catch (e) {
            console.warn('SmartBids: No se pudo guardar la preferencia de tema en localStorage', e);
        }
    }

    // Actualizar todos los switches e indicadores visuales presentes en el DOM
    syncThemeControls(isDark);

    // Ajustar Chart.js si se encuentra cargado en la página (ej. Dashboard)
    updateChartJsTheme(isDark);

    // Disparar evento para otros componentes
    window.dispatchEvent(new CustomEvent('smartbids:themechange', {
        detail: { theme: isDark ? 'dark' : 'light', isDark }
    }));
}

/**
 * Alterna entre modo claro y modo oscuro.
 */
export function toggleTheme() {
    const currentTheme = document.documentElement.classList.contains('dark-mode') ? 'dark' : 'light';
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme, true);
    return nextTheme;
}

/**
 * Sincroniza el estado de los switches, textos y los íconos (luna / sol).
 * @param {boolean} isDark
 */
export function syncThemeControls(isDark) {
    // 1. Checkboxes
    const switches = document.querySelectorAll('#theme-dark-toggle, #theme-dark-toggle-tab, [data-theme-switch]');
    switches.forEach((sw) => {
        if (sw && sw.type === 'checkbox') {
            sw.checked = isDark;
        }
    });

    // 2. Textos de estado
    const statusLabels = document.querySelectorAll('#theme-toggle-status, #theme-toggle-status-tab, .theme-status-text');
    statusLabels.forEach((label) => {
        if (label) {
            label.textContent = isDark ? 'Activado' : 'Desactivado';
        }
    });

    // 3. Íconos
    const iconWraps = document.querySelectorAll('#theme-toggle-icon i, #theme-toggle-icon-tab i, .theme-icon-i');
    iconWraps.forEach((icon) => {
        if (icon) {
            if (isDark) {
                icon.className = 'fa-solid fa-sun';
            } else {
                icon.className = 'fa-solid fa-moon';
            }
        }
    });
}

/**
 * Ajusta los estilos de Chart.js si está presente en la vista.
 * @param {boolean} isDark
 */
function updateChartJsTheme(isDark) {
    if (typeof window.Chart !== 'undefined') {
        const textColor = isDark ? '#cbd5e1' : '#4a5568';
        const gridColor = isDark ? 'rgba(177, 210, 202, 0.12)' : 'rgba(0, 0, 0, 0.05)';

        if (window.Chart.defaults) {
            window.Chart.defaults.color = textColor;
            if (window.Chart.defaults.borderColor) {
                window.Chart.defaults.borderColor = gridColor;
            }
        }

        if (window.Chart.instances) {
            Object.values(window.Chart.instances).forEach((chart) => {
                if (chart && chart.options) {
                    if (chart.options.scales) {
                        Object.values(chart.options.scales).forEach((scale) => {
                            if (scale.ticks) scale.ticks.color = textColor;
                            if (scale.grid) scale.grid.color = gridColor;
                        });
                    }
                    if (chart.options.plugins?.legend?.labels) {
                        chart.options.plugins.legend.labels.color = textColor;
                    }
                    chart.update('none');
                }
            });
        }
    }
}

/**
 * Inicializa la escucha de eventos en los switches del DOM.
 */
export function setupThemeEvents() {
    const currentTheme = getSavedTheme();
    // Asegurar que las clases están aplicadas
    applyTheme(currentTheme, false);

    const switches = document.querySelectorAll('#theme-dark-toggle, #theme-dark-toggle-tab, [data-theme-switch]');
    switches.forEach((sw) => {
        if (sw && sw.dataset.themeBound !== 'true') {
            sw.dataset.themeBound = 'true';
            sw.checked = currentTheme === 'dark';
            sw.addEventListener('change', (e) => {
                applyTheme(e.target.checked ? 'dark' : 'light', true);
            });
        }
    });

    syncThemeControls(currentTheme === 'dark');
}

// Inicialización automática
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupThemeEvents, { once: true });
} else {
    setupThemeEvents();
}

window.SmartBidsTheme = {
    applyTheme,
    toggleTheme,
    getSavedTheme
};
