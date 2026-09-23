// ==========================================================================
// NAVEGACIÓN DE PESTAÑAS DEL PERFIL
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