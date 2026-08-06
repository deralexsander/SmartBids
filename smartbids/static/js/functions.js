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
