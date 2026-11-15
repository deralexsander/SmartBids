/**
 * SmartBids - Validador Dinámico y Medidor de Fuerza de Contraseñas
 * Se adapta automáticamente y en tiempo real a la Política de Contraseñas
 * configurada por el administrador en Identity Platform / Firebase.
 * No retiene caché estático en cookies ni en sessionStorage.
 */

// Limpieza de cualquier almacenamiento residual de sesiones previas
try {
    sessionStorage.removeItem('sb_active_password_policy');
    localStorage.removeItem('sb_active_password_policy');
} catch (_) {}

// Estado global de la política activa en memoria
export let currentPolicy = {
    status: 'ok',
    enforcementState: 'ENFORCE',
    minPasswordLength: 6,
    maxPasswordLength: 4096,
    containsUppercaseCharacter: true,
    containsLowercaseCharacter: true,
    containsNumericCharacter: true,
    containsNonAlphanumericCharacter: true
};

// Registro de medidores activos en la página
const medidoresActivos = new Set();
let peticionPoliticaEnCurso = null;

/**
 * Obtiene la lista de requisitos activos según la política configurada.
 * Si un criterio está desactivado por el administrador, no se exigirá ni se mostrará.
 */
export function obtenerRequisitosDesdePolitica(policy = currentPolicy) {
    const rules = [];
    const isEnforced = (policy.enforcementState || 'ENFORCE') === 'ENFORCE';
    const minLen = Math.max(6, Number(policy.minPasswordLength) || 6);
    const maxLen = Number(policy.maxPasswordLength) || 4096;

    // 1. Longitud mínima (siempre activa)
    rules.push({
        id: 'length',
        label: `Mínimo ${minLen} caracteres`,
        test: (pwd) => pwd.length >= minLen
    });

    // 2. Longitud máxima (si está configurada y no es el valor por defecto 4096)
    if (maxLen && maxLen < 4096) {
        rules.push({
            id: 'max-length',
            label: `Máximo ${maxLen} caracteres`,
            test: (pwd) => pwd.length > 0 && pwd.length <= maxLen
        });
    }

    // 3. Requisitos de caracteres si el modo forzoso está activo
    if (isEnforced) {
        if (policy.containsUppercaseCharacter) {
            rules.push({
                id: 'uppercase',
                label: 'Al menos una letra mayúscula',
                test: (pwd) => /[A-Z]/.test(pwd)
            });
        }

        if (policy.containsLowercaseCharacter) {
            rules.push({
                id: 'lowercase',
                label: 'Al menos una letra minúscula',
                test: (pwd) => /[a-z]/.test(pwd)
            });
        }

        if (policy.containsNumericCharacter) {
            rules.push({
                id: 'numeric',
                label: 'Al menos un número',
                test: (pwd) => /[0-9]/.test(pwd)
            });
        }

        if (policy.containsNonAlphanumericCharacter) {
            rules.push({
                id: 'special',
                label: 'Al menos un carácter especial (ej: !@#$%^&*)',
                test: (pwd) => /[^A-Za-z0-9]/.test(pwd)
            });
        }
    }

    return rules;
}

/**
 * Evalúa la contraseña contra los requisitos activos y calcula el porcentaje.
 */
export function evaluarFuerzaPassword(password = '', policy = currentPolicy) {
    const pwd = String(password || '');
    const rules = obtenerRequisitosDesdePolitica(policy);

    const maxLen = Number(policy.maxPasswordLength) || 4096;
    const excedeMaximo = maxLen < 4096 && pwd.length > maxLen;

    const resultados = rules.map(req => {
        let cumple = false;
        if (pwd.length > 0) {
            cumple = req.test(pwd);
        }
        return {
            id: req.id,
            label: req.label,
            cumple
        };
    });

    const cumplidos = resultados.filter(r => r.cumple).length;
    const total = Math.max(1, resultados.length);
    const esValida = pwd.length > 0 && cumplidos === total && !excedeMaximo;
    const porcentaje = pwd.length === 0 ? 0 : Math.round((cumplidos / total) * 100);

    let nivel = 'vacio';
    let textoNivel = 'Seguridad de la contraseña';
    let color = '#cbd5e1';

    if (pwd.length === 0) {
        nivel = 'vacio';
        textoNivel = 'Seguridad de la contraseña';
        color = '#cbd5e1';
    } else if (excedeMaximo) {
        nivel = 'excedido';
        textoNivel = `Supera el máximo permitido (${maxLen} caracteres)`;
        color = '#ef4444'; // Rojo por exceder límite
    } else if (esValida) {
        nivel = 'fuerte';
        textoNivel = 'Fuerte (Requisitos completos)';
        color = '#10b981'; // Verde esmeralda
    } else {
        const ratio = cumplidos / total;
        if (ratio <= 0.25) {
            nivel = 'muy-debil';
            textoNivel = 'Muy débil';
            color = '#ef4444';
        } else if (ratio <= 0.5) {
            nivel = 'debil';
            textoNivel = 'Débil';
            color = '#f97316';
        } else if (ratio <= 0.75) {
            nivel = 'media';
            textoNivel = 'Media';
            color = '#eab308';
        } else {
            nivel = 'buena';
            textoNivel = 'Buena';
            color = '#84cc16';
        }
    }

    return {
        resultados,
        cumplidos,
        total,
        porcentaje,
        esValida,
        excedeMaximo,
        maxLen,
        nivel,
        textoNivel,
        color,
        rules
    };
}

/**
 * Consulta la política activa desde la API pública en tiempo real.
 * Usa cache: 'no-store' y timestamp dinámico para evitar caché de navegador/cookies.
 */
