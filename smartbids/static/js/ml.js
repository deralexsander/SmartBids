function initSimuladorModal() {
    const modal = document.getElementById('modal-simulador-ml');
    const openBtn = document.getElementById('btn-abrir-modal-simulador');
    const closeBtn = document.getElementById('btn-cerrar-modal-simulador');
    const cancelBtn = document.getElementById('btn-cancelar-modal-simulador');

    if (!modal) return;

    const form = modal.querySelector('#form-simulador-ml');
    form?.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!form.hasAttribute('action')) return;
        let feedback = form.querySelector('[data-simulador-feedback]');
        if (!feedback) {
            feedback = document.createElement('p');
            feedback.dataset.simuladorFeedback = '';
            feedback.setAttribute('role', 'status');
            form.append(feedback);
        }
        const submit = form.querySelector('[type="submit"]');
        submit.disabled = true;
        form.setAttribute('aria-busy', 'true');
        feedback.textContent = 'Evaluando escenario…';
        const result = modal.querySelector('.simulador-modal__result');
        const score = result.querySelector('.simulador-modal__score');
        score.textContent = '—';
        score.classList.add('simulador-modal__score--empty');
        result.querySelector('.simulador-modal__status').textContent = 'Sin evaluación';
        result.querySelector('p').textContent = 'Evaluando los valores ingresados.';
        result.querySelectorAll('dd').forEach(el => { el.textContent = '—'; });
        try {
            const response = await fetch(form.action, {
                method: 'POST', body: new FormData(form), credentials: 'same-origin',
                headers: { 'Accept': 'application/json' },
            });
            const data = await response.json();
            if (!response.ok) {
                feedback.textContent = data.errors
                    ? Object.entries(data.errors).map(([name, errors]) => {
                        const label = form.querySelector(`label[for="id_${name}"]`);
                        return `${label?.textContent || name}: ${errors.map(e => e.message).join(' ')}`;
                    }).join(' ')
                    : data.error || 'No se pudo evaluar el escenario.';
                result.querySelector('p').textContent = 'Corrige el formulario o intenta nuevamente.';
                return;
            }
            const prediction = data.resultado;
            score.textContent = `${prediction.puntuacion}%`;
            score.classList.remove('simulador-modal__score--empty');
            result.querySelector('.simulador-modal__status').textContent = prediction.etiqueta;
            result.querySelector('p').textContent = 'Clasificación para los valores ingresados.';
            const metrics = result.querySelectorAll('dd');
            metrics[0].textContent = prediction.etiqueta;
            metrics[1].textContent = `${prediction.puntuacion}%`;
            metrics[2].textContent = `${prediction.umbral}%`;
            feedback.textContent = 'Evaluación completada.';
        } catch {
            feedback.textContent = 'No se pudo evaluar el escenario. Intenta nuevamente.';
            result.querySelector('p').textContent = 'No se pudo obtener un resultado.';
        } finally {
            submit.disabled = false;
            form.removeAttribute('aria-busy');
        }
    });

    let previousFocus = null;
    let previousOverflow = '';

    function abrir() {
        if (!modal.hidden) return;
        previousFocus = document.activeElement;
        previousOverflow = document.body.style.overflow;
        modal.hidden = false;
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        closeBtn?.focus();
    }

    function cerrar() {
        modal.classList.remove('active');
        modal.hidden = true;
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = previousOverflow;

        if (previousFocus && previousFocus.isConnected) {
            previousFocus.focus();
        }
    }

    // Abrir modal
    openBtn?.addEventListener('click', abrir);

    // Cerrar modal
    closeBtn?.addEventListener('click', cerrar);
    cancelBtn?.addEventListener('click', cerrar);

    // Cerrar al hacer clic fuera del contenido
    modal.addEventListener('click', (event) => {
        if (event.target === modal) {
            cerrar();
        }
    });

    // Manejo del teclado
    document.addEventListener('keydown', (event) => {
        if (modal.hidden) return;

        if (event.key === 'Escape') {
            cerrar();
            return;
        }

        if (event.key === 'Tab') {
            const focusables = Array.from(
                modal.querySelectorAll(
                    'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href]'
                )
            ).filter(el => el.getClientRects().length > 0);

            const first = focusables[0];
            const last = focusables[focusables.length - 1];

            if (!first || !last) return;

            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });

    // Reabrir después de una predicción o error en Django
    const reabrirTrasPost = modal.dataset.reabrir === 'true';

    if (reabrirTrasPost) {
        abrir();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSimuladorModal, { once: true });
} else {
    initSimuladorModal();
}
