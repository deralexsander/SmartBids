import { mostrarMensaje } from './mensaje.js';

const contactForm = document.getElementById('contact-form');
const contactFeedback = document.getElementById('contact-feedback');
const contactSubmit = document.getElementById('contact-submit');

if (contactForm && contactSubmit) {
    contactForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!contactForm.reportValidity()) return;

        const csrfToken = contactForm.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
        const payload = Object.fromEntries(new FormData(contactForm).entries());
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
            const msgExito = data.mensaje || '¡Tu consulta fue enviada con éxito! Nos pondremos en contacto contigo.';
            if (contactFeedback) {
                contactFeedback.textContent = msgExito;
                contactFeedback.style.color = 'var(--dark-green)';
            }
            mostrarMensaje(msgExito, 'exito');
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
