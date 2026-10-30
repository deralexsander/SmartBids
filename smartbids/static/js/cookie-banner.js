/**
 * SmartBids - Gestión del Banner Informativo de Cookies y Almacenamiento Local
 * Cumplimiento de la Ley N° 21.719 sobre Protección de Datos Personales de Chile.
 */

document.addEventListener('DOMContentLoaded', () => {
    const banner = document.getElementById('smartbids-cookie-banner');
    if (!banner) return;

    const STORAGE_KEY = 'smartbids_cookies_consent';
    const yaAceptado = localStorage.getItem(STORAGE_KEY);

    if (!yaAceptado) {
        // Mostrar con un leve retraso para suavizar la carga inicial
        setTimeout(() => {
            banner.style.display = 'block';
            banner.classList.add('cookie-banner--visible');
        }, 600);
    }

    const btnAccept = document.getElementById('btn-accept-cookies');
    if (btnAccept) {
        btnAccept.addEventListener('click', () => {
            localStorage.setItem(STORAGE_KEY, 'accepted');
            banner.classList.remove('cookie-banner--visible');
            banner.classList.add('cookie-banner--hidden');
            setTimeout(() => {
                banner.style.display = 'none';
            }, 350);
        });
    }
});
