import { auth } from './firebase-config.js';
import { EmailAuthProvider, reauthenticateWithCredential, updatePassword, signOut } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js';
import { setButtonLoading, SessionManager } from './functions.js';
import { mostrarMensaje } from './mensaje.js';

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

// ==========================================================================
// 1. CÁLCULO DE COMPLETITUD Y SEMÁFORO DE COLORES (ROJO - AMARILLO - VERDE)
// ==========================================================================
export function actualizarPorcentajePerfil() {
    const checkVal = (id) => Boolean(document.getElementById(id)?.value?.trim());

    // 1. Datos Personales (Información del Suscriptor)
    const suscriptorChecks = [
        checkVal('profile-nombre1'),
        checkVal('profile-apellido1'),
        checkVal('profile-nombre-social') || checkVal('profile-nombre2') || checkVal('profile-apellido2'),
        checkVal('profile-iniciales')
    ];

    // 2. Información de la Empresa
    const empresaChecks = [
        checkVal('empresa-rut'),
        checkVal('empresa-fantasia'),
        checkVal('empresa-razon-social'),
        checkVal('empresa-correo'),
        checkVal('empresa-comuna'),
        checkVal('empresa-direccion') || checkVal('empresa-telefono') || checkVal('empresa-iniciales')
    ];

    // 3. Filtros y los 3 Ejes de Mercado
    const countComunas = comunasManager ? comunasManager.getCodes().length : 0;
    const countProductos = productosManager ? productosManager.getCodes().length : 0;
    const countUcom = ucomManager ? ucomManager.getCodes().length : 0;
    const tieneProcedimiento = checkVal('pref-tipo-lic');
    const tienePalabras = checkVal('pref-palabras');

    const filtrosChecks = [
        countComunas > 0,
        countProductos > 0,
        countUcom > 0,
        tieneProcedimiento || tienePalabras
    ];

    // Total de 14 items ponderados equitativamente
    const totalItems = [...suscriptorChecks, ...empresaChecks, ...filtrosChecks];
    const completados = totalItems.filter(Boolean).length;
    const porcentaje = Math.round((completados / totalItems.length) * 100);

    // Actualización de elementos en el DOM
    const barFill = document.getElementById('profile-progress-fill');
    const numberText = document.getElementById('profile-progress-number');
    const statusText = document.getElementById('profile-progress-status');

    if (!barFill || !numberText) return;

    barFill.style.width = `${porcentaje}%`;
    numberText.textContent = `${porcentaje}%`;

    // Escala del Semáforo
    if (porcentaje < 40) {
        // Rojo
        barFill.style.backgroundColor = '#e53e3e';
        numberText.style.color = '#e53e3e';
        if (statusText) statusText.textContent = 'Perfil básico. Faltan datos esenciales de empresa o filtros.';
    } else if (porcentaje < 80) {
        // Amarillo / Ámbar
        barFill.style.backgroundColor = '#dd6b20';
        numberText.style.color = '#dd6b20';
        if (statusText) statusText.textContent = 'Perfil intermedio. Puedes afinar tus filtros de búsqueda y datos tributarios.';
    } else {
        // Verde
        barFill.style.backgroundColor = 'var(--accent-green)';
        numberText.style.color = 'var(--dark-green)';
        if (statusText) statusText.textContent = '¡Excelente! Perfil y filtros de licitación completamente calibrados.';
    }
}

// ==========================================================================
// 2. GESTOR DE TAGS / CHIPS (Muestra NOMBRE, guarda CÓDIGO)
// ==========================================================================
class TagManager {
    constructor(containerId, hiddenInputId, placeholderText) {
        this.container = document.getElementById(containerId);
        this.hiddenInput = document.getElementById(hiddenInputId);
        this.placeholderText = placeholderText;
        this.items = new Map(); // code -> label
    }

    setItems(itemArray) {
        this.items.clear();
        (itemArray || []).forEach(item => {
            if (typeof item === 'object' && item !== null) {
                const code = String(item.code || '').trim();
                const label = String(item.label || item.code || '').trim();
                if (code) this.items.set(code, label);
            } else if (item) {
                const val = String(item).trim();
                if (val) this.items.set(val, val);
            }
        });
        this.render();
    }

