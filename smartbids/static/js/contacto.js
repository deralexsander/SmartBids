import { mostrarMensaje } from './mensaje.js';

const contactForm = document.getElementById('contact-form');
const contactFeedback = document.getElementById('contact-feedback');
const contactSubmit = document.getElementById('contact-submit');

const nameInput = document.getElementById('contact-name');
const emailInput = document.getElementById('contact-email');
const phoneInput = document.getElementById('contact-phone');
const topicInput = document.getElementById('contact-topic');
const planItem = document.getElementById('contact-plan-item');
const planSelect = document.getElementById('contact-plan');
const companyItem = document.getElementById('contact-company-item');
const companyInput = document.getElementById('contact-company');
const messageInput = document.getElementById('contact-message');

function actualizarCamposSuscripcion() {
    const topicVal = (topicInput?.value || '').toLowerCase();
    const esSuscripcion = topicVal.includes('suscriptor') || topicVal.includes('suscripci');
    if (planItem) planItem.style.display = esSuscripcion ? 'block' : 'none';
    if (companyItem) companyItem.style.display = esSuscripcion ? 'block' : 'none';
    return esSuscripcion;
}

if (topicInput) {
    topicInput.addEventListener('change', actualizarCamposSuscripcion);
}

export function seleccionarPlanYDesplazar(planValor) {
    if (topicInput) {
        topicInput.value = 'Solicitud de suscripción';
        actualizarCamposSuscripcion();
    }
    if (planSelect && planValor) {
        planSelect.value = planValor;
    }
    const contactoSection = document.getElementById('contacto');
    if (contactoSection) {
        contactoSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    if (phoneInput && !phoneInput.value) {
        phoneInput.focus();
    } else if (companyInput && !companyInput.value) {
        companyInput.focus();
    }
}

// Botones rápidos en las tarjetas de planes en Home
const btnHomeMensual = document.getElementById('btn-home-plan-mensual');
const btnHomeAnual = document.getElementById('btn-home-plan-anual');

btnHomeMensual?.addEventListener('click', () => {
    seleccionarPlanYDesplazar('Plan Mensual ($20.000 CLP)');
});

btnHomeAnual?.addEventListener('click', () => {
    seleccionarPlanYDesplazar('Plan Anual ($200.000 CLP)');
});

// Autocompletar datos si el usuario tiene sesión activa (pero permitiendo editarlos)
async function autocompletarDatosUsuario() {
    const uid = localStorage.getItem('smartbids_uid');
    if (!uid) return;

    try {
        const response = await fetch('/api/obtener-perfil/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid })
        });
        const resData = await response.json();
        if (resData?.status === 'ok' && resData.datos) {
            const d = resData.datos;
            if (nameInput && !nameInput.value) {
                const nombreCompleto = `${d.sus_nombre1 || ''} ${d.sus_apellido1 || ''}`.trim();
                if (nombreCompleto) nameInput.value = nombreCompleto;
            }
            if (emailInput && !emailInput.value) {
                if (d.sus_correo_institucional) emailInput.value = d.sus_correo_institucional;
            }
            if (phoneInput && !phoneInput.value) {
                if (d.empresa?.emp_contacto_telefono) phoneInput.value = d.empresa.emp_contacto_telefono;
            }
            if (companyInput && !companyInput.value) {
                const nombreEmpresa = d.empresa?.emp_fantasia || d.empresa?.emp_razon_social || '';
                if (nombreEmpresa) companyInput.value = nombreEmpresa;
            }
        }
    } catch (_) {
        // Silencioso si falla la consulta previa
    }
}

