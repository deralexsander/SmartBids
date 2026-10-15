// ==========================================================================
// MODAL DE AUTENTICACIÓN DE DOS FACTORES (2FA)
// ==========================================================================
export function abrirModal2FA() {
    const modal2FA = document.getElementById('modal-2fa');
    const otpInputs = document.querySelectorAll('.otp-digit-input');

    if (!modal2FA) return;

    modal2FA.classList.remove('closing');
    modal2FA.classList.add('active');

    if (otpInputs.length > 0) {
        otpInputs[0].focus();
    }
}

export function cerrarModal2FA() {
    const modal2FA = document.getElementById('modal-2fa');
    const otpInputs = document.querySelectorAll('.otp-digit-input');

    if (!modal2FA) return;

    modal2FA.classList.add('closing');

    setTimeout(() => {
        modal2FA.classList.remove('active', 'closing');
        otpInputs.forEach((input) => (input.value = ''));
        const otpMsg = document.getElementById('otp-message');
        if (otpMsg) otpMsg.textContent = '';
    }, 400);
}

window.abrirModal2FA = abrirModal2FA;
window.cerrarModal2FA = cerrarModal2FA;