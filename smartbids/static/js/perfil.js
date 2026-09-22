import { setButtonLoading, SessionManager } from './functions.js';
import { mostrarMensaje } from './mensaje.js';

// ==========================================================================
// SECCIÓN PERFIL: Conectada a PostgreSQL (Sin llamadas a Firestore)
// ==========================================================================
function formatTimestamp(ts) {
    if (!ts) return 'No registrada';
    const date = new Date(ts);
    return date.toLocaleDateString('es-CL', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

export async function inicializarVistaPerfil(user) {
    if (!user) return;

    try {
        const resp = await fetch('/api/obtener-perfil/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid: user.uid })
        });
        const resData = await resp.json();

        if (resData.status === 'ok') {
            const data = resData.datos;
            const emp = data.empresa || {};
            const pref = data.preferencias || {};

            // 1. Sidebar y Cabeceras
            const n1 = data.sus_nombre1 || '';
            const n2 = data.sus_nombre2 || '';
            const a1 = data.sus_apellido1 || '';
            const a2 = data.sus_apellido2 || '';
            const nombreCompleto = [n1, n2, a1, a2].filter(Boolean).join(' ') || 'Suscriptor';

            document.getElementById('profile-fullname-header').textContent = nombreCompleto;
            document.getElementById('profile-social-header').textContent = data.sus_nombre_social ? `@${data.sus_nombre_social}` : `@suscriptor_${data.id_suscriptor}`;
            
            // ===================================================================
            // ✅ ESTADO LEÍDO DIRECTO DE POSTGRESQL (config.estado_suscriptor)
            // ===================================================================
            document.getElementById('profile-role-badge').textContent = data.nombre_estado || 'Sin Estado';
            
            document.getElementById('profile-initials').textContent = data.sus_iniciales || (n1 && a1 ? (n1[0] + a1[0]).toUpperCase() : 'SB');
            document.getElementById('profile-id-suscriptor').textContent = data.id_suscriptor || '--';
            document.getElementById('profile-uid-header').textContent = user.uid;
            document.getElementById('profile-created-at').textContent = formatTimestamp(data.fecha_registro);
            document.getElementById('profile-last-login').textContent = formatTimestamp(data.fecha_actualizacion);
            document.getElementById('profile-token-id').textContent = data.token_sesion || SessionManager.getLocalToken() || 'No asignado';
            document.getElementById('profile-email').value = user.email || '';

            // 2. Formulario Datos Personales
            document.getElementById('profile-nombre1').value = n1;
            document.getElementById('profile-nombre2').value = n2;
            document.getElementById('profile-apellido1').value = a1;
            document.getElementById('profile-apellido2').value = a2;
            document.getElementById('profile-nombre-social').value = data.sus_nombre_social || '';
            document.getElementById('profile-iniciales').value = data.sus_iniciales || '';

            // 3. Formulario Empresa
            document.getElementById('empresa-rut').value = emp.emp_rut || '';
            document.getElementById('empresa-fantasia').value = emp.emp_nombre_fantasia || '';
            document.getElementById('empresa-razon-social').value = emp.emp_razon_social || '';
            document.getElementById('empresa-correo').value = emp.emp_contacto_correo || '';
            document.getElementById('empresa-iniciales').value = emp.emp_iniciales || '';
            document.getElementById('empresa-telefono').value = emp.emp_contacto_telefono || '';
            document.getElementById('empresa-comuna').value = emp.emp_codigo_comuna || '';
            document.getElementById('empresa-direccion').value = emp.emp_direccion || '';

            // 4. Formulario Filtros de Licitación
            document.getElementById('pref-comunas').value = pref.pref_comunas || '';
            document.getElementById('pref-productos').value = pref.pref_productos || '';
            document.getElementById('pref-tipo-lic').value = pref.pref_tipo_licitacion || '';
            document.getElementById('pref-ucom').value = pref.pref_ucom || '';
            document.getElementById('pref-palabras').value = pref.pref_palabras_claves || '';
        }
    } catch (err) {
        console.error('[SmartBids] Error al cargar perfil desde PostgreSQL:', err);
    }

    // Submit: Datos Personales
    const formDatos = document.getElementById('form-perfil-datos');
    if (formDatos) {
        formDatos.onsubmit = async (e) => {
            e.preventDefault();
            const btn = formDatos.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Guardando...');
            try {
                const resp = await fetch('/api/actualizar-perfil/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        uid: user.uid,
                        sus_nombre1: document.getElementById('profile-nombre1').value,
                        sus_nombre2: document.getElementById('profile-nombre2').value,
                        sus_apellido1: document.getElementById('profile-apellido1').value,
                        sus_apellido2: document.getElementById('profile-apellido2').value,
                        sus_nombre_social: document.getElementById('profile-nombre-social').value,
                        sus_iniciales: document.getElementById('profile-iniciales').value,
                    })
                });
                const res = await resp.json();
                mostrarMensaje(res.mensaje, res.status === 'ok' ? 'exito' : 'error');
                await inicializarVistaPerfil(user);
            } finally {
                setButtonLoading(btn, false);
            }
        };
    }

    // Submit: Empresa
    const formEmpresa = document.getElementById('form-perfil-empresa');
    if (formEmpresa) {
        formEmpresa.onsubmit = async (e) => {
            e.preventDefault();
            const btn = formEmpresa.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Guardando...');
            try {
                const resp = await fetch('/api/actualizar-empresa/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        uid: user.uid,
                        emp_rut: document.getElementById('empresa-rut').value,
                        emp_nombre_fantasia: document.getElementById('empresa-fantasia').value,
                        emp_razon_social: document.getElementById('empresa-razon-social').value,
                        emp_contacto_correo: document.getElementById('empresa-correo').value,
                        emp_iniciales: document.getElementById('empresa-iniciales').value,
                        emp_contacto_telefono: document.getElementById('empresa-telefono').value,
                        emp_codigo_comuna: document.getElementById('empresa-comuna').value,
                        emp_direccion: document.getElementById('empresa-direccion').value,
                    })
                });
                const res = await resp.json();
                mostrarMensaje(res.mensaje, res.status === 'ok' ? 'exito' : 'error');
            } finally {
                setButtonLoading(btn, false);
            }
        };
    }

    // Submit: Filtros de Licitación
    const formFiltros = document.getElementById('form-perfil-preferencias');
    if (formFiltros) {
        formFiltros.onsubmit = async (e) => {
            e.preventDefault();
            const btn = formFiltros.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Guardando...');
            try {
                const resp = await fetch('/api/actualizar-preferencias/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        uid: user.uid,
                        pref_comunas: document.getElementById('pref-comunas').value,
                        pref_productos: document.getElementById('pref-productos').value,
                        pref_tipo_licitacion: document.getElementById('pref-tipo-lic').value,
                        pref_ucom: document.getElementById('pref-ucom').value,
                        pref_palabras_claves: document.getElementById('pref-palabras').value,
                    })
                });
                const res = await resp.json();
                mostrarMensaje(res.mensaje, res.status === 'ok' ? 'exito' : 'error');
            } finally {
                setButtonLoading(btn, false);
            }
        };
    }
}