// Detectar parámetros URL (?plan=mensual o ?plan=anual o #contacto?plan=...)
function procesarParametrosUrl() {
    const searchParams = new URLSearchParams(window.location.search);
    let planParam = searchParams.get('plan');

    if (!planParam && window.location.hash.includes('plan=')) {
        const hashQuery = window.location.hash.split('?')[1];
        if (hashQuery) {
            const hashParams = new URLSearchParams(hashQuery);
            planParam = hashParams.get('plan');
        }
    }

    if (planParam) {
        const planParamLower = planParam.toLowerCase();
        if (planParamLower.includes('anual')) {
            seleccionarPlanYDesplazar('Plan Anual ($200.000 CLP)');
        } else if (planParamLower.includes('mensual')) {
            seleccionarPlanYDesplazar('Plan Mensual ($20.000 CLP)');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    actualizarCamposSuscripcion();
    autocompletarDatosUsuario();
    procesarParametrosUrl();
});

if (contactForm && contactSubmit) {
    contactForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const name = (nameInput?.value || '').trim();
        const email = (emailInput?.value || '').trim();
        const phone = (phoneInput?.value || '').trim();
        const topic = (topicInput?.value || '').trim();
        const company = (companyInput?.value || '').trim();
        const plan = planSelect?.value || 'Plan Mensual ($20.000 CLP)';
        const esSuscripcion = actualizarCamposSuscripcion();
        let message = (messageInput?.value || '').trim();

        if (!name) {
            mostrarMensaje('Por favor completa el campo: Nombre.', 'error');
            nameInput?.focus();
            return;
        }

        if (name.length > 100) {
            mostrarMensaje('El nombre no puede superar los 100 caracteres.', 'error');
            nameInput?.focus();
            return;
        }

        if (!email) {
            mostrarMensaje('Por favor completa el campo: Correo.', 'error');
            emailInput?.focus();
            return;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email) || email.length > 254) {
            mostrarMensaje('Por favor ingresa un correo electrónico válido.', 'error');
            emailInput?.focus();
            return;
        }

        if (!phone) {
            mostrarMensaje('Por favor completa el campo: Teléfono.', 'error');
            phoneInput?.focus();
            return;
        }

        if (phone.length > 20 || !/^[+0-9() .-]+$/.test(phone)) {
            mostrarMensaje('Por favor ingresa un teléfono válido (máx. 20 caracteres).', 'error');
            phoneInput?.focus();
            return;
        }

        if (!topic) {
            mostrarMensaje('Por favor selecciona una opción para: Tema.', 'error');
            topicInput?.focus();
            return;
        }

        if (esSuscripcion) {
            if (!company) {
                mostrarMensaje('Por favor ingresa el Nombre de la Empresa para la suscripción.', 'error');
                companyInput?.focus();
                return;
            }
            if (company.length > 150) {
                mostrarMensaje('El nombre de la empresa no puede superar los 150 caracteres.', 'error');
                companyInput?.focus();
                return;
            }
            if (!message) {
                message = `Solicitud de suscripción para el plan ${plan} de la empresa ${company}.`;
            }
        }

        if (!message) {
            mostrarMensaje('Por favor completa el campo: ¿Cómo podemos ayudarte?.', 'error');
            messageInput?.focus();
            return;
        }

        if (message.length < 20) {
            mostrarMensaje('Tu mensaje debe tener al menos 20 caracteres.', 'error');
            messageInput?.focus();
            return;
        }

        if (message.length > 3000) {
            mostrarMensaje('Tu mensaje no puede superar los 3000 caracteres.', 'error');
            messageInput?.focus();
            return;
        }

        const csrfToken = contactForm.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
        const payload = {
            name,
            email,
            phone,
            topic,
            message,
            ...(esSuscripcion ? {
                tipo: 'suscripcion',
                company,
                plan
            } : {})
        };

        const originalButton = contactSubmit.innerHTML;
        contactSubmit.disabled = true;
        contactSubmit.textContent = 'Enviando...';
        contactSubmit.setAttribute('aria-busy', 'true');
        if (contactFeedback) {
            contactFeedback.textContent = 'Enviando tu consulta...';
            contactFeedback.style.color = 'var(--gray-text)';
        }

        try {
            const response = await fetch('/api/contacto/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (!response.ok || data.status !== 'ok') {
                throw new Error(data.mensaje || 'No se pudo enviar la consulta.');
            }

            contactForm.reset();
            actualizarCamposSuscripcion();

            const msgExito = data.mensaje || (esSuscripcion
                ? '¡Solicitud de suscripción recibida con éxito! Nuestro equipo comercial se comunicará contigo para coordinar la activación tras confirmar el pago.'
                : '¡Tu consulta fue enviada con éxito! Nos pondremos en contacto contigo a la brevedad.');

            if (contactFeedback) {
                contactFeedback.textContent = msgExito;
                contactFeedback.style.color = 'var(--dark-green)';
            }
            mostrarMensaje(msgExito, 'exito', 16000);
        } catch (error) {
            const msgError = error.message || 'No se pudo enviar la consulta. Inténtalo nuevamente.';
            if (contactFeedback) {
                contactFeedback.textContent = msgError;
                contactFeedback.style.color = '#c53030';
            }
            mostrarMensaje(msgError, 'error');
        } finally {
            contactSubmit.disabled = false;
            contactSubmit.innerHTML = originalButton;
            contactSubmit.removeAttribute('aria-busy');
        }
    });
}
