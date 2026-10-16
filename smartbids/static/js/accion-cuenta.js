/**
 * SmartBids - Controlador de Acciones de Cuenta (Activar Cuenta y Cambiar Contraseña)
 * Procesa oobCodes de Firebase con la interfaz corporativa y redirige a /ingreso.
 */

import { auth } from './firebase-config.js';
import {
    applyActionCode,
    verifyPasswordResetCode,
    confirmPasswordReset
} from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js';

document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const mode = urlParams.get('mode');
    const oobCode = urlParams.get('oobCode');

    const panelLoading = document.getElementById('panel-loading-accion');
    const panelVerify = document.getElementById('panel-verificar-correo');
    const panelReset = document.getElementById('panel-reset-password');
    const panelError = document.getElementById('panel-error-accion');

    const errorTitle = document.getElementById('error-title');
    const errorDesc = document.getElementById('error-desc');
    const pageTitle = document.getElementById('page-title');

    function hideAllPanels() {
        if (panelLoading) panelLoading.style.display = 'none';
        if (panelVerify) panelVerify.style.display = 'none';
        if (panelReset) panelReset.style.display = 'none';
        if (panelError) panelError.style.display = 'none';
    }

    function showError(title, message) {
        hideAllPanels();
        if (errorTitle) errorTitle.textContent = title;
        if (errorDesc) errorDesc.textContent = message;
        if (panelError) panelError.style.display = 'block';
    }

    function setBtnLoading(btn, isLoading, loadingText = 'Procesando...') {
        if (!btn) return;
        if (isLoading) {
            btn.disabled = true;
            btn.dataset.originalHtml = btn.innerHTML;
            btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${loadingText}`;
        } else {
            btn.disabled = false;
            if (btn.dataset.originalHtml) {
                btn.innerHTML = btn.dataset.originalHtml;
            }
        }
    }

    // Configurar alternancia de visibilidad de contraseña
    function setupPasswordToggle(toggleBtnId, inputId, iconId) {
        const toggleBtn = document.getElementById(toggleBtnId);
        const input = document.getElementById(inputId);
        const icon = document.getElementById(iconId);
        if (toggleBtn && input && icon) {
            toggleBtn.addEventListener('click', () => {
                const isPassword = input.getAttribute('type') === 'password';
                input.setAttribute('type', isPassword ? 'text' : 'password');
                icon.className = isPassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye';
            });
        }
    }

    setupPasswordToggle('toggle-new-password', 'new-password', 'toggle-new-password-icon');
    setupPasswordToggle('toggle-confirm-password', 'confirm-new-password', 'toggle-confirm-password-icon');

    // Validación inicial de parámetros
    if (!mode || !oobCode) {
        showError(
            'Enlace incompleto o inválido',
            'No se proporcionaron los parámetros de seguridad necesarios. Asegúrate de abrir el enlace completo que recibiste en tu correo.'
        );
        return;
    }

    // -------------------------------------------------------------
    // 1. FLUJO: ACTIVAR CUENTA (mode === 'verifyEmail')
    // -------------------------------------------------------------
    if (mode === 'verifyEmail') {
        if (pageTitle) pageTitle.textContent = 'SmartBids - Activar Cuenta';
        hideAllPanels();
        panelVerify.style.display = 'block';

        const btnActivar = document.getElementById('btn-activar-cuenta');
        const verifyFeedback = document.getElementById('verify-feedback');

        if (btnActivar) {
            btnActivar.addEventListener('click', async () => {
                setBtnLoading(btnActivar, true, 'Activando cuenta...');
                if (verifyFeedback) verifyFeedback.style.display = 'none';

                try {
                    await applyActionCode(auth, oobCode);

                    // Mensaje de éxito en la tarjeta
                    if (verifyFeedback) {
                        verifyFeedback.className = 'action-feedback action-feedback--success';
                        verifyFeedback.innerHTML = `
                            <i class="fa-solid fa-circle-check"></i>
                            <strong>¡Cuenta activada exitosamente!</strong>
                            <p>Tu correo ha sido verificado. Te estamos redirigiendo a la pantalla de ingreso...</p>
                        `;
                        verifyFeedback.style.display = 'flex';
                    }
                    btnActivar.style.display = 'none';

                    // Guardar mensaje flash para mostrar en /ingreso
                    sessionStorage.setItem('flash_message', JSON.stringify({
                        texto: '¡Cuenta activada exitosamente! Ya puedes iniciar sesión en SmartBids.',
                        tipo: 'exito',
                        duracion: 10000
                    }));

                    // Redirigir al ingresar
                    setTimeout(() => {
                        window.location.href = '/ingreso';
                    }, 1800);

                } catch (error) {
                    console.error('[SmartBids] Error al activar cuenta:', error);
                    setBtnLoading(btnActivar, false);

                    let errorMsg = 'El enlace de activación ha expirado o ya fue utilizado.';
                    if (error.code === 'auth/invalid-action-code') {
                        errorMsg = 'El enlace no es válido o tu cuenta ya fue verificada previamente.';
                    } else if (error.code === 'auth/expired-action-code') {
                        errorMsg = 'El enlace ha expirado. Por favor solicita uno nuevo desde la pantalla de ingreso.';
                    }

                    if (verifyFeedback) {
                        verifyFeedback.className = 'action-feedback action-feedback--error';
                        verifyFeedback.innerHTML = `
                            <i class="fa-solid fa-triangle-exclamation"></i>
                            <span>${errorMsg}</span>
                        `;
                        verifyFeedback.style.display = 'flex';
                    }
                }
            });
        }
        return;
    }

    // -------------------------------------------------------------
    // 2. FLUJO: CAMBIAR CONTRASEÑA (mode === 'resetPassword')
    // -------------------------------------------------------------
    if (mode === 'resetPassword') {
        if (pageTitle) pageTitle.textContent = 'SmartBids - Cambiar Contraseña';

        let accountEmail = '';
        try {
            // Verificar primero si el oobCode es válido
            accountEmail = await verifyPasswordResetCode(auth, oobCode);
            hideAllPanels();
            panelReset.style.display = 'block';

            const emailDisplay = document.getElementById('reset-account-email');
            if (emailDisplay && accountEmail) {
                emailDisplay.textContent = accountEmail;
            }
        } catch (error) {
            console.error('[SmartBids] Código de reseteo inválido:', error);
            showError(
                'El enlace ha expirado o es inválido',
                'El enlace para restablecer tu contraseña ya no es válido o fue utilizado. Por favor solicita uno nuevo desde la pantalla de ingreso.'
            );
            return;
        }

        const resetForm = document.getElementById('reset-password-form');
        const resetFeedback = document.getElementById('reset-feedback');
        const btnCambiar = document.getElementById('btn-cambiar-password');

        if (resetForm) {
            resetForm.addEventListener('submit', async (e) => {
                e.preventDefault();

                const newPasswordInput = document.getElementById('new-password');
                const confirmPasswordInput = document.getElementById('confirm-new-password');

                const newPassword = newPasswordInput ? newPasswordInput.value : '';
                const confirmPassword = confirmPasswordInput ? confirmPasswordInput.value : '';

                if (resetFeedback) resetFeedback.style.display = 'none';

                if (!newPassword || !confirmPassword) {
                    if (resetFeedback) {
                        resetFeedback.className = 'action-feedback action-feedback--error';
                        resetFeedback.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i><span>Por favor completa ambos campos.</span>';
                        resetFeedback.style.display = 'flex';
                    }
                    return;
                }

                if (newPassword.length < 8) {
                    if (resetFeedback) {
                        resetFeedback.className = 'action-feedback action-feedback--error';
                        resetFeedback.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i><span>La contraseña debe tener al menos 8 caracteres.</span>';
                        resetFeedback.style.display = 'flex';
                    }
                    return;
                }

                if (newPassword !== confirmPassword) {
                    if (resetFeedback) {
                        resetFeedback.className = 'action-feedback action-feedback--error';
                        resetFeedback.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i><span>Las contraseñas no coinciden.</span>';
                        resetFeedback.style.display = 'flex';
                    }
                    return;
                }

                setBtnLoading(btnCambiar, true, 'Guardando nueva contraseña...');

                try {
                    await confirmPasswordReset(auth, oobCode, newPassword);

                    // Notificación opcional por correo de seguridad
                    if (accountEmail) {
                        try {
                            fetch('/api/enviar-correo-cambio-password/', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ email: accountEmail })
                            }).catch(() => {});
                        } catch (_) {}
                    }

                    // Mensaje de éxito
                    if (resetFeedback) {
                        resetFeedback.className = 'action-feedback action-feedback--success';
                        resetFeedback.innerHTML = `
                            <i class="fa-solid fa-circle-check"></i>
                            <strong>¡Contraseña cambiada correctamente!</strong>
                            <p>Tu nueva clave ha sido guardada. Te estamos redirigiendo a la pantalla de ingreso...</p>
                        `;
                        resetFeedback.style.display = 'flex';
                    }

                    btnCambiar.style.display = 'none';
                    if (newPasswordInput) newPasswordInput.disabled = true;
                    if (confirmPasswordInput) confirmPasswordInput.disabled = true;

                    // Guardar mensaje flash y email registrado para /ingreso
                    sessionStorage.setItem('flash_message', JSON.stringify({
                        texto: 'Contraseña cambiada correctamente. Ya puedes ingresar con tu nueva clave.',
                        tipo: 'exito',
                        duracion: 10000
                    }));
                    if (accountEmail) {
                        sessionStorage.setItem('registered_email', accountEmail);
                    }

                    // Redirigir al ingresar
                    setTimeout(() => {
                        window.location.href = '/ingreso';
                    }, 1800);

                } catch (error) {
                    console.error('[SmartBids] Error al cambiar contraseña:', error);
                    setBtnLoading(btnCambiar, false);

                    let errorMsg = 'No pudimos actualizar tu contraseña. Inténtalo de nuevo.';
                    if (error.code === 'auth/weak-password') {
                        errorMsg = 'La contraseña elegida es muy débil. Debe combinar al menos 8 letras y números.';
                    } else if (error.code === 'auth/expired-action-code') {
                        errorMsg = 'El enlace ha expirado. Por favor solicita uno nuevo desde la pantalla de ingreso.';
                    }

                    if (resetFeedback) {
                        resetFeedback.className = 'action-feedback action-feedback--error';
                        resetFeedback.innerHTML = `
                            <i class="fa-solid fa-circle-exclamation"></i>
                            <span>${errorMsg}</span>
                        `;
                        resetFeedback.style.display = 'flex';
                    }
                }
            });
        }
        return;
    }

    // -------------------------------------------------------------
    // 3. MODO NO SOPORTADO
    // -------------------------------------------------------------
    showError(
        'Acción no reconocida',
        'El tipo de solicitud especificado en el enlace no es compatible con el sistema.'
    );
});