    add(code, label) {
        const c = String(code || '').trim();
        const l = String(label || code || '').trim();
        if (!c) return;
        this.items.set(c, l);
        this.render();
    }

    remove(code) {
        this.items.delete(String(code).trim());
        this.render();
    }

    getCodes() {
        const codesFromMap = Array.from(this.items.keys()).filter(Boolean);
        if (codesFromMap.length > 0) return codesFromMap;
        
        if (this.hiddenInput && this.hiddenInput.value.trim()) {
            return this.hiddenInput.value.split(',').map(s => s.trim()).filter(Boolean);
        }
        return [];
    }

    render() {
        if (!this.container) return;
        this.container.innerHTML = '';
        const codes = Array.from(this.items.keys());
        
        if (this.hiddenInput) {
            this.hiddenInput.value = codes.join(',');
        }

        if (codes.length === 0) {
            this.container.innerHTML = `<span style="color: var(--muted-teal); font-size: 0.85rem; padding: 4px;">${this.placeholderText}</span>`;
            actualizarPorcentajePerfil();
            return;
        }

        codes.forEach(code => {
            const label = this.items.get(code) || code;
            const chip = document.createElement('div');
            chip.className = 'dash-badge';
            chip.style.cssText = 'display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; font-size: 0.83rem; background: var(--white); border: 1.5px solid var(--accent-green); color: var(--dark-green); border-radius: 20px; font-weight: 700; box-shadow: 0 2px 6px rgba(0,0,0,0.04);';
            chip.innerHTML = `
                <span>${label}</span>
                <i class="fa-solid fa-xmark" style="cursor: pointer; color: #e53e3e; margin-left: 4px;" title="Eliminar"></i>
            `;
            chip.querySelector('i').addEventListener('click', () => this.remove(code));
            this.container.appendChild(chip);
        });

        actualizarPorcentajePerfil();
    }
}

// Instancias globales de tags
let comunasManager = null;
let productosManager = null;
let ucomManager = null;
let territoryData = null;

// ==========================================================================
// 3. BUSCADOR FLOTANTE CON AUTOCOMPLETADO (ACUMULATIVO)
// ==========================================================================
function setupDropdownSearch(inputId, catalogType, codeField, labelField, onSelect) {
    const input = document.getElementById(inputId);
    if (!input || input.dataset.bound === 'true') return;
    input.dataset.bound = 'true';

    const resultsBox = document.createElement('div');
    resultsBox.style.cssText = 'position: absolute; left: 0; right: 0; top: 100%; background: #fff; border: 1.5px solid var(--soft-mint); border-radius: 8px; max-height: 220px; overflow-y: auto; z-index: 1000; box-shadow: 0 10px 25px rgba(0,0,0,0.1); display: none; margin-top: 4px;';
    input.parentElement.style.position = 'relative';
    input.parentElement.appendChild(resultsBox);

    let timer = null;
    input.addEventListener('input', () => {
        clearTimeout(timer);
        const query = input.value.trim();
        if (query.length < 2) {
            resultsBox.style.display = 'none';
            resultsBox.innerHTML = '';
            return;
        }

        timer = setTimeout(async () => {
            try {
                const response = await fetch(`/api/catalogos-preferencias/?tipo=${catalogType}&q=${encodeURIComponent(query)}`);
                const data = await response.json();
                const list = data.resultados || [];
                
                resultsBox.innerHTML = '';
                if (list.length === 0) {
                    resultsBox.innerHTML = '<div style="padding: 10px; font-size: 0.85rem; color: var(--muted-teal);">Sin coincidencias.</div>';
                } else {
                    list.forEach(item => {
                        const itemEl = document.createElement('div');
                        itemEl.style.cssText = 'padding: 8px 12px; cursor: pointer; font-size: 0.88rem; border-bottom: 1px solid #f0f0f0; transition: background 0.15s;';
                        itemEl.innerHTML = `<strong>${item[labelField]}</strong> <small style="color: var(--muted-teal);">(${item[codeField]})</small>`;
                        
                        itemEl.onmouseenter = () => itemEl.style.background = 'rgba(30, 196, 152, 0.08)';
                        itemEl.onmouseleave = () => itemEl.style.background = 'transparent';
                        
                        itemEl.addEventListener('pointerdown', (e) => {
                            e.preventDefault();
                            onSelect(item[codeField], item[labelField]);
                            input.value = '';
                            resultsBox.style.display = 'none';
                        });
                        resultsBox.appendChild(itemEl);
                    });
                }
                resultsBox.style.display = 'block';
            } catch (error) {
                console.error('[SmartBids] Error en autocompletado:', error);
            }
        }, 200);
    });

    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !resultsBox.contains(e.target)) {
            resultsBox.style.display = 'none';
        }
    });
}

