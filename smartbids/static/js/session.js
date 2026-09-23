// ==========================================================================
// AUTENTICACIÓN DE NAVEGACIÓN Y SESIÓN LOCAL
// ==========================================================================
export function redirectIfAuthenticated(auth, redirectPath = '/') {
    const currentPath = window.location.pathname;

    auth.onAuthStateChanged((user) => {
        const shouldRedirect = Boolean(user && user.emailVerified && (
            currentPath.includes('/ingreso') || currentPath.includes('/registro')
        ));

        if (shouldRedirect) {
            window.location.replace(redirectPath);
        }
    });
}

export function generateSessionId() {
    return crypto.randomUUID();
}

export const SessionManager = {
    setLocalToken(token) {
        localStorage.setItem('smartbids_session_token', token);
    },
    getLocalToken() {
        return localStorage.getItem('smartbids_session_token');
    },
    clearLocalToken() {
        localStorage.removeItem('smartbids_session_token');
    }
};