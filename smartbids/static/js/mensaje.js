// ==========================================================================
// CATÁLOGO CENTRALIZADO DE MENSAJES DEL SISTEMA
// ==========================================================================
export const MENSAJES = {
    auth: {
        loginExitoso: 'Ingreso exitoso.',
        emailNoVerificado: 'Por favor verifica tu correo electrónico antes de ingresar.',
        registroExitoso: 'Registro exitoso. Se ha enviado un correo de verificación a tu email.',
        resetPasswordEnviado: 'Se ha enviado un correo para restablecer tu contraseña.',
        resetPasswordSinEmail: 'Ingresa tu correo en el campo superior para recuperar tu contraseña.',
        resetPasswordError: 'No se pudo enviar el correo de recuperación. Inténtalo más tarde.',
        logoutError: 'No se pudo cerrar la sesión.'
    },
    validacion: {
        camposRequeridos: 'Por favor, completa todos los campos requeridos.',
        emailsNoCoinciden: 'Los correos no coinciden.',
        passwordsNoCoinciden: 'Las contraseñas no coinciden.',
        emailInvalido: 'El formato del correo ingresado no es válido.',
        cuentaNoExiste: 'No existe una cuenta registrada con ese correo.'
    }
};

// ==========================================================================
// 1. TRADUCCIÓN DINÁMICA DE ERRORES DE FIREBASE
// ==========================================================================
export function getFriendlyErrorMessage(errorCode, rawMessage = '') {
    if (errorCode === 'auth/password-does-not-meet-requirements') {
        const missingReqs = [];

        if (rawMessage.includes('at least')) {
            const minMatch = rawMessage.match(/at least (\d+)/i);
            missingReqs.push(`al menos ${minMatch ? minMatch[1] : ''} caracteres`);
        }
        if (rawMessage.includes('at most')) {
            const maxMatch = rawMessage.match(/at most (\d+)/i);
            missingReqs.push(`máximo ${maxMatch ? maxMatch[1] : ''} caracteres`);
        }

        if (rawMessage.includes('upper case')) {
            missingReqs.push('al menos una letra mayúscula');
        }
        if (rawMessage.includes('lower case')) {
            missingReqs.push('al menos una letra minúscula');
        }

        if (rawMessage.includes('a numeric character')) {
            missingReqs.push('al menos un número');
        }

        if (rawMessage.includes('non-alphanumeric')) {
            missingReqs.push('al menos un carácter especial (ej: !@#$%^&*)');
        }

        if (missingReqs.length > 0) {
            return `La contraseña debe contener: ${missingReqs.join(', ')}.`;
        }

        return 'La contraseña no cumple con los requisitos configurados en el sistema.';
    }

    switch (errorCode) {
        case 'auth/invalid-credential':
        case 'auth/user-not-found':
        case 'auth/wrong-password':
            return 'Correo o contraseña incorrectos. Por favor, verifica tus datos.';
        case 'auth/invalid-email':
            return 'El formato del correo electrónico no es válido.';
        case 'auth/user-disabled':
            return 'Esta cuenta ha sido deshabilitada. Contacta al soporte.';
        case 'auth/too-many-requests':
            return 'Demasiados intentos fallidos. Por favor, reintenta más tarde o restablece tu contraseña.';
        case 'auth/network-request-failed':
            return 'Error de red. Verifica tu conexión a internet.';
        case 'auth/email-already-in-use':
            return 'Ese correo ya está registrado.';
        case 'auth/weak-password':
            return 'La contraseña ingresada es demasiado débil.';
        case 'auth/operation-not-allowed':
            return 'El método de correo/contraseña no está habilitado en Firebase Console.';
        default:
            return 'Ocurrió un error inesperado. Inténtalo nuevamente.';
    }
}

// ==========================================================================
// 2. CONTROL VISUAL Y DESPLIEGUE DEL MENSAJE (UI)
// ==========================================================================
let timerMensaje = null;

export function mostrarMensaje(texto, tipo = 'info') {
    const container = document.getElementById('global-message-container');
    const badge = document.getElementById('global-message-badge');
    const badgeText = document.getElementById('global-message-text');
    const icon = document.getElementById('global-message-icon');

    if (!container || !badgeText) return;

    if (timerMensaje) {
        clearTimeout(timerMensaje);
    }

    badgeText.textContent = texto;

    if (icon && badge) {
        icon.className = 'fa-solid';
        if (tipo === 'exito') {
            icon.classList.add('fa-circle-check');
            icon.style.color = 'var(--accent-green)';
            badgeText.style.color = 'var(--dark-green)';
            badge.style.borderColor = 'var(--accent-green)';
        } else if (tipo === 'error') {
            icon.classList.add('fa-circle-exclamation');
            icon.style.color = '#e53e3e';
            badgeText.style.color = '#c53030';
            badge.style.borderColor = '#feb2b2';
        } else {
            icon.classList.add('fa-circle-info');
            icon.style.color = 'var(--muted-teal)';
            badgeText.style.color = 'var(--dark-green)';
            badge.style.borderColor = 'var(--soft-mint)';
        }
    }

    container.style.visibility = 'visible';
    container.style.opacity = '1';
    container.style.transform = 'translate(-50%, 0)';

    timerMensaje = setTimeout(() => {
        limpiarMensaje();
    }, 5000);
}