// ==========================================================================
// 4. ÁRBOL GEOGRÁFICO (MODAL TRI-STATE)
// ==========================================================================
async function setupTerritoryTree() {
    const openBtn = document.getElementById('btn-ajustar-cobertura');
    const modal = document.getElementById('territory-modal');
    const tree = document.getElementById('territory-tree');
    const closeBtn = document.getElementById('btn-cerrar-cobertura');
    const closeX = document.getElementById('btn-cerrar-x');
    const saveBtn = document.getElementById('btn-guardar-cobertura');
    const searchInput = document.getElementById('territory-tree-search');
    const counter = document.getElementById('territory-counter');

    if (!openBtn || !modal || !tree || !saveBtn) return;
    if (openBtn.dataset.bound === 'true') return;
    openBtn.dataset.bound = 'true';

    function closeModal() {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }

    function updateCounter() {
        const total = tree.querySelectorAll('.comuna-check:checked').length;
        if (counter) counter.textContent = `${total} comunas seleccionadas`;
    }

    function updateParentState(node) {
        const children = [...node.querySelectorAll(':scope > .tree-children input[type="checkbox"]')];
        if (!children.length) return;

        const checked = children.filter(c => c.checked).length;
        const parentCheck = node.querySelector(':scope > .tree-header input[type="checkbox"]');
        if (parentCheck) {
            parentCheck.checked = checked === children.length;
            parentCheck.indeterminate = checked > 0 && checked < children.length;
        }
    }

    function renderTree(data) {
        const currentCodes = comunasManager ? comunasManager.getCodes() : [];
        const selectedSet = new Set(currentCodes.map(c => String(c).trim()));
        
        let html = '';
        (data.regiones || []).forEach(reg => {
            const regId = String(reg.codigo_region).trim();
            const provs = (data.provincias || []).filter(p => String(p.codigo_region_id ?? p.codigo_region).trim() === regId);
            let provsHtml = '';

            provs.forEach(prov => {
                const provId = String(prov.codigo_provincia).trim();
                const coms = (data.comunas || []).filter(c => String(c.codigo_provincia_id ?? c.codigo_provincia).trim() === provId);
                let comsHtml = '';

                coms.forEach(c => {
                    const cod = String(c.codigo_comuna).trim();
                    const isChecked = selectedSet.has(cod) ? 'checked' : '';
                    comsHtml += `
                        <div class="tree-item-comuna" style="margin-left: 28px; padding: 2px 0;">
                            <label style="cursor: pointer; display: inline-flex; align-items: center; gap: 8px;">
                                <input type="checkbox" class="comuna-check" value="${cod}" data-label="${c.nombre_comuna}" ${isChecked}>
                                <span>${c.nombre_comuna}</span>
                            </label>
                        </div>
                    `;
                });

                provsHtml += `
                    <div class="tree-node tree-province" style="margin-left: 20px; margin-top: 4px;">
                        <div class="tree-header" style="display: flex; align-items: center; gap: 8px; font-weight: 600; color: var(--dark-green);">
                            <i class="fa-solid fa-folder" style="color: var(--soft-mint); font-size: 0.85rem;"></i>
                            <label style="cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
                                <input type="checkbox" class="province-check">
                                <span>${prov.nombre_provincia}</span>
                            </label>
                        </div>
                        <div class="tree-children" style="margin-top: 2px;">
                            ${comsHtml}
                        </div>
                    </div>
                `;
            });

            html += `
                <div class="tree-node tree-region" style="margin-bottom: 12px; background: #fff; padding: 8px 12px; border-radius: 8px; border: 1px solid #eaeaea;">
                    <div class="tree-header" style="display: flex; align-items: center; gap: 8px; font-weight: 800; color: var(--dark-green); font-size: 0.96rem;">
                        <i class="fa-solid fa-map" style="color: var(--accent-green); font-size: 0.9rem;"></i>
                        <label style="cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
                            <input type="checkbox" class="region-check">
                            <span>${reg.nombre_region}</span>
                        </label>
                    </div>
                    <div class="tree-children" style="margin-top: 4px;">
                        ${provsHtml}
                    </div>
                </div>
            `;
        });

        tree.innerHTML = html || '<p>No se encontraron divisiones territoriales.</p>';

        tree.querySelectorAll('.tree-region, .tree-province').forEach(node => {
            const check = node.querySelector(':scope > .tree-header input[type="checkbox"]');
            check.addEventListener('change', () => {
                node.querySelectorAll('.tree-children input[type="checkbox"]').forEach(child => {
                    child.checked = check.checked;
                    child.indeterminate = false;
                });
                tree.querySelectorAll('.tree-province').forEach(updateParentState);
                tree.querySelectorAll('.tree-region').forEach(updateParentState);
                updateCounter();
            });
        });

        tree.querySelectorAll('.comuna-check').forEach(check => {
            check.addEventListener('change', () => {
                tree.querySelectorAll('.tree-province').forEach(updateParentState);
                tree.querySelectorAll('.tree-region').forEach(updateParentState);
                updateCounter();
            });
        });

        tree.querySelectorAll('.tree-province').forEach(updateParentState);
        tree.querySelectorAll('.tree-region').forEach(updateParentState);
        updateCounter();
    }

    openBtn.addEventListener('click', async () => {
        modal.classList.add('active');
        modal.style.display = 'flex';
        modal.style.zIndex = '99999';

        if (!territoryData) {
            try {
                const resp = await fetch('/api/catalogos-preferencias/?tipo=territorio');
                territoryData = await resp.json();
                renderTree(territoryData);
            } catch (err) {
                tree.innerHTML = '<p style="color: #e53e3e;">Error al cargar datos territoriales.</p>';
            }
        } else {
            renderTree(territoryData);
        }
    });

    closeBtn.addEventListener('click', closeModal);
    if (closeX) closeX.addEventListener('click', closeModal);

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const term = searchInput.value.toLowerCase().trim();
            tree.querySelectorAll('.tree-region').forEach(regNode => {
                let matchRegion = false;
                regNode.querySelectorAll('.tree-province').forEach(provNode => {
                    let matchProv = false;
                    provNode.querySelectorAll('.tree-item-comuna').forEach(comNode => {
                        const visible = comNode.textContent.toLowerCase().includes(term);
                        comNode.style.display = visible ? 'block' : 'none';
                        if (visible) matchProv = true;
                    });
                    provNode.style.display = matchProv || provNode.textContent.toLowerCase().includes(term) ? 'block' : 'none';
                    if (provNode.style.display === 'block') matchRegion = true;
                });
                regNode.style.display = matchRegion || regNode.textContent.toLowerCase().includes(term) ? 'block' : 'none';
            });
        });
    }

    saveBtn.addEventListener('click', () => {
        const checkedComunas = [...tree.querySelectorAll('.comuna-check:checked')];
        const selected = checkedComunas.map(c => ({
            code: String(c.value).trim(),
            label: c.dataset.label || c.value
        }));
        if (comunasManager) {
            comunasManager.setItems(selected);
        }
        closeModal();
    });
}

