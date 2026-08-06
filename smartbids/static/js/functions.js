export function redirectIfAuthenticated(auth, redirectPath = '/') {
    const currentPath = window.location.pathname;

    auth.onAuthStateChanged((user) => {
        if (user && user.emailVerified) {
            if (currentPath.includes('/ingreso') || currentPath.includes('/registro')) {
                window.location.href = redirectPath;
            }
        }
    });
}
