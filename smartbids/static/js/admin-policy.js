import { auth } from './firebase-config.js';
import { mostrarMensaje } from './mensaje.js';

const policyModal = document.getElementById('password-policy-modal');
const policyForm = document.getElementById('password-policy-form');
const policyMessage = document.getElementById('password-policy-feedback');
const openPolicyButton = document.getElementById('btn-abrir-politica-password');
const closePolicyButton = document.getElementById('btn-cerrar-politica-password');
const closePolicyButtonX = document.getElementById('btn-cerrar-politica-password-x');
const modeEnforce = document.getElementById('mode-enforce');
const modeOff = document.getElementById('mode-off');
const forceUpgrade = document.getElementById('password-policy-force-upgrade');
const minLength = document.getElementById('password-policy-min-length');
const maxLength = document.getElementById('password-policy-max-length');
const uppercase = document.getElementById('password-policy-uppercase');
const lowercase = document.getElementById('password-policy-lowercase');
const special = document.getElementById('password-policy-special');
const numeric = document.getElementById('password-policy-numeric');
let policyCache = null;
let policyRequest = null;

function adminHeaders() {
    const uid = auth.currentUser?.uid;
    return uid ? { 'X-Firebase-UID': uid } : {};
}

function setPolicyMessage(text, type = 'info') {
    if (!policyMessage) return;
    policyMessage.textContent = text;
    policyMessage.style.color = type === 'error' ? '#c53030' : 'var(--dark-green)';
}

function openPolicyModal() {
    if (policyModal) policyModal.classList.add('active');
}

function closePolicyModal() {
    if (policyModal) {
        policyModal.classList.remove('active');
        policyModal.classList.add('closing');
        setTimeout(() => policyModal.classList.remove('closing'), 400);
    }
    setPolicyMessage('');
}

function applyPolicyData(config) {
    const policyConfig = config.passwordPolicyConfig || {};
    const version = policyConfig.passwordPolicyVersions?.[0] || {};
    const options = version.customStrengthOptions || {};

    const enforcement = policyConfig.passwordPolicyEnforcementState || 'OFF';
    modeEnforce.checked = enforcement === 'ENFORCE';
    modeOff.checked = enforcement !== 'ENFORCE';
    forceUpgrade.checked = Boolean(policyConfig.forceUpgradeOnSignin);
    minLength.value = options.minPasswordLength || 6;
    maxLength.value = options.maxPasswordLength || 4096;
    uppercase.checked = Boolean(options.containsUppercaseCharacter);
    lowercase.checked = Boolean(options.containsLowercaseCharacter);
    special.checked = Boolean(options.containsNonAlphanumericCharacter);
    numeric.checked = Boolean(options.containsNumericCharacter);
}

async function loadPolicy() {
    if (policyCache) {
        applyPolicyData(policyCache);
        setPolicyMessage('Política actual cargada.');
        return;
    }

    if (policyRequest) return policyRequest;

    setPolicyMessage('Cargando política actual...');

    policyRequest = (async () => {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);

        try {
            const response = await fetch('/api/firebase/politica-contrasenas/', {
                headers: adminHeaders(),
                signal: controller.signal
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.mensaje || 'No se pudo cargar la política.');
            policyCache = data;
            applyPolicyData(data);
            setPolicyMessage('Política actual cargada.');
        } catch (error) {
            const message = error.name === 'AbortError'
                ? 'La consulta tardó demasiado. Verifica la configuración administrativa de Google Cloud.'
                : error.message;
            setPolicyMessage(message, 'error');
        } finally {
            clearTimeout(timeout);
            policyRequest = null;
        }
    })();

    return policyRequest;
}

async function savePolicy(event) {
    event.preventDefault();

    const minimum = Number(minLength.value);
    const maximum = Number(maxLength.value);
    if (minimum < 6 || minimum > 30 || maximum < 6 || maximum > 4096 || maximum < minimum) {
        setPolicyMessage('La longitud mínima debe estar entre 6 y 30, y la máxima entre 6 y 4096. Además, la máxima debe ser mayor o igual.', 'error');
        return;
    }

    const saveButton = policyForm.querySelector('button[type="submit"]');
    saveButton.disabled = true;
    saveButton.textContent = 'Guardando...';

    try {
        const response = await fetch('/api/firebase/politica-contrasenas/', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                ...adminHeaders()
            },
            body: JSON.stringify({
                passwordPolicyEnforcementState: modeEnforce.checked ? 'ENFORCE' : 'OFF',
                forceUpgradeOnSignin: forceUpgrade.checked,
                passwordPolicyVersions: [{
                    customStrengthOptions: {
                        minPasswordLength: minimum,
                        maxPasswordLength: maximum,
                        containsUppercaseCharacter: uppercase.checked,
                        containsLowercaseCharacter: lowercase.checked,
                        containsNonAlphanumericCharacter: special.checked,
                        containsNumericCharacter: numeric.checked
                    }
                }]
            })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.mensaje || 'No se pudo guardar la política.');

        policyCache = data;
        setPolicyMessage('Política de contraseñas actualizada correctamente.');
        mostrarMensaje('Política de contraseñas actualizada.', 'exito');
    } catch (error) {
        setPolicyMessage(error.message, 'error');
    } finally {
        saveButton.disabled = false;
        saveButton.textContent = 'Guardar política';
    }
}

if (openPolicyButton) {
    openPolicyButton.addEventListener('click', () => {
        openPolicyModal();
        loadPolicy();
    });
}

if (closePolicyButton) closePolicyButton.addEventListener('click', closePolicyModal);
if (closePolicyButtonX) closePolicyButtonX.addEventListener('click', closePolicyModal);
if (policyForm) policyForm.addEventListener('submit', savePolicy);
if (policyModal) {
    policyModal.addEventListener('click', (event) => {
        if (event.target === policyModal) closePolicyModal();
    });
}