// ==========================================================================
// 5. FUNCIONALIDADES AUXILIARES: CONTRASEÑA Y CIERRE DE SESIÓN
// ==========================================================================
function setupPasswordFunctionality(user) {
    const formPassword = document.getElementById('form-perfil-password');
    if (formPassword && formPassword.dataset.bound !== 'true') {
        formPassword.dataset.bound = 'true';
        formPassword.onsubmit = async (e) => {
            e.preventDefault();
            const currentPass = document.getElementById('profile-current-pass')?.value;
            const newPass = document.getElementById('profile-new-pass')?.value;
            const confirmPass = document.getElementById('profile-confirm-pass')?.value;

            if (newPass !== confirmPass) {
                mostrarMensaje('Las nuevas contraseñas no coinciden.', 'error');
                return;
            }

            if (newPass.length < 6) {
                mostrarMensaje('La nueva contraseña debe tener al menos 6 caracteres.', 'error');
                return;
            }

            const btn = formPassword.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Actualizando...');

            try {
                const currentUser = auth.currentUser || user;
                if (!currentUser || !currentUser.email) {
                    mostrarMensaje('Error: No hay sesión activa para actualizar clave.', 'error');
                    return;
                }

                // Re-autenticación obligatoria
                const credential = EmailAuthProvider.credential(currentUser.email, currentPass);
                await reauthenticateWithCredential(currentUser, credential);
                await updatePassword(currentUser, newPass);

                mostrarMensaje('Contraseña actualizada con éxito.', 'exito');
                formPassword.reset();
            } catch (err) {
                console.error('[SmartBids] Error al cambiar clave:', err);
                if (err.code === 'auth/wrong-password' || err.code === 'auth/invalid-credential') {
                    mostrarMensaje('La contraseña actual es incorrecta.', 'error');
                } else {
                    mostrarMensaje(`Error al cambiar clave: ${err.message}`, 'error');
                }
            } finally {
                setButtonLoading(btn, false);
            }
        };
    }
}

