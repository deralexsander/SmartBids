import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js';
import { getAuth } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js';
import { getFirestore } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js';

const configScript = document.getElementById('firebase-config');
let firebaseConfig = {};

if (configScript) {
    try {
        firebaseConfig = JSON.parse(configScript.textContent);
    } catch (e) {
        console.error('[SmartBids] Error parseando JSON de Firebase:', e);
    }
}

if (!firebaseConfig || !firebaseConfig.apiKey) {
    console.error('[SmartBids] ❌ Error: No se encontraron las credenciales de Firebase. Verifica tu archivo .env y el servidor de Django.');
}

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

export { firebaseConfig, app, auth, db };