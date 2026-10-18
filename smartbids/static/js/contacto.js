import { mostrarMensaje } from './mensaje.js';

const contactForm = document.getElementById('contact-form');
const contactFeedback = document.getElementById('contact-feedback');
const contactSubmit = document.getElementById('contact-submit');

if (contactForm && contactSubmit) {
    contactForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const nameInput = document.getElementById('contact-name');
        const emailInput = document.getElementById('contact-email');
        const phoneInput = document.getElementById('contact-phone');
        const topicInput = document.getElementById('contact-topic');
        const messageInput = document.getElementById('contact-message');

        const name = (nameInput?.value || '').trim();
        const email = (emailInput?.value || '').trim();
        const phone = (phoneInput?.value || '').trim();
        const topic = (topicInput?.value || '').trim();
        const message = (messageInput?.value || '').trim();

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

        if (phone && (phone.length > 20 || !/^[+0-9() .-]+$/.test(phone))) {
            mostrarMensaje('Por favor ingresa un teléfono válido (máx. 20 caracteres).', 'error');
            phoneInput?.focus();
            return;
        }

        if (!topic) {
            mostrarMensaje('Por favor selecciona una opción para: Tema.', 'error');
            topicInput?.focus();
            return;
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