function setupLogoutButton() {
    const logoutBtn = document.getElementById('logout-button');
    if (logoutBtn && logoutBtn.dataset.bound !== 'true') {
        logoutBtn.dataset.bound = 'true';
        logoutBtn.addEventListener('click', async () => {
            if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
                try {
                    SessionManager.clearLocalToken();
                    localStorage.removeItem('smartbids_uid');
                    await signOut(auth);
                    window.location.replace('/ingreso');
                } catch (err) {
                    console.error('[SmartBids] Error al cerrar sesión:', err);
                    window.location.replace('/ingreso');
                }
            }
        });
    }
}

// ==========================================================================
// 6. INICIALIZADOR PRINCIPAL DE LA VISTA PERFIL
// ==========================================================================
export async function inicializarVistaPerfil(user) {
    if (!comunasManager) {
        comunasManager = new TagManager('chips-comunas', 'pref-comunas', 'Sin comunas seleccionadas (Aplica cobertura nacional)');
    }
    if (!productosManager) {
        productosManager = new TagManager('chips-productos', 'pref-productos', 'Sin filtros de productos (Aplica a todos los rubros)');
    }
    if (!ucomManager) {
        ucomManager = new TagManager('chips-ucom', 'pref-ucom', 'Sin entidades específicas (Monitorea todo el Estado)');
    }

    setupDropdownSearch('buscar-producto-input', 'producto', 'codigo_producto', 'descripcion', (code, label) => {
        productosManager.add(code, label);
    });

    setupDropdownSearch('buscar-ucom-input', 'unidad_compra', 'codigo_unidad_compra', 'ucom_descripcion', (code, label) => {
        ucomManager.add(code, label);
    });

    setupTerritoryTree();
    setupPasswordFunctionality(user);
    setupLogoutButton();

    // Eventos reactivos: recalcular porcentaje al escribir o modificar formularios
    ['form-perfil-datos', 'form-perfil-empresa', 'form-perfil-preferencias'].forEach(formId => {
        const f = document.getElementById(formId);
        if (f && f.dataset.listenerAttached !== 'true') {
            f.dataset.listenerAttached = 'true';
            f.addEventListener('input', actualizarPorcentajePerfil);
            f.addEventListener('change', actualizarPorcentajePerfil);
        }
    });

    const targetUid = user?.uid || auth.currentUser?.uid || localStorage.getItem('smartbids_uid');
    if (!targetUid) return;

    try {
        const resp = await fetch('/api/obtener-perfil/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid: targetUid })
        });
        const resData = await resp.json();

        if (resData.status === 'ok' && resData.datos) {
            const data = resData.datos;
            const emp = data.empresa || {};
            const pref = data.preferencias || {};

            const n1 = data.sus_nombre1 || '';
            const n2 = data.sus_nombre2 || '';
            const a1 = data.sus_apellido1 || '';
            const a2 = data.sus_apellido2 || '';
            const nombreCompleto = [n1, n2, a1, a2].filter(Boolean).join(' ') || 'Suscriptor';

            const fullNameHeader = document.getElementById('profile-fullname-header');
            if (fullNameHeader) fullNameHeader.textContent = nombreCompleto;

            const socialHeader = document.getElementById('profile-social-header');
            if (socialHeader) socialHeader.textContent = data.sus_nombre_social ? `@${data.sus_nombre_social}` : `@suscriptor_${data.id_suscriptor}`;

            const roleBadge = document.getElementById('profile-role-badge');
            if (roleBadge) roleBadge.textContent = data.nombre_estado || 'Activo';

            const initials = document.getElementById('profile-initials');
            if (initials) initials.textContent = data.sus_iniciales || (n1 && a1 ? (n1[0] + a1[0]).toUpperCase() : 'SB');

            const idSusc = document.getElementById('profile-id-suscriptor');
            if (idSusc) idSusc.textContent = data.id_suscriptor || '--';

            const uidHeader = document.getElementById('profile-uid-header');
            if (uidHeader) uidHeader.textContent = targetUid;

            const createdAt = document.getElementById('profile-created-at');
            if (createdAt) createdAt.textContent = formatTimestamp(data.fecha_registro);

            const lastLogin = document.getElementById('profile-last-login');
            if (lastLogin) lastLogin.textContent = formatTimestamp(data.fecha_actualizacion);

            const tokenId = document.getElementById('profile-token-id');
            if (tokenId) tokenId.textContent = data.token_sesion || SessionManager?.getLocalToken?.() || 'No asignado';

            const emailInput = document.getElementById('profile-email');
            if (emailInput) emailInput.value = user?.email || auth.currentUser?.email || '';

            // Datos Personales
            const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
            setVal('profile-nombre1', n1);
            setVal('profile-nombre2', n2);
            setVal('profile-apellido1', a1);
            setVal('profile-apellido2', a2);
            setVal('profile-nombre-social', data.sus_nombre_social);
            setVal('profile-iniciales', data.sus_iniciales);

            // Empresa
            setVal('empresa-rut', emp.emp_rut);
            setVal('empresa-fantasia', emp.emp_fantasia || emp.emp_nombre_fantasia);
            setVal('empresa-razon-social', emp.emp_razon_social);
            setVal('empresa-correo', emp.emp_contacto_correo);
            setVal('empresa-iniciales', emp.emp_iniciales);
            setVal('empresa-telefono', emp.emp_contacto_telefono);
            setVal('empresa-comuna', emp.emp_codigo_comuna);
            setVal('empresa-direccion', emp.emp_direccion);

            // Cargar Tags de Preferencias
            comunasManager.setItems(pref.comunas_detalle || []);
            productosManager.setItems(pref.productos_detalle || []);
            ucomManager.setItems(pref.ucom_detalle || []);

            setVal('pref-tipo-lic', Array.isArray(pref.pref_tipo_licitacion) ? pref.pref_tipo_licitacion.join(', ') : (pref.pref_tipo_licitacion || ''));
            setVal('pref-palabras', Array.isArray(pref.pref_palabras_claves) ? pref.pref_palabras_claves.join(', ') : (pref.pref_palabras_claves || ''));

            // Calcular porcentaje inicial tras volcar los datos
            actualizarPorcentajePerfil();
        }
    } catch (err) {
        console.error('[SmartBids] Error al cargar perfil:', err);
    }

    // Submit: Datos Personales
    const formDatos = document.getElementById('form-perfil-datos');
    if (formDatos && formDatos.dataset.bound !== 'true') {
        formDatos.dataset.bound = 'true';
        formDatos.onsubmit = async (e) => {
            e.preventDefault();
            const btn = formDatos.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Guardando...');
            try {
                const resp = await fetch('/api/actualizar-perfil/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        uid: targetUid,
                        sus_nombre1: document.getElementById('profile-nombre1')?.value || '',
                        sus_nombre2: document.getElementById('profile-nombre2')?.value || '',
                        sus_apellido1: document.getElementById('profile-apellido1')?.value || '',
                        sus_apellido2: document.getElementById('profile-apellido2')?.value || '',
                        sus_nombre_social: document.getElementById('profile-nombre-social')?.value || '',
                        sus_iniciales: document.getElementById('profile-iniciales')?.value || '',
                    })
                });
                const res = await resp.json();
                mostrarMensaje(res.mensaje, res.status === 'ok' ? 'exito' : 'error');
                actualizarPorcentajePerfil();
            } catch (err) {
                mostrarMensaje('Error de red al actualizar datos personales.', 'error');
            } finally {
                setButtonLoading(btn, false);
            }
        };
    }

    // Submit: Empresa
    const formEmpresa = document.getElementById('form-perfil-empresa');
    if (formEmpresa && formEmpresa.dataset.bound !== 'true') {
        formEmpresa.dataset.bound = 'true';
        formEmpresa.onsubmit = async (e) => {
            e.preventDefault();
            const btn = formEmpresa.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Guardando...');
            try {
                const resp = await fetch('/api/actualizar-empresa/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        uid: targetUid,
                        emp_rut: document.getElementById('empresa-rut')?.value || '',
                        emp_nombre_fantasia: document.getElementById('empresa-fantasia')?.value || '',
                        emp_razon_social: document.getElementById('empresa-razon-social')?.value || '',
                        emp_contacto_correo: document.getElementById('empresa-correo')?.value || '',
                        emp_iniciales: document.getElementById('empresa-iniciales')?.value || '',
                        emp_contacto_telefono: document.getElementById('empresa-telefono')?.value || '',
                        emp_codigo_comuna: document.getElementById('empresa-comuna')?.value || '',
                        emp_direccion: document.getElementById('empresa-direccion')?.value || '',
                    })
                });
                const res = await resp.json();
                mostrarMensaje(res.mensaje, res.status === 'ok' ? 'exito' : 'error');
                actualizarPorcentajePerfil();
            } catch (err) {
                mostrarMensaje('Error de conexión al guardar los datos de empresa.', 'error');
            } finally {
                setButtonLoading(btn, false);
            }
        };
    }

    // Submit: Filtros de Licitación
    const formFiltros = document.getElementById('form-perfil-preferencias');
    if (formFiltros && formFiltros.dataset.bound !== 'true') {
        formFiltros.dataset.bound = 'true';
        formFiltros.onsubmit = async (e) => {
            e.preventDefault();
            const btn = formFiltros.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Guardando...');

            const getArrayOrHidden = (manager, inputId) => {
                const codes = manager ? manager.getCodes() : [];
                if (codes.length > 0) return codes;
                const hiddenEl = document.getElementById(inputId);
                return hiddenEl && hiddenEl.value.trim() ? hiddenEl.value.split(',').map(s => s.trim()).filter(Boolean) : [];
            };

            const payload = {
                uid: targetUid,
                pref_comunas: getArrayOrHidden(comunasManager, 'pref-comunas'),
                pref_productos: getArrayOrHidden(productosManager, 'pref-productos'),
                pref_tipo_licitacion: document.getElementById('pref-tipo-lic').value.split(',').map(s => s.trim()).filter(Boolean),
                pref_ucom: getArrayOrHidden(ucomManager, 'pref-ucom'),
                pref_palabras_claves: document.getElementById('pref-palabras').value.split(',').map(s => s.trim()).filter(Boolean)
            };

            try {
                const resp = await fetch('/api/actualizar-preferencias/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const res = await resp.json();

                if (res.status === 'ok') {
                    mostrarMensaje(res.mensaje, 'exito');
                } else {
                    mostrarMensaje(`No se pudo guardar: ${res.mensaje}`, 'error');
                }
                actualizarPorcentajePerfil();
            } catch (err) {
                console.error('[SmartBids] Error de red:', err);
                mostrarMensaje('Error al conectar con el servidor Django.', 'error');
            } finally {
                setButtonLoading(btn, false);
            }
        };
    }
}