// ==========================================================================
// 3. LIMPIEZA VISUAL DEL MENSAJE
// ==========================================================================
export function limpiarMensaje() {
    const container = document.getElementById('global-message-container');
    if (!container) return;

    container.style.opacity = '0';
    container.style.transform = 'translate(-50%, -25px)';
    container.style.visibility = 'hidden';
}

// ==========================================================================
// 4. CREACIÓN Y CONTROL DE ALERTAS DINÁMICAS (PILA APILADA CON COLA)
// ==========================================================================
const colaAlertas = [];
let timerAlertaFrontal = null;

export function renderizarAlerta(id, data) {
    const contenedor = document.getElementById('dynamic-alerts-container');
    if (!contenedor) return;

    const STORAGE_KEY = `smartbids_hide_alert_${id}`;

    // Si el usuario marcó no volver a mostrar, omitir
    if (localStorage.getItem(STORAGE_KEY) === 'true') {
        return;
    }

    // Evitar duplicados si ya está en la cola o en el DOM
    if (colaAlertas.some(item => item.id === id) || document.getElementById(`alert-box-${id}`)) {
        return;
    }

    // Crear el elemento de alerta
    const alertBox = document.createElement('div');
    alertBox.id = `alert-box-${id}`;
    
    const tipo = data.tipoAlerta || 'alerta';
    alertBox.className = `test-alert-container dynamic-alert tipo-${tipo}`;

    const icono = data.tipoAlerta === 'error' ? 'fa-circle-xmark' : 
                  data.tipoAlerta === 'exito' ? 'fa-circle-check' : 'fa-triangle-exclamation';

    alertBox.innerHTML = `
        <div class="test-alert-content">
            <i class="fa-solid ${icono} test-alert-icon"></i>
            <div class="test-alert-text">
                <h6>${data.asunto || 'Aviso'}</h6>
                <p>${data.cuerpo || ''}</p>
                <label class="test-alert-checkbox-label">
                    <input type="checkbox" class="check-dont-show">
                    <span>No volver a mostrar este mensaje</span>
                </label>
            </div>
            <button type="button" class="test-alert-close" aria-label="Cerrar aviso">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <div class="test-alert-progress-bar"></div>
    `;

    const closeBtn = alertBox.querySelector('.test-alert-close');
    const dontShowCheck = alertBox.querySelector('.check-dont-show');

    const cerrarEstaAlerta = () => {
        if (dontShowCheck && dontShowCheck.checked) {
            localStorage.setItem(STORAGE_KEY, 'true');
        }
        removerAlertaDeLaPila(id);
    };

    if (dontShowCheck) {
        dontShowCheck.addEventListener('change', () => {
            if (dontShowCheck.checked) {
                localStorage.setItem(STORAGE_KEY, 'true');
            } else {
                localStorage.removeItem(STORAGE_KEY);
            }
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', cerrarEstaAlerta);
    }

    contenedor.appendChild(alertBox);

    // Agregar a la lista de seguimiento
    colaAlertas.push({ id, elemento: alertBox, cerrarCallback: cerrarEstaAlerta });

    // Pequeño retardo de 50ms para permitir que el CSS anime la entrada con suavidad
    setTimeout(() => {
        actualizarPilaAlertas();
    }, 50);
}

function removerAlertaDeLaPila(id) {
    const index = colaAlertas.findIndex(item => item.id === id);
    if (index === -1) return;

    if (index === 0 && timerAlertaFrontal) {
        clearTimeout(timerAlertaFrontal);
        timerAlertaFrontal = null;
    }

    const { elemento } = colaAlertas[index];
    colaAlertas.splice(index, 1);

    // Animación suave de salida hacia arriba
    elemento.classList.remove('activa', 'pila-pos-0', 'pila-pos-1', 'pila-pos-2');
    elemento.classList.add('alerta-saliendo');

    setTimeout(() => {
        elemento.remove();
        actualizarPilaAlertas();
    }, 400);
}

function actualizarPilaAlertas() {
    if (timerAlertaFrontal) {
        clearTimeout(timerAlertaFrontal);
        timerAlertaFrontal = null;
    }

    colaAlertas.forEach((item, index) => {
        const el = item.elemento;

        // Limpiar clases previas de posición y estado activo
        el.classList.remove('pila-pos-0', 'pila-pos-1', 'pila-pos-2', 'pila-oculta', 'activa');

        if (index === 0) {
            // Tarjeta principal al frente
            el.classList.add('pila-pos-0', 'activa');
            timerAlertaFrontal = setTimeout(() => {
                item.cerrarCallback();
            }, 8000);
        } else if (index === 1) {
            // Segunda tarjeta
            el.classList.add('pila-pos-1');
        } else if (index === 2) {
            // Tercera tarjeta
            el.classList.add('pila-pos-2');
        } else {
            // En cola oculta
            el.classList.add('pila-oculta');
        }
    });
}