export async function cargarPoliticaContrasenas() {
    if (peticionPoliticaEnCurso) {
        return peticionPoliticaEnCurso;
    }

    peticionPoliticaEnCurso = (async () => {
        try {
            const timestamp = Date.now();
            const res = await fetch(`/api/politica-contrasenas-publica/?_t=${timestamp}`, {
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            });

            if (res.ok) {
                const data = await res.json();
                if (data && data.status === 'ok') {
                    Object.assign(currentPolicy, data);
                }
            }
        } catch (err) {
            console.warn('[SmartBids] No se pudo cargar la política dinámica de contraseñas:', err);
        } finally {
            peticionPoliticaEnCurso = null;
        }
        return currentPolicy;
    })();

    return peticionPoliticaEnCurso;
}

/**
 * Renderiza la lista de requisitos en el DOM según la política activa.
 */
function renderizarListaRequisitos(container, rules) {
    const list = container.querySelector('.password-meter__list');
    if (!list) return;

    list.innerHTML = rules.map(rule => `
        <li class="password-meter__item" data-criterion="${rule.id}">
            <i class="fa-regular fa-circle password-meter__icon"></i>
            <span>${rule.label}</span>
        </li>
    `).join('');
}

/**
 * Conecta un campo de contraseña a su medidor visual en el DOM.
 */
export function conectarMedidorPassword(inputElementOrId, containerElementOrId) {
    const input = typeof inputElementOrId === 'string'
        ? document.getElementById(inputElementOrId)
        : inputElementOrId;

    const container = typeof containerElementOrId === 'string'
        ? document.getElementById(containerElementOrId)
        : containerElementOrId;

    if (!input || !container) return null;

    if (input.dataset.meterBound === 'true') {
        const existente = Array.from(medidoresActivos).find(m => m.input === input);
        if (existente) return existente;
    }
    input.dataset.meterBound = 'true';

    const barFill = container.querySelector('.password-meter__bar');
    const statusText = container.querySelector('.password-meter__status');

    function actualizar() {
        const evaluacion = evaluarFuerzaPassword(input.value, currentPolicy);

        if (barFill) {
            barFill.style.width = `${evaluacion.porcentaje}%`;
            barFill.style.backgroundColor = evaluacion.color;
        }

        if (statusText) {
            statusText.textContent = evaluacion.textoNivel;
            statusText.style.color = evaluacion.nivel === 'vacio' ? '' : evaluacion.color;
        }

        const items = container.querySelectorAll('.password-meter__item');
        items.forEach(item => {
            const ruleId = item.dataset.criterion || item.dataset.rule;
            const res = evaluacion.resultados.find(r => r.id === ruleId);
            const icon = item.querySelector('.password-meter__icon');

            if (res && res.cumple) {
                item.classList.add('is-valid');
                item.classList.remove('is-exceeded');
                if (icon) {
                    icon.className = 'fa-solid fa-circle-check password-meter__icon';
                }
            } else if (ruleId === 'max-length' && evaluacion.excedeMaximo) {
                item.classList.remove('is-valid');
                item.classList.add('is-exceeded');
                if (icon) {
                    icon.className = 'fa-solid fa-circle-xmark password-meter__icon';
                }
            } else {
                item.classList.remove('is-valid');
                item.classList.remove('is-exceeded');
                if (icon) {
                    icon.className = 'fa-regular fa-circle password-meter__icon';
                }
            }
        });

        return evaluacion;
    }

    function reconfigurar() {
        const rules = obtenerRequisitosDesdePolitica(currentPolicy);
        renderizarListaRequisitos(container, rules);
        actualizar();
    }

    input.addEventListener('input', actualizar);
    input.addEventListener('focus', () => {
        container.classList.add('is-focused');
        // Al hacer focus, verifica en vivo si la política fue modificada por el admin
        cargarPoliticaContrasenas().then(() => {
            reconfigurar();
        });
    });
    input.addEventListener('blur', () => {
        container.classList.remove('is-focused');
    });

    const instancia = {
        input,
        container,
        actualizar,
        reconfigurar,
        obtenerEvaluacion: () => evaluarFuerzaPassword(input.value, currentPolicy)
    };

    medidoresActivos.add(instancia);

    // Cargar política remota y reconfigurar de inmediato
    cargarPoliticaContrasenas().then(policy => {
        const rules = obtenerRequisitosDesdePolitica(policy);
        renderizarListaRequisitos(container, rules);
        actualizar();
    });

    // Render inicial
    reconfigurar();

    return instancia;
}

/**
 * Refresca todos los medidores conectados en la página ante un cambio de política.
 */
export function refrescarTodosLosMedidores() {
    medidoresActivos.forEach(m => {
        if (typeof m.reconfigurar === 'function') {
            m.reconfigurar();
        }
    });
}

// Sincronización en tiempo real sin requerir recargar ni limpiar cookies
if (typeof window !== 'undefined') {
    // Al volver a la pestaña (cambiar entre pestañas de navegador)
    window.addEventListener('focus', () => {
        cargarPoliticaContrasenas().then(refrescarTodosLosMedidores);
    });

    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            cargarPoliticaContrasenas().then(refrescarTodosLosMedidores);
        }
    });

    // Evento storage entre pestañas
    window.addEventListener('storage', (e) => {
        if (e.key === 'sb_password_policy_updated') {
            cargarPoliticaContrasenas().then(refrescarTodosLosMedidores);
        }
    });

    // Evento personalizado directo
    window.addEventListener('sb:password-policy-updated', (e) => {
        if (e.detail) {
            Object.assign(currentPolicy, e.detail);
            refrescarTodosLosMedidores();
        } else {
            cargarPoliticaContrasenas().then(refrescarTodosLosMedidores);
        }
    });
}
