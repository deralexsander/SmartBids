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
        contactFeedback.textContent = 'Enviando tu consulta...';
        contactFeedback.style.color = 'var(--gray-text)';

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
            contactFeedback.textContent = data.mensaje || 'Tu consulta fue enviada.';
            contactFeedback.style.color = 'var(--dark-green)';
        } catch (error) {
            contactFeedback.textContent = error.message || 'No se pudo enviar la consulta. Inténtalo nuevamente.';
            contactFeedback.style.color = '#c53030';
        } finally {
            contactSubmit.disabled = false;
            contactSubmit.innerHTML = originalButton;
            contactSubmit.removeAttribute('aria-busy');
        }
    });
}
