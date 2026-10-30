import { mostrarMensaje } from './mensaje.js';

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
    if (feedback) {
        feedback.textContent = mensaje;
        feedback.hidden = false;
        feedback.classList.toggle('feedback--error', error);
        feedback.classList.toggle('feedback--success', !error);
        if (error) {
            feedback.style.color = '#e53e3e';
            feedback.style.borderColor = '#e53e3e';
        } else {
            feedback.style.color = '';
            feedback.style.borderColor = '';
        }
    }
    mostrarMensaje(mensaje, error ? 'error' : 'exito');
}

function actualizarBotonSeguimiento(form, activo) {
    const accion = form.querySelector('input[name="accion"]');
    const boton = form.querySelector('button[type="submit"]');
    const icono = form.querySelector('[data-seguimiento-icon]');
    const etiqueta = form.querySelector('[data-seguimiento-label]');
    if (!accion || !boton) return;

    accion.value = activo ? 'dejar' : 'seguir';
    if (etiqueta) {
        etiqueta.textContent = activo ? (boton.dataset.dejarLabel || 'Dejar de seguir') : (boton.dataset.seguirLabel || 'Seguir');
    }
    if (icono) {
        // Remover spinner y aplicar ícono bookmark con estilo relleno (solid) o contorno (regular)
        icono.className = `${activo ? 'fa-solid' : 'fa-regular'} fa-bookmark`;
    }
    if (boton.dataset.siguiendoClass && boton.dataset.noSiguiendoClass) {
        boton.classList.remove('btn-primary', 'btn-outline');
        boton.classList.add(activo ? boton.dataset.siguiendoClass : boton.dataset.noSiguiendoClass);
    }
}

async function actualizarSeguimiento(form) {
    const boton = form.querySelector('button[type="submit"]');
    if (!boton) return;
    const icono = form.querySelector('[data-seguimiento-icon]');
    const etiqueta = form.querySelector('[data-seguimiento-label]');
    const accion = form.querySelector('input[name="accion"]')?.value;
    const actionUrl = form.getAttribute('action') || form.action;

    boton.disabled = true;
    boton.style.pointerEvents = 'none';
    boton.style.opacity = '0.85';
    if (icono) icono.className = 'fa-solid fa-circle-notch fa-spin';
    if (etiqueta) etiqueta.textContent = accion === 'dejar' ? 'Dejando de seguir...' : 'Siguiendo...';

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

        // Sincronizar todos los botones de esta licitación en la página
        document.querySelectorAll(`form[data-seguimiento-form][action="${actionUrl}"]`).forEach(f => {
            actualizarBotonSeguimiento(f, data.seguimiento_activo);
        });

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
        const accionActual = form.querySelector('input[name="accion"]')?.value;
        document.querySelectorAll(`form[data-seguimiento-form][action="${actionUrl}"]`).forEach(f => {
            actualizarBotonSeguimiento(f, accionActual === 'dejar');
        });
    } finally {
        document.querySelectorAll(`form[data-seguimiento-form][action="${actionUrl}"]`).forEach(f => {
            const btn = f.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = false;
                btn.style.pointerEvents = 'auto';
                btn.style.opacity = '1';
            }
        });
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

function iniciarCargaVerFicha() {
    document.addEventListener('click', (event) => {
        const link = event.target.closest('.mis-lic__detail-link, a[data-ver-ficha]');
        if (!link || link.dataset.loading === 'true') return;
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.button !== 0 || link.target === '_blank') return;
        if (link.closest('.mis-lic__pagination') || link.closest('.mis-lic__filter-link')) return;

        link.dataset.loading = 'true';
        link.style.pointerEvents = 'none';
        link.style.opacity = '0.85';
        link.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin me-1"></i> Cargando...';
    });
}

function iniciarToggleMatchCards() {
    const btn = document.getElementById('btn-toggle-match-cards');
    if (!btn) return;
    let expandido = false;
    btn.addEventListener('click', () => {
        expandido = !expandido;
        const extras = document.querySelectorAll('.mis-lic__card--match-extra');
        extras.forEach(card => {
            card.style.display = expandido ? 'block' : 'none';
        });
        const totalExtras = extras.length;
        if (expandido) {
            btn.innerHTML = '<i class="fa-solid fa-chevron-up me-1"></i> Mostrar menos';
        } else {
            btn.innerHTML = `<i class="fa-solid fa-chevron-down me-1"></i> Mostrar ${totalExtras} más con match`;
            document.getElementById('seccion-match-perfil')?.scrollIntoView({ behavior: 'smooth' });
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    iniciarSeguimientoAsincrono();
    iniciarNotificacionesLicitacion();
    iniciarFiltrosDetalleLicitacion();
    iniciarCargaVerFicha();
    iniciarToggleMatchCards();
});