// ==========================================================================
// CONTROLES VISUALES DE LICITACIONES
// ==========================================================================
export function toggleTextoLicitacion(idElemento, boton) {
    const contenedor = document.getElementById(idElemento);
    if (contenedor.classList.contains('licitacion-text-clamp')) {
        contenedor.classList.remove('licitacion-text-clamp');
        contenedor.classList.add('licitacion-text-expanded');
        boton.innerHTML = 'Ocultar <i class="fa-solid fa-chevron-up" style="font-size: 0.65rem;"></i>';
    } else {
        contenedor.classList.remove('licitacion-text-expanded');
        contenedor.classList.add('licitacion-text-clamp');
        boton.innerHTML = 'Ver <i class="fa-solid fa-chevron-down" style="font-size: 0.65rem;"></i>';
    }
}

function csrfToken() {
    const cookie = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='));
    return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : '';
}

function mostrarEstadoSeguimiento(mensaje, error = false) {
    const feedback = document.getElementById('seguimiento-feedback');
    if (!feedback) return;
    feedback.textContent = mensaje;
    feedback.hidden = false;
    feedback.style.color = error ? '#e53e3e' : 'var(--dark-green)';
    feedback.style.borderColor = error ? '#e53e3e' : 'var(--border-color)';
}

function actualizarBotonSeguimiento(form, activo) {
    const accion = form.querySelector('input[name="accion"]');
    const boton = form.querySelector('button[type="submit"]');
    const icono = form.querySelector('[data-seguimiento-icon]');
    const etiqueta = form.querySelector('[data-seguimiento-label]');
    if (!accion || !boton || !icono || !etiqueta) return;

    accion.value = activo ? 'dejar' : 'seguir';
    etiqueta.textContent = activo ? boton.dataset.dejarLabel : boton.dataset.seguirLabel;
    icono.classList.toggle('fa-solid', activo);
    icono.classList.toggle('fa-regular', !activo);
    boton.classList.remove('btn-primary', 'btn-outline');
    boton.classList.add(activo ? boton.dataset.siguiendoClass : boton.dataset.noSiguiendoClass);
}

async function actualizarSeguimiento(form) {
    const boton = form.querySelector('button[type="submit"]');
    if (!boton) return;
    boton.disabled = true;

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            credentials: 'same-origin',
            headers: {
                'Accept': 'application/json',
                'X-CSRFToken': csrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Error HTTP ${response.status} al actualizar seguimiento`);

        actualizarBotonSeguimiento(form, data.seguimiento_activo);
        const contador = document.getElementById('seguimientos-count');
        if (contador) contador.textContent = String(data.cantidad_seguidas);

        const tarjeta = form.closest('[data-licitacion-card]');
        const lista = document.getElementById('licitaciones-list');
        if (!data.seguimiento_activo && tarjeta && lista?.dataset.soloSeguidas === 'true') {
            tarjeta.remove();
            if (!lista.querySelector('[data-licitacion-card]')) {
                const vacio = document.createElement('div');
                vacio.className = 'dashboard-card';
                vacio.dataset.seguimientosEmpty = '';
                vacio.style.cssText = 'text-align:center;padding:3rem;color:var(--muted-teal);';
                vacio.textContent = 'Ya no sigues licitaciones en esta página.';
                lista.append(vacio);
            }
        }
        mostrarEstadoSeguimiento(
            data.seguimiento_activo ? 'Licitación agregada a tus seguidas.' : 'Licitación eliminada de tus seguidas.',
        );
    } catch (error) {
        console.error(error);
        mostrarEstadoSeguimiento(error.message || 'No se pudo actualizar el seguimiento. Intenta nuevamente.', true);
    } finally {
        boton.disabled = false;
    }
}

function iniciarSeguimientoAsincrono() {
    document.addEventListener('submit', (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.matches('[data-seguimiento-form]')) return;
        event.preventDefault();
        actualizarSeguimiento(form);
    });
}

function iniciarNotificacionesLicitacion() {
    const toggle = document.getElementById('licitacion-notifications-toggle');
    const panel = document.getElementById('licitacion-notifications-panel');
    const lista = document.getElementById('licitacion-notifications-list');
    const contador = document.getElementById('licitacion-notifications-count');
    if (!toggle || !panel || !lista || !contador) return;

    panel.hidden = true;
    panel.style.display = 'none';

    const endpoint = toggle.dataset.endpoint;
    const mostrarError = () => {
        lista.replaceChildren();
        const error = document.createElement('p');
        error.textContent = 'No se pudieron cargar las notificaciones. Intenta nuevamente.';
        error.style.color = '#b91c1c';
        lista.append(error);
    };

    const cargar = async () => {
        const response = await fetch(endpoint, { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Error HTTP ${response.status} al consultar notificaciones`);
        const data = await response.json();
        contador.textContent = data.count > 99 ? '99+' : String(data.count);
        contador.hidden = data.count === 0;
        lista.replaceChildren();
        if (!data.notifications.length) {
            const vacio = document.createElement('p');
            vacio.textContent = 'No tienes novedades de tus licitaciones seguidas.';
            vacio.style.color = 'var(--gray-text)';
            lista.append(vacio);
        }
        data.notifications.forEach((notification) => {
            const item = document.createElement('a');
            item.href = notification.url;
            item.style.cssText = 'display:block;padding:.7rem 0;border-top:1px solid var(--border-color);color:var(--dark-green);text-decoration:none;';
            const mensaje = document.createElement('span');
            mensaje.textContent = notification.message;
            const fecha = document.createElement('small');
            fecha.textContent = notification.created_at;
            fecha.style.cssText = 'display:block;color:var(--gray-text);margin-top:.25rem;';
            item.append(mensaje, fecha);
            item.addEventListener('click', async (event) => {
                event.preventDefault();
                try {
                    const markRead = await fetch(endpoint, {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': csrfToken() },
                    });
                    if (!markRead.ok) throw new Error(`Error HTTP ${markRead.status} al marcar notificaciones`);
                    window.location.assign(item.href);
                } catch (error) {
                    console.error(error);
                    mostrarError();
                }
            });
            lista.append(item);
        });
    };

    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        const isHidden = panel.hidden || panel.style.display === 'none';
        panel.hidden = !isHidden;
        panel.style.display = isHidden ? 'block' : 'none';
        panel.classList.toggle('is-open', isHidden);
        toggle.setAttribute('aria-expanded', String(isHidden));
    });

    document.addEventListener('click', (e) => {
        if (!panel.contains(e.target) && !toggle.contains(e.target)) {
            panel.hidden = true;
            panel.style.display = 'none';
            panel.classList.remove('is-open');
            toggle.setAttribute('aria-expanded', 'false');
        }
    });
    cargar().catch((error) => {
        console.error(error);
        mostrarError();
    });
    window.setInterval(() => {
        cargar().catch((error) => {
            console.error(error);
            contador.title = 'Error al actualizar notificaciones';
        });
    }, 60000);
}

function iniciarFiltrosDetalleLicitacion() {
    const configurarFiltro = (inputId, itemSelector) => {
        const input = document.getElementById(inputId);
        if (!input) return;

        input.addEventListener('input', () => {
            const term = input.value.trim().toLowerCase();
            const items = document.querySelectorAll(itemSelector);

            items.forEach((item) => {
                const text = (item.dataset.searchText || item.textContent || '').toLowerCase();
                const match = !term || text.includes(term);
                item.style.display = match ? '' : 'none';
            });
        });
    };

    configurarFiltro('filtro-documentos', '[data-doc-item]');
    configurarFiltro('filtro-preguntas', '[data-qa-item]');
}

document.addEventListener('DOMContentLoaded', () => {
    iniciarSeguimientoAsincrono();
    iniciarNotificacionesLicitacion();
    iniciarFiltrosDetalleLicitacion();
});