// Conexión de autenticación
auth.onAuthStateChanged((user) => {
    if (user) {
        localStorage.setItem('smartbids_uid', user.uid);
        document.cookie = `sb_firebase_uid=${user.uid}; path=/; max-age=604800; SameSite=Lax`;
        
        if (document.getElementById('form-perfil-preferencias')) {
            inicializarVistaPerfil(user);
        }
    }
});

// ==========================================================================
// CONTROL DEL MODAL DE COMPLETITUD (< 90%)
// ==========================================================================
const KEY_OMITIR_MODAL = 'smartbids_omitir_modal_perfil_hasta';

export function evaluarYMostrarModalPerfil(datosPerfil) {
    const modal = document.getElementById('modal-completar-perfil');
    if (!modal) return;

    // No mostrar si ya está en la vista de edición de perfil
    if (window.location.pathname.includes('/perfil')) return;

    // Control de no ser molesto: verificar si fue omitido recientemente (7 días)
    const omitidoHasta = localStorage.getItem(KEY_OMITIR_MODAL);
    if (omitidoHasta && Date.now() < Number(omitidoHasta)) {
        return;
    }

    const data = datosPerfil || {};
    const emp = data.empresa || {};
    const pref = data.preferencias || {};

    const faltantes = [];

    // 1. Suscriptor
    if (!data.sus_nombre1 || !data.sus_apellido1) faltantes.push('Nombres y apellidos del suscriptor');
    if (!data.sus_iniciales) faltantes.push('Iniciales del suscriptor');

    // 2. Empresa
    if (!emp.emp_rut) faltantes.push('RUT de la empresa');
    if (!emp.emp_fantasia && !emp.emp_nombre_fantasia) faltantes.push('Nombre de fantasía de la empresa');
    if (!emp.emp_razon_social) faltantes.push('Razón social');
    if (!emp.emp_contacto_correo) faltantes.push('Correo de notificaciones');
    if (!emp.emp_codigo_comuna) faltantes.push('Comuna de casa matriz');

    // 3. Ejes de licitación
    const countComunas = (pref.comunas_detalle || []).length;
    const countProds = (pref.productos_detalle || []).length;
    const countUcom = (pref.ucom_detalle || []).length;

    if (countComunas === 0) faltantes.push('Cobertura territorial (comunas)');
    if (countProds === 0) faltantes.push('Catálogo de productos (ONU)');
    if (countUcom === 0) faltantes.push('Organismos o unidades de compra');

    // Total ítems evaluados = 10
    const totalItems = 10;
    const itemsCompletados = totalItems - faltantes.length;
    const porcentaje = Math.max(0, Math.round((itemsCompletados / totalItems) * 100));

    // Si tiene 90% o más, no se muestra el modal
    if (porcentaje >= 90) return;

    // Llenar datos de la UI del Modal
    const txtPorcentaje = document.getElementById('modal-porcentaje-texto');
    const barra = document.getElementById('modal-barra-relleno');
    const listaUl = document.getElementById('lista-faltantes-perfil');

    if (txtPorcentaje) txtPorcentaje.textContent = `${porcentaje}%`;
    if (barra) {
        barra.style.width = `${porcentaje}%`;
        barra.style.backgroundColor = porcentaje < 40 ? '#e53e3e' : '#dd6b20';
    }

    if (listaUl) {
        listaUl.innerHTML = faltantes.slice(0, 4).map(f => `<li>${f}</li>`).join('');
        if (faltantes.length > 4) {
            listaUl.innerHTML += `<li>Y ${faltantes.length - 4} dato(s) adicional(es)...</li>`;
        }
    }

    // Configuración de botones de cierre con animación fluida de salida
    const cerrarModal = (diasPospuesto = 7) => {
        const tiempoMilisegundos = diasPospuesto * 24 * 60 * 60 * 1000;
        localStorage.setItem(KEY_OMITIR_MODAL, String(Date.now() + tiempoMilisegundos));

        modal.classList.remove('active');
        modal.classList.add('closing');
        setTimeout(() => {
            modal.classList.remove('closing');
            modal.style.display = 'none';
        }, 450);
    };

    const btnOmitir = document.getElementById('btn-omitir-completar-perfil');
    const btnX = document.getElementById('btn-cerrar-x-perfil');

    if (btnOmitir && !btnOmitir.dataset.bound) {
        btnOmitir.dataset.bound = 'true';
        btnOmitir.addEventListener('click', () => cerrarModal(7));
    }

    if (btnX && !btnX.dataset.bound) {
        btnX.dataset.bound = 'true';
        btnX.addEventListener('click', () => cerrarModal(3));
    }

    // ⏱️ Espera de 1 segundo (1000 ms) y entrada suave mediante requestAnimationFrame
    setTimeout(() => {
        modal.style.display = 'flex';
        modal.classList.remove('closing');

        // Permite que el navegador registre primero el display antes de activar la transición CSS
        requestAnimationFrame(() => {
            modal.classList.add('active');
        });
    }, 1000);
}