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

// Instancias globales
let comunasManager = null;
let productosManager = null;
let ucomManager = null;
let territoryData = null;
let productosData = null;
let ucomData = null;
let modoModalTerritorio = 'cobertura';

// ==========================================================================
// 1. CÁLCULO CENTRALIZADO Y SINCRONIZADO DE PROGRESO
// ==========================================================================
export function calcularMetricasPerfil(dataObj = null) {
    let suscriptorChecks = [];
    let empresaChecks = [];
    let filtrosChecks = [];
    const faltantes = [];

    if (dataObj) {
        const emp = dataObj.empresa || {};
        const pref = dataObj.preferencias || {};

        const checkSus1 = Boolean(dataObj.sus_nombre1?.trim());
        const checkSus2 = Boolean(dataObj.sus_apellido1?.trim());
        const checkSocial = Boolean(dataObj.sus_nombre_social?.trim() || dataObj.sus_nombre2?.trim() || dataObj.sus_apellido2?.trim());
        const checkInic = Boolean(dataObj.sus_iniciales?.trim());

        suscriptorChecks = [checkSus1, checkSus2, checkSocial, checkInic];

        if (!checkSus1 || !checkSus2) faltantes.push('Nombres y apellidos del suscriptor');

        const checkRut = Boolean(emp.emp_rut?.trim());
        const checkFantasia = Boolean((emp.emp_fantasia || emp.emp_nombre_fantasia)?.trim());
        const checkRazon = Boolean(emp.emp_razon_social?.trim());
        const checkCorreo = Boolean(emp.emp_contacto_correo?.trim());
        const checkComuna = Boolean(emp.emp_codigo_comuna);
        const checkExtra = Boolean(emp.emp_direccion?.trim() || emp.emp_contacto_telefono?.trim() || emp.emp_iniciales?.trim() || emp.emp_contacto_nombre?.trim());

        empresaChecks = [checkRut, checkFantasia, checkRazon, checkCorreo, checkComuna, checkExtra];

        if (!checkRut) faltantes.push('RUT de la empresa');
        if (!checkFantasia) faltantes.push('Nombre de fantasía de la empresa');
        if (!checkRazon) faltantes.push('Razón social');
        if (!checkCorreo) faltantes.push('Correo de notificaciones');
        if (!checkComuna) faltantes.push('Comuna de casa matriz');

        const countComunas = (pref.comunas_detalle || []).length;
        const countProds = (pref.productos_detalle || []).length;
        const countUcom = (pref.ucom_detalle || []).length;
        const tieneTipos = Array.isArray(pref.pref_tipo_licitacion) ? pref.pref_tipo_licitacion.length > 0 : Boolean(pref.pref_tipo_licitacion);
        const tienePalabras = Array.isArray(pref.pref_palabras_claves) ? pref.pref_palabras_claves.length > 0 : Boolean(pref.pref_palabras_claves);

        filtrosChecks = [
            countComunas > 0,
            countProds > 0,
            countUcom > 0,
            tieneTipos || tienePalabras
        ];

        if (countComunas === 0) faltantes.push('Cobertura territorial (comunas)');
        if (countProds === 0) faltantes.push('Catálogo de productos (ONU)');
        if (countUcom === 0) faltantes.push('Organismos o unidades de compra');
        if (!tieneTipos && !tienePalabras) faltantes.push('Tipos de licitación o palabras clave');

    } else {
        const checkVal = (id) => Boolean(document.getElementById(id)?.value?.trim());
        const avatarInitials = document.getElementById('profile-initials')?.textContent?.replace('--', '').trim();

        suscriptorChecks = [
            checkVal('profile-nombre1'),
            checkVal('profile-apellido1'),
            checkVal('profile-nombre-social') || checkVal('profile-nombre2') || checkVal('profile-apellido2'),
            Boolean(avatarInitials)
        ];

        empresaChecks = [
            checkVal('empresa-rut'),
            checkVal('empresa-fantasia'),
            checkVal('empresa-razon-social'),
            checkVal('empresa-correo'),
            checkVal('empresa-comuna'),
            checkVal('empresa-direccion') || checkVal('empresa-telefono') || checkVal('empresa-iniciales') || checkVal('empresa-contacto-nombre')
        ];

        const countComunas = comunasManager ? comunasManager.getCodes().length : 0;
        const countProductos = productosManager ? productosManager.getCodes().length : 0;
        const countUcom = ucomManager ? ucomManager.getCodes().length : 0;
        
        const tieneProcedimiento = document.querySelectorAll('input[name="pref_tipo_lic_check"]:checked').length > 0;
        const tienePalabras = checkVal('pref-palabras');

        filtrosChecks = [
            countComunas > 0,
            countProductos > 0,
            countUcom > 0,
            tieneProcedimiento || tienePalabras
        ];
    }

    const totalItems = [...suscriptorChecks, ...empresaChecks, ...filtrosChecks];
    const completados = totalItems.filter(Boolean).length;
    const porcentaje = Math.round((completados / totalItems.length) * 100);

    return { porcentaje, faltantes };
}

export function actualizarPorcentajePerfil() {
    const { porcentaje } = calcularMetricasPerfil(null);

    const barFill = document.getElementById('profile-progress-fill');
    const numberText = document.getElementById('profile-progress-number');
    const statusText = document.getElementById('profile-progress-status');

    if (!barFill || !numberText) return;

    barFill.style.width = `${porcentaje}%`;
    numberText.textContent = `${porcentaje}%`;

    if (porcentaje < 40) {
        barFill.style.backgroundColor = '#e53e3e';
        numberText.style.color = '#e53e3e';
        if (statusText) statusText.textContent = 'Perfil básico. Faltan datos esenciales de empresa o filtros.';
    } else if (porcentaje < 80) {
        barFill.style.backgroundColor = '#dd6b20';
        numberText.style.color = '#dd6b20';
        if (statusText) statusText.textContent = 'Perfil intermedio. Puedes afinar tus filtros de búsqueda y datos tributarios.';
    } else {
        barFill.style.backgroundColor = 'var(--accent-green)';
        numberText.style.color = 'var(--dark-green)';
        if (statusText) statusText.textContent = '¡Excelente! Perfil y filtros de licitación completamente calibrados.';
    }
}

// ==========================================================================
// 2. GESTOR DE TAGS / CHIPS
// ==========================================================================
class TagManager {
    constructor(containerId, hiddenInputId, placeholderText) {
        this.container = document.getElementById(containerId);
        this.hiddenInput = document.getElementById(hiddenInputId);
        this.placeholderText = placeholderText;
        this.items = new Map();
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

// ==========================================================================
// 3. ÁRBOLES JERÁRQUICOS (COBERTURA, PRODUCTOS ONU, UCOM)
// ==========================================================================
async function setupTerritoryTree() {
    const openBtnCobertura = document.getElementById('btn-ajustar-cobertura');
    const openBtnEmpresa = document.getElementById('btn-seleccionar-comuna-empresa');
    const inputLabelEmpresa = document.getElementById('empresa-comuna-label');
    const modal = document.getElementById('territory-modal');
    const tree = document.getElementById('territory-tree');
    const closeBtn = document.getElementById('btn-cerrar-cobertura');
    const closeX = document.getElementById('btn-cerrar-x');
    const saveBtn = document.getElementById('btn-guardar-cobertura');
    const searchInput = document.getElementById('territory-tree-search');
    const counter = document.getElementById('territory-counter');
    const modalTitle = document.getElementById('territory-modal-title');
    const modalDesc = document.getElementById('territory-modal-desc');

    if (!modal || !tree || !saveBtn) return;

    function closeModal() {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }

    function updateCounter() {
        const total = tree.querySelectorAll('.comuna-check:checked').length;
        if (counter) {
            counter.textContent = (modoModalTerritorio === 'empresa')
                ? (total > 0 ? '1 comuna seleccionada' : 'Selecciona 1 comuna')
                : `${total} comunas seleccionadas`;
        }
    }

    function updateParentState(node) {
        if (modoModalTerritorio === 'empresa') return;
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
        const esModoEmpresa = (modoModalTerritorio === 'empresa');
        const currentEmpresaCode = document.getElementById('empresa-comuna')?.value?.trim();
        const currentCodes = comunasManager ? comunasManager.getCodes() : [];
        const selectedSet = new Set(esModoEmpresa ? [currentEmpresaCode] : currentCodes.map(c => String(c).trim()));

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
                    const inputType = esModoEmpresa ? 'radio' : 'checkbox';
                    const nameAttr = esModoEmpresa ? 'name="comuna_empresa_radio"' : '';

                    comsHtml += `
                        <div class="tree-item-comuna" style="padding: 6px 10px; border-radius: 8px; border: 1px solid #f1f5f9; background: #ffffff; transition: all 0.2s ease;">
                            <label style="cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 0.88rem; width: 100%;">
                                <input type="${inputType}" ${nameAttr} class="comuna-check" value="${cod}" data-label="${c.nombre_comuna}" ${isChecked} style="accent-color: var(--accent-green); cursor: pointer;">
                                <span style="color: var(--dark-green); font-weight: 600;">${c.nombre_comuna}</span>
                                <small style="color: var(--muted-teal); font-size: 0.78rem; margin-left: auto;">(${cod})</small>
                            </label>
                        </div>
                    `;
                });

                provsHtml += `
                    <div class="tree-node tree-province" style="margin-top: 6px; border: 1px solid #eef2f6; border-radius: 8px; background: #fafbfc; overflow: hidden;">
                        <div class="tree-header tree-toggle-btn" data-target="prov-child-${provId}" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; cursor: pointer; user-select: none;">
                            <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; color: var(--dark-green); font-size: 0.9rem;">
                                <i class="fa-solid fa-chevron-right toggle-icon" style="font-size: 0.75rem; color: var(--muted-teal); transition: transform 0.2s ease;"></i>
                                <i class="fa-solid fa-folder" style="color: var(--soft-mint); font-size: 0.85rem;"></i>
                                <span>${prov.nombre_provincia}</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 6px;" onclick="event.stopPropagation();">
                                ${!esModoEmpresa ? `
                                    <label style="cursor: pointer; display: inline-flex; align-items: center; gap: 4px; font-size: 0.78rem; color: var(--muted-teal);">
                                        <input type="checkbox" class="province-check" style="accent-color: var(--accent-green);">
                                        <span>Todas</span>
                                    </label>` : ''}
                            </div>
                        </div>
                        <div id="prov-child-${provId}" class="tree-children" style="display: none; padding: 8px; border-top: 1px dashed #e2e8f0; background: #ffffff;">
                            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 6px;">
                                ${comsHtml}
                            </div>
                        </div>
                    </div>
                `;
            });

            html += `
                <div class="tree-node tree-region" style="margin-bottom: 12px; background: #ffffff; border-radius: 12px; border: 1.5px solid var(--soft-mint); box-shadow: 0 2px 8px rgba(0,0,0,0.02); overflow: hidden;">
                    <div class="tree-header tree-toggle-btn" data-target="reg-child-${regId}" style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: rgba(30, 196, 152, 0.05); cursor: pointer; user-select: none;">
                        <div style="display: flex; align-items: center; gap: 10px; font-weight: 800; color: var(--dark-green); font-size: 0.95rem;">
                            <i class="fa-solid fa-chevron-right toggle-icon" style="font-size: 0.8rem; color: var(--accent-green); transition: transform 0.2s ease;"></i>
                            <i class="fa-solid fa-map" style="color: var(--accent-green); font-size: 0.9rem;"></i>
                            <span>${reg.nombre_region}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;" onclick="event.stopPropagation();">
                            ${!esModoEmpresa ? `
                                <label style="cursor: pointer; display: inline-flex; align-items: center; gap: 5px; font-size: 0.82rem; font-weight: 700; color: var(--dark-green);">
                                    <input type="checkbox" class="region-check" style="accent-color: var(--accent-green);">
                                    <span>Seleccionar Región</span>
                                </label>` : ''}
                        </div>
                    </div>
                    <div id="reg-child-${regId}" class="tree-children" style="display: none; padding: 10px 12px; background: #ffffff;">
                        ${provsHtml}
                    </div>
                </div>
            `;
        });

        tree.innerHTML = html || '<p style="text-align: center; color: var(--muted-teal);">No se encontraron divisiones territoriales.</p>';

        tree.querySelectorAll('.tree-toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.dataset.target;
                const container = document.getElementById(targetId);
                const icon = btn.querySelector('.toggle-icon');
                if (!container) return;

                const estaOculto = (container.style.display === 'none' || container.style.display === '');
                container.style.display = estaOculto ? 'block' : 'none';
                if (icon) {
                    icon.style.transform = estaOculto ? 'rotate(90deg)' : 'rotate(0deg)';
                }
            });
        });

        if (!esModoEmpresa) {
            tree.querySelectorAll('.tree-region').forEach(regNode => {
                const check = regNode.querySelector(':scope > .tree-header input.region-check');
                if (check) {
                    check.addEventListener('change', () => {
                        regNode.querySelectorAll('.tree-children input[type="checkbox"]').forEach(c => {
                            c.checked = check.checked;
                            c.indeterminate = false;
                        });
                        tree.querySelectorAll('.tree-province').forEach(updateParentState);
                        updateCounter();
                    });
                }
            });

            tree.querySelectorAll('.tree-province').forEach(provNode => {
                const check = provNode.querySelector(':scope > .tree-header input.province-check');
                if (check) {
                    check.addEventListener('change', () => {
                        provNode.querySelectorAll('.tree-children input[type="checkbox"]').forEach(c => {
                            c.checked = check.checked;
                            c.indeterminate = false;
                        });
                        tree.querySelectorAll('.tree-province').forEach(updateParentState);
                        tree.querySelectorAll('.tree-region').forEach(updateParentState);
                        updateCounter();
                    });
                }
            });
        }

        tree.querySelectorAll('.comuna-check').forEach(check => {
            check.addEventListener('change', () => {
                if (!esModoEmpresa) {
                    tree.querySelectorAll('.tree-province').forEach(updateParentState);
                    tree.querySelectorAll('.tree-region').forEach(updateParentState);
                }
                updateCounter();
            });
        });

        if (!esModoEmpresa) {
            tree.querySelectorAll('.tree-province').forEach(updateParentState);
            tree.querySelectorAll('.tree-region').forEach(updateParentState);
        }
        updateCounter();
    }

    async function abrirModal(modo) {
        modoModalTerritorio = modo;
        modal.classList.add('active');
        modal.style.display = 'flex';
        modal.style.zIndex = '99999';

        if (modalTitle) {
            modalTitle.textContent = modo === 'empresa' ? 'Comuna Casa Matriz *' : 'Cobertura Geográfica';
        }
        if (modalDesc) {
            modalDesc.textContent = modo === 'empresa'
                ? 'Navega en el árbol territorial y selecciona la comuna donde opera la casa matriz de la empresa.'
                : 'Marca o desmarca regiones, provincias o comunas específicas para tus filtros.';
        }

        const codComunaEmpresa = document.getElementById('empresa-comuna')?.value?.trim() || '';

        try {
            const resp = await fetch(`/api/catalogos-preferencias/?tipo=territorio&comuna_empresa=${encodeURIComponent(codComunaEmpresa)}`);
            territoryData = await resp.json();
            renderTree(territoryData);
        } catch (err) {
            console.error('[SmartBids] Error al cargar datos de territorio:', err);
            tree.innerHTML = '<p style="color: #e53e3e; text-align: center;">Error al cargar datos territoriales.</p>';
        }
    }

    if (openBtnCobertura && openBtnCobertura.dataset.bound !== 'true') {
        openBtnCobertura.dataset.bound = 'true';
        openBtnCobertura.addEventListener('click', () => abrirModal('cobertura'));
    }

    if (openBtnEmpresa && openBtnEmpresa.dataset.bound !== 'true') {
        openBtnEmpresa.dataset.bound = 'true';
        openBtnEmpresa.addEventListener('click', () => {
            if (!openBtnEmpresa.disabled && openBtnEmpresa.style.cursor !== 'not-allowed') {
                abrirModal('empresa');
            }
        });
    }

    if (inputLabelEmpresa && inputLabelEmpresa.dataset.bound !== 'true') {
        inputLabelEmpresa.dataset.bound = 'true';
        inputLabelEmpresa.addEventListener('click', () => {
            const esBloqueado = inputLabelEmpresa.readOnly && (
                inputLabelEmpresa.style.cursor === 'not-allowed' ||
                inputLabelEmpresa.style.backgroundColor === 'rgb(241, 245, 249)' ||
                inputLabelEmpresa.style.backgroundColor === '#f1f5f9'
            );
            if (!esBloqueado) {
                abrirModal('empresa');
            }
        });
    }

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
                        const visible = !term || comNode.textContent.toLowerCase().includes(term);
                        comNode.style.display = visible ? 'block' : 'none';
                        if (visible && term) matchProv = true;
                    });
                    provNode.style.display = (!term || matchProv || provNode.textContent.toLowerCase().includes(term)) ? 'block' : 'none';
                    if (provNode.style.display === 'block') matchRegion = true;
                });
                regNode.style.display = (!term || matchRegion || regNode.textContent.toLowerCase().includes(term)) ? 'block' : 'none';
            });
        });
    }

    saveBtn.addEventListener('click', () => {
        if (modoModalTerritorio === 'empresa') {
            const checkedRadio = tree.querySelector('.comuna-check:checked');
            if (checkedRadio) {
                const cod = String(checkedRadio.value).trim();
                const nombre = checkedRadio.dataset.label || cod;

                const hiddenInput = document.getElementById('empresa-comuna');
                const labelInput = document.getElementById('empresa-comuna-label');
                if (hiddenInput) hiddenInput.value = cod;
                if (labelInput) labelInput.value = `${nombre} (${cod})`;
            }
        } else {
            const checkedComunas = [...tree.querySelectorAll('.comuna-check:checked')];
            const selected = checkedComunas.map(c => ({
                code: String(c.value).trim(),
                label: c.dataset.label || c.value
            }));
            if (comunasManager) {
                comunasManager.setItems(selected);
            }
        }
        actualizarPorcentajePerfil();
        closeModal();
    });
}

async function setupProductsTree() {
    const openBtn = document.getElementById('btn-ajustar-productos');
    const modal = document.getElementById('productos-modal');
    const tree = document.getElementById('productos-tree');
    const closeBtn = document.getElementById('btn-cerrar-productos');
    const closeX = document.getElementById('btn-cerrar-productos-x');
    const saveBtn = document.getElementById('btn-guardar-productos');
    const searchInput = document.getElementById('productos-tree-search');
    const searchLoader = document.getElementById('productos-search-loader');
    const counter = document.getElementById('productos-counter');

    if (!modal || !tree || !saveBtn) return;

    let searchDebounceTimer = null;

    function closeModal() {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }

    function updateCounter() {
        const total = tree.querySelectorAll('.prod-check:checked').length;
        if (counter) counter.textContent = `${total} productos seleccionados`;
    }

    function updateParentState(rubroNode) {
        const children = [...rubroNode.querySelectorAll('.tree-children input.prod-check')];
        if (!children.length) return;

        const checkedCount = children.filter(c => c.checked).length;
        const parentCheck = rubroNode.querySelector('.tree-header input.rubro-check');
        if (parentCheck) {
            parentCheck.checked = checkedCount === children.length;
            parentCheck.indeterminate = checkedCount > 0 && checkedCount < children.length;
        }
    }

    function renderTree(data) {
        const currentCodes = productosManager ? productosManager.getCodes() : [];
        const selectedSet = new Set(currentCodes.map(c => String(c).trim()));
        let html = '';

        (data.rubros || []).forEach(rubro => {
            const rubroId = `rubro-onu-${String(rubro.codigo_rubro || rubro.nombre_rubro).replace(/[^a-zA-Z0-9]/g, '_')}`;
            const prods = rubro.productos || [];
            let prodsHtml = '';

            prods.forEach(p => {
                const cod = String(p.codigo_producto).trim();
                const isChecked = selectedSet.has(cod) ? 'checked' : '';

                prodsHtml += `
                    <div class="tree-item-prod" style="padding: 6px 10px; border-radius: 6px; border: 1px solid #f1f5f9; background: #ffffff; margin-bottom: 4px; display: flex; align-items: center; transition: all 0.15s ease;">
                        <label style="cursor: pointer; display: flex; align-items: center; gap: 10px; font-size: 0.88rem; width: 100%;">
                            <input type="checkbox" class="prod-check" value="${cod}" data-label="${p.descripcion}" ${isChecked} style="accent-color: var(--accent-green); cursor: pointer; flex-shrink: 0;">
                            <span class="prod-desc" style="color: var(--dark-green); font-weight: 500; line-height: 1.3;">${p.descripcion}</span>
                            <small class="prod-code" style="color: var(--muted-teal); font-size: 0.8rem; margin-left: auto; white-space: nowrap; font-family: monospace;">[${cod}]</small>
                        </label>
                    </div>
                `;
            });

            html += `
                <div class="tree-node tree-rubro" style="margin-bottom: 10px; background: #ffffff; border-radius: 10px; border: 1.5px solid var(--soft-mint); box-shadow: 0 2px 6px rgba(0,0,0,0.02); overflow: hidden;">
                    <div class="tree-header tree-toggle-btn" data-target="${rubroId}" style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: rgba(30, 196, 152, 0.06); cursor: pointer; user-select: none;">
                        <div style="display: flex; align-items: center; gap: 10px; font-weight: 700; color: var(--dark-green); font-size: 0.93rem;">
                            <i class="fa-solid fa-chevron-right toggle-icon" style="font-size: 0.8rem; color: var(--accent-green); transition: transform 0.2s ease;"></i>
                            <i class="fa-solid fa-folder" style="color: var(--soft-mint); font-size: 0.95rem;"></i>
                            <span class="rubro-title">${rubro.nombre_rubro}</span>
                            <span class="rubro-badge-count" style="font-size: 0.75rem; background: #e2e8f0; color: #475569; padding: 2px 7px; border-radius: 10px; font-weight: 600;">${prods.length}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;" onclick="event.stopPropagation();">
                            <label style="cursor: pointer; display: inline-flex; align-items: center; gap: 5px; font-size: 0.8rem; font-weight: 700; color: var(--dark-green);">
                                <input type="checkbox" class="rubro-check" style="accent-color: var(--accent-green);">
                                <span>Marcar Todo</span>
                            </label>
                        </div>
                    </div>
                    <div id="${rubroId}" class="tree-children" style="display: none; padding: 10px 14px; background: #fafbfc; max-height: 320px; overflow-y: auto;">
                        ${prodsHtml}
                    </div>
                </div>
            `;
        });

        tree.innerHTML = html || '<p style="text-align: center; color: var(--muted-teal); padding: 2rem;">No se encontraron productos en el catálogo.</p>';

        tree.querySelectorAll('.tree-toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.dataset.target;
                const container = document.getElementById(targetId);
                const icon = btn.querySelector('.toggle-icon');
                if (!container) return;

                const estaOculto = (container.style.display === 'none' || container.style.display === '');
                container.style.display = estaOculto ? 'block' : 'none';
                if (icon) {
                    icon.style.transform = estaOculto ? 'rotate(90deg)' : 'rotate(0deg)';
                }
            });
        });

        tree.querySelectorAll('.tree-rubro').forEach(rubroNode => {
            const check = rubroNode.querySelector('.tree-header input.rubro-check');
            if (check) {
                check.addEventListener('change', () => {
                    rubroNode.querySelectorAll('.tree-children input.prod-check').forEach(c => {
                        c.checked = check.checked;
                    });
                    updateCounter();
                });
            }
        });

        tree.querySelectorAll('.prod-check').forEach(check => {
            check.addEventListener('change', () => {
                const rubroNode = check.closest('.tree-rubro');
                if (rubroNode) updateParentState(rubroNode);
                updateCounter();
            });
        });

        tree.querySelectorAll('.tree-rubro').forEach(updateParentState);
        updateCounter();
    }

    if (openBtn && openBtn.dataset.bound !== 'true') {
        openBtn.dataset.bound = 'true';
        openBtn.addEventListener('click', async () => {
            modal.classList.add('active');
            modal.style.display = 'flex';
            modal.style.zIndex = '99999';

            if (searchInput) searchInput.value = '';

            if (!productosData) {
                tree.innerHTML = `
                    <div style="text-align: center; color: var(--muted-teal); padding: 3rem;">
                        <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 1.8rem; color: var(--accent-green); margin-bottom: 0.8rem; display: block;"></i>
                        <span style="font-weight: 700; color: var(--dark-green);">Cargando catálogo completo de productos ONU...</span>
                    </div>
                `;

                try {
                    const resp = await fetch('/api/catalogos-preferencias/?tipo=productos_arbol');
                    productosData = await resp.json();
                    renderTree(productosData);
                } catch (err) {
                    console.error('[SmartBids] Error al cargar catálogo de productos:', err);
                    tree.innerHTML = '<p style="color: #e53e3e; text-align: center; padding: 2rem;">Error al cargar el catálogo de productos.</p>';
                }
            } else {
                renderTree(productosData);
            }
        });
    }

    closeBtn.addEventListener('click', closeModal);
    if (closeX) closeX.addEventListener('click', closeModal);

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchDebounceTimer);
            if (searchLoader) searchLoader.style.display = 'block';

            searchDebounceTimer = setTimeout(() => {
                const term = searchInput.value.toLowerCase().trim();

                tree.querySelectorAll('.tree-rubro').forEach(rubroNode => {
                    const titleText = rubroNode.querySelector('.rubro-title')?.textContent.toLowerCase() || '';
                    const matchRubroTitle = titleText.includes(term);

                    let prodsCoincidentes = 0;
                    rubroNode.querySelectorAll('.tree-item-prod').forEach(prodNode => {
                        const desc = prodNode.querySelector('.prod-desc')?.textContent.toLowerCase() || '';
                        const code = prodNode.querySelector('.prod-code')?.textContent.toLowerCase() || '';
                        const matchProd = !term || desc.includes(term) || code.includes(term);

                        prodNode.style.display = matchProd ? 'flex' : 'none';
                        if (matchProd) prodsCoincidentes++;
                    });

                    const debeMostrarRubro = !term || matchRubroTitle || prodsCoincidentes > 0;
                    rubroNode.style.display = debeMostrarRubro ? 'block' : 'none';

                    const childrenContainer = rubroNode.querySelector('.tree-children');
                    const toggleIcon = rubroNode.querySelector('.toggle-icon');

                    if (term && debeMostrarRubro && prodsCoincidentes > 0) {
                        if (childrenContainer) childrenContainer.style.display = 'block';
                        if (toggleIcon) toggleIcon.style.transform = 'rotate(90deg)';
                    } else if (!term) {
                        if (childrenContainer) childrenContainer.style.display = 'none';
                        if (toggleIcon) toggleIcon.style.transform = 'rotate(0deg)';
                    }
                });

                if (searchLoader) searchLoader.style.display = 'none';
            }, 120);
        });
    }

    saveBtn.addEventListener('click', () => {
        const checkedProds = [...tree.querySelectorAll('.prod-check:checked')];
        const selected = checkedProds.map(p => ({
            code: String(p.value).trim(),
            label: `${p.dataset.label} (${p.value})`
        }));

        if (productosManager) {
            productosManager.setItems(selected);
        }
        actualizarPorcentajePerfil();
        closeModal();
    });
}

// ==========================================================================
// ÁRBOL DE ENTIDADES PÚBLICAS Y UNIDADES DE COMPRA (UCOM) - CORREGIDO
// ==========================================================================
async function setupUcomTree() {
    const openBtn = document.getElementById('btn-ajustar-ucom');
    const modal = document.getElementById('ucom-modal');
    const tree = document.getElementById('ucom-tree');
    const closeBtn = document.getElementById('btn-cerrar-ucom');
    const closeX = document.getElementById('btn-cerrar-ucom-x');
    const saveBtn = document.getElementById('btn-guardar-ucom');
    const searchInput = document.getElementById('ucom-tree-search');
    const searchLoader = document.getElementById('ucom-search-loader');
    const counter = document.getElementById('ucom-counter');

    if (!modal || !tree || !saveBtn) return;

    let debounceTimer = null;

    function closeModal() {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }

    function updateCounter() {
        const total = tree.querySelectorAll('.ucom-check:checked').length;
        if (counter) counter.textContent = `${total} unidades seleccionadas`;
    }

    // Sincroniza el checkbox padre según el estado de sus hijos
    function updateParentState(node, childSelector, checkSelector) {
        const children = [...node.querySelectorAll(childSelector)];
        if (!children.length) return;

        const checkedCount = children.filter(c => c.checked).length;
        const parentCheck = node.querySelector(checkSelector);
        if (parentCheck) {
            parentCheck.checked = (checkedCount === children.length);
            parentCheck.indeterminate = (checkedCount > 0 && checkedCount < children.length);
        }
    }

    function renderTree(data) {
        const currentCodes = ucomManager ? ucomManager.getCodes() : [];
        const selectedSet = new Set(currentCodes.map(c => String(c).trim()));
        let html = '';

        (data.sectores || []).forEach(sec => {
            const secId = `sec-${String(sec.codigo_sector).replace(/[^a-zA-Z0-9]/g, '_')}`;
            let orgsHtml = '';

            (sec.organismos || []).forEach(org => {
                const orgId = `org-${String(org.codigo_organismo).replace(/[^a-zA-Z0-9]/g, '_')}`;
                let ucomsHtml = '';

                (org.unidades || []).forEach(u => {
                    const cod = String(u.codigo_ucom).trim();
                    const isChecked = selectedSet.has(cod) ? 'checked' : '';

                    ucomsHtml += `
                        <div class="tree-item-ucom" style="padding: 6px 10px; border-radius: 6px; border: 1px solid #f1f5f9; background: #ffffff; margin-bottom: 4px; display: flex; align-items: center; transition: all 0.15s ease;">
                            <label style="cursor: pointer; display: flex; align-items: center; gap: 10px; font-size: 0.88rem; width: 100%; margin: 0;">
                                <input type="checkbox" class="ucom-check" value="${cod}" data-label="${u.descripcion}" ${isChecked} style="accent-color: var(--accent-green); cursor: pointer; flex-shrink: 0; width: 16px; height: 16px;">
                                <span class="ucom-desc" style="color: var(--dark-green); font-weight: 500; line-height: 1.3;">${u.descripcion}</span>
                                <small class="ucom-code" style="color: var(--muted-teal); font-size: 0.8rem; margin-left: auto; white-space: nowrap; font-family: monospace;">[${cod}]</small>
                            </label>
                        </div>
                    `;
                });

                orgsHtml += `
                    <div class="tree-node tree-organismo" style="margin-top: 6px; border: 1px solid #eef2f6; border-radius: 8px; background: #fafbfc; overflow: hidden;">
                        <div class="tree-header tree-toggle-btn" data-target="${orgId}" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; cursor: pointer; user-select: none;">
                            <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; color: var(--dark-green); font-size: 0.9rem;">
                                <i class="fa-solid fa-chevron-right toggle-icon" style="font-size: 0.75rem; color: var(--muted-teal); transition: transform 0.2s ease;"></i>
                                <i class="fa-solid fa-building-columns" style="color: var(--muted-teal); font-size: 0.85rem;"></i>
                                <span class="org-title">${org.nombre_organismo}</span>
                                <span style="font-size: 0.75rem; background: #e2e8f0; color: #475569; padding: 2px 7px; border-radius: 10px; font-weight: 600;">${(org.unidades || []).length}</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 6px;" onclick="event.stopPropagation();">
                                <label style="cursor: pointer; display: inline-flex; align-items: center; gap: 4px; font-size: 0.78rem; color: var(--muted-teal); margin: 0;">
                                    <input type="checkbox" class="org-check" style="accent-color: var(--accent-green); cursor: pointer;">
                                    <span>Todas</span>
                                </label>
                            </div>
                        </div>
                        <div id="${orgId}" class="tree-children" style="display: none; padding: 8px; border-top: 1px dashed #e2e8f0; background: #ffffff;">
                            <div style="display: flex; flex-direction: column; gap: 4px;">
                                ${ucomsHtml}
                            </div>
                        </div>
                    </div>
                `;
            });

            html += `
                <div class="tree-node tree-sector" style="margin-bottom: 12px; background: #ffffff; border-radius: 12px; border: 1.5px solid var(--soft-mint); box-shadow: 0 2px 8px rgba(0,0,0,0.02); overflow: hidden;">
                    <div class="tree-header tree-toggle-btn" data-target="${secId}" style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: rgba(30, 196, 152, 0.05); cursor: pointer; user-select: none;">
                        <div style="display: flex; align-items: center; gap: 10px; font-weight: 800; color: var(--dark-green); font-size: 0.95rem;">
                            <i class="fa-solid fa-chevron-right toggle-icon" style="font-size: 0.8rem; color: var(--accent-green); transition: transform 0.2s ease;"></i>
                            <i class="fa-solid fa-landmark" style="color: var(--accent-green); font-size: 0.9rem;"></i>
                            <span class="sec-title">${sec.nombre_sector}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;" onclick="event.stopPropagation();">
                            <label style="cursor: pointer; display: inline-flex; align-items: center; gap: 5px; font-size: 0.82rem; font-weight: 700; color: var(--dark-green); margin: 0;">
                                <input type="checkbox" class="sec-check" style="accent-color: var(--accent-green); cursor: pointer;">
                                <span>Marcar Sector</span>
                            </label>
                        </div>
                    </div>
                    <div id="${secId}" class="tree-children" style="display: none; padding: 10px 12px; background: #ffffff;">
                        ${orgsHtml}
                    </div>
                </div>
            `;
        });

        tree.innerHTML = html || '<p style="text-align: center; color: var(--muted-teal); padding: 2rem;">No se encontraron organismos o unidades.</p>';

        // Acordeón / Despliegue de carpetas
        tree.querySelectorAll('.tree-toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.dataset.target;
                const container = document.getElementById(targetId);
                const icon = btn.querySelector('.toggle-icon');
                if (!container) return;

                const estaOculto = (container.style.display === 'none' || container.style.display === '');
                container.style.display = estaOculto ? 'block' : 'none';
                if (icon) {
                    icon.style.transform = estaOculto ? 'rotate(90deg)' : 'rotate(0deg)';
                }
            });
        });

        // Casilla Marcar Sector -> afecta a todos sus organismos y unidades
        tree.querySelectorAll('.tree-sector').forEach(secNode => {
            const check = secNode.querySelector(':scope > .tree-header input.sec-check');
            if (check) {
                check.addEventListener('change', () => {
                    secNode.querySelectorAll('.tree-children input[type="checkbox"]').forEach(c => {
                        c.checked = check.checked;
                        c.indeterminate = false;
                    });
                    updateCounter();
                });
            }
        });

        // Casilla "Todas" de un organismo -> afecta a sus unidades y actualiza al Sector
        tree.querySelectorAll('.tree-organismo').forEach(orgNode => {
            const check = orgNode.querySelector(':scope > .tree-header input.org-check');
            if (check) {
                check.addEventListener('change', () => {
                    orgNode.querySelectorAll('.tree-children input.ucom-check').forEach(c => {
                        c.checked = check.checked;
                    });
                    const secNode = orgNode.closest('.tree-sector');
                    if (secNode) {
                        updateParentState(secNode, '.tree-children input.ucom-check', ':scope > .tree-header input.sec-check');
                    }
                    updateCounter();
                });
            }
        });

        // Casilla de una unidad individual -> actualiza a su Organismo y a su Sector
        tree.querySelectorAll('.ucom-check').forEach(check => {
            check.addEventListener('change', () => {
                const orgNode = check.closest('.tree-organismo');
                if (orgNode) {
                    updateParentState(orgNode, '.tree-children input.ucom-check', ':scope > .tree-header input.org-check');
                }
                const secNode = check.closest('.tree-sector');
                if (secNode) {
                    updateParentState(secNode, '.tree-children input.ucom-check', ':scope > .tree-header input.sec-check');
                }
                updateCounter();
            });
        });

        // Sincronizar estados iniciales de casillas
        tree.querySelectorAll('.tree-organismo').forEach(o => {
            updateParentState(o, '.tree-children input.ucom-check', ':scope > .tree-header input.org-check');
        });
        tree.querySelectorAll('.tree-sector').forEach(s => {
            updateParentState(s, '.tree-children input.ucom-check', ':scope > .tree-header input.sec-check');
        });
        updateCounter();
    }

    if (openBtn && openBtn.dataset.bound !== 'true') {
        openBtn.dataset.bound = 'true';
        openBtn.addEventListener('click', async () => {
            modal.classList.add('active');
            modal.style.display = 'flex';
            modal.style.zIndex = '99999';

            if (searchInput) searchInput.value = '';

            if (!ucomData) {
                tree.innerHTML = `
                    <div style="text-align: center; color: var(--muted-teal); padding: 3rem;">
                        <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 1.8rem; color: var(--accent-green); margin-bottom: 0.8rem; display: block;"></i>
                        <span style="font-weight: 700; color: var(--dark-green);">Cargando catálogo oficial de organismos y unidades...</span>
                    </div>
                `;

                try {
                    const resp = await fetch('/api/catalogos-preferencias/?tipo=ucom_arbol');
                    const jsonRes = await resp.json();

                    if (!resp.ok || jsonRes.status === 'error') {
                        throw new Error(jsonRes.mensaje || `Error HTTP ${resp.status}`);
                    }

                    ucomData = jsonRes;
                    renderTree(ucomData);
                } catch (err) {
                    console.error('[SmartBids] Error al cargar unidades de compra:', err);
                    tree.innerHTML = `<p style="color: #e53e3e; text-align: center; padding: 2rem;">Error al cargar catálogo de unidades: ${err.message}</p>`;
                }
            } else {
                renderTree(ucomData);
            }
        });
    }

    closeBtn.addEventListener('click', closeModal);
    if (closeX) closeX.addEventListener('click', closeModal);

    // ======================================================================
    // BUSCADOR EN VIVO INTELIGENTE (HERENCIA JERÁRQUICA)
    // ======================================================================
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            if (searchLoader) searchLoader.style.display = 'block';

            debounceTimer = setTimeout(() => {
                const term = searchInput.value.toLowerCase().trim();

                tree.querySelectorAll('.tree-sector').forEach(secNode => {
                    const secTitle = secNode.querySelector('.sec-title')?.textContent.toLowerCase() || '';
                    const matchSector = term && secTitle.includes(term);
                    let secTieneHijosCoincidentes = false;

                    secNode.querySelectorAll('.tree-organismo').forEach(orgNode => {
                        const orgTitle = orgNode.querySelector('.org-title')?.textContent.toLowerCase() || '';
                        const matchOrganismo = term && orgTitle.includes(term);

                        let orgTieneUcomCoincidente = false;

                        orgNode.querySelectorAll('.tree-item-ucom').forEach(uNode => {
                            const desc = uNode.querySelector('.ucom-desc')?.textContent.toLowerCase() || '';
                            const code = uNode.querySelector('.ucom-code')?.textContent.toLowerCase() || '';
                            const matchUcom = !term || desc.includes(term) || code.includes(term);

                            // Si coincide el Sector o el Organismo, se muestran TODAS sus unidades
                            const visible = !term || matchSector || matchOrganismo || matchUcom;
                            uNode.style.display = visible ? 'flex' : 'none';

                            if (matchUcom && term) orgTieneUcomCoincidente = true;
                        });

                        const debeMostrarOrg = !term || matchSector || matchOrganismo || orgTieneUcomCoincidente;
                        orgNode.style.display = debeMostrarOrg ? 'block' : 'none';

                        if (debeMostrarOrg && term) secTieneHijosCoincidentes = true;

                        // Desplegar automáticamente si hay búsqueda activa
                        const orgChildren = orgNode.querySelector('.tree-children');
                        const orgIcon = orgNode.querySelector('.toggle-icon');
                        if (term && debeMostrarOrg) {
                            if (orgChildren) orgChildren.style.display = 'block';
                            if (orgIcon) orgIcon.style.transform = 'rotate(90deg)';
                        } else if (!term) {
                            if (orgChildren) orgChildren.style.display = 'none';
                            if (orgIcon) orgIcon.style.transform = 'rotate(0deg)';
                        }
                    });

                    const debeMostrarSector = !term || matchSector || secTieneHijosCoincidentes;
                    secNode.style.display = debeMostrarSector ? 'block' : 'none';

                    const secChildren = secNode.querySelector('.tree-children');
                    const secIcon = secNode.querySelector('.toggle-icon');
                    if (term && debeMostrarSector) {
                        if (secChildren) secChildren.style.display = 'block';
                        if (secIcon) secIcon.style.transform = 'rotate(90deg)';
                    } else if (!term) {
                        if (secChildren) secChildren.style.display = 'none';
                        if (secIcon) secIcon.style.transform = 'rotate(0deg)';
                    }
                });

                if (searchLoader) searchLoader.style.display = 'none';
            }, 120);
        });
    }

    // Botón "Aplicar Selección"
    saveBtn.addEventListener('click', () => {
        const checkedUcoms = [...tree.querySelectorAll('.ucom-check:checked')];
        const selected = checkedUcoms.map(u => ({
            code: String(u.value).trim(),
            label: `${u.dataset.label} (${u.value})`
        }));

        if (ucomManager) {
            ucomManager.setItems(selected);
        }
        actualizarPorcentajePerfil();
        closeModal();
    });
}

// ==========================================================================
// 4. SEGURIDAD Y SESIÓN
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
// 5. FUNCIONES DE APOYO PARA FORMULARIO DE EMPRESA
// ==========================================================================
function setFieldState(elementId, value, forceEditable = false) {
    const input = document.getElementById(elementId);
    if (!input) return;

    const tieneValor = value !== null && value !== undefined && String(value).trim() !== '';
    input.value = tieneValor ? String(value).trim() : '';

    const btnComuna = document.getElementById('btn-seleccionar-comuna-empresa');

    if (tieneValor && !forceEditable) {
        input.readOnly = true;
        input.style.backgroundColor = '#f1f5f9';
        input.style.cursor = 'not-allowed';
        input.title = 'Dato registrado oficialmente en el sistema. No modificable.';

        if (elementId === 'empresa-comuna-label' && btnComuna) {
            btnComuna.disabled = true;
            btnComuna.style.opacity = '0.5';
            btnComuna.style.cursor = 'not-allowed';
            btnComuna.style.pointerEvents = 'none';
        }
    } else {
        input.readOnly = (elementId === 'empresa-comuna-label');
        input.style.backgroundColor = '#ffffff';
        input.style.cursor = (elementId === 'empresa-comuna-label') ? 'pointer' : 'text';
        input.title = '';

        if (elementId === 'empresa-comuna-label' && btnComuna) {
            btnComuna.disabled = false;
            btnComuna.style.opacity = '1';
            btnComuna.style.cursor = 'pointer';
            btnComuna.style.pointerEvents = 'auto';
        }
    }
}

function limpiarCamposEmpresa() {
    const campos = [
        'empresa-fantasia',
        'empresa-razon-social',
        'empresa-contacto-nombre',
        'empresa-correo',
        'empresa-iniciales',
        'empresa-telefono',
        'empresa-comuna',
        'empresa-comuna-label',
        'empresa-direccion'
    ];
    campos.forEach(id => {
        setFieldState(id, '', true);
    });

    const btnComuna = document.getElementById('btn-seleccionar-comuna-empresa');
    if (btnComuna) {
        btnComuna.disabled = false;
        btnComuna.style.opacity = '1';
        btnComuna.style.cursor = 'pointer';
        btnComuna.style.pointerEvents = 'auto';
    }
}

function bloquearFormularioEmpresa() {
    const camposEmpresa = [
        'empresa-rut',
        'empresa-fantasia',
        'empresa-razon-social',
        'empresa-contacto-nombre',
        'empresa-correo',
        'empresa-iniciales',
        'empresa-telefono',
        'empresa-comuna',
        'empresa-comuna-label',
        'empresa-direccion'
    ];

    camposEmpresa.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.readOnly = true;
            el.style.backgroundColor = '#f1f5f9';
            el.style.cursor = 'not-allowed';
            el.title = 'Información consolidada y registrada en el sistema.';
        }
    });

    const btnComuna = document.getElementById('btn-seleccionar-comuna-empresa');
    if (btnComuna) {
        btnComuna.disabled = true;
        btnComuna.style.opacity = '0.5';
        btnComuna.style.cursor = 'not-allowed';
        btnComuna.style.pointerEvents = 'none';
    }

    const btnBuscar = document.getElementById('btn-buscar-rut-empresa');
    if (btnBuscar) {
        btnBuscar.disabled = true;
        btnBuscar.style.opacity = '0.5';
        btnBuscar.style.cursor = 'not-allowed';
    }

    const btnGuardar = document.getElementById('btn-guardar-empresa');
    if (btnGuardar) {
        btnGuardar.style.display = 'none';
    }
}

function actualizarInicialesSidebar() {
    const n1 = document.getElementById('profile-nombre1')?.value.trim() || '';
    const n2 = document.getElementById('profile-nombre2')?.value.trim() || '';
    const a1 = document.getElementById('profile-apellido1')?.value.trim() || '';
    const a2 = document.getElementById('profile-apellido2')?.value.trim() || '';

    const iniciales = [n1, n2, a1, a2]
        .filter(Boolean)
        .map(p => p[0].toUpperCase())
        .join('')
        .slice(0, 5);

    const avatarInitials = document.getElementById('profile-initials');
    if (avatarInitials) {
        avatarInitials.textContent = iniciales || '--';
    }
    return iniciales;
}

function autogenerarInicialesEmpresa() {
    const inputIniciales = document.getElementById('empresa-iniciales');
    if (!inputIniciales) return;

    if (inputIniciales.readOnly && inputIniciales.style.cursor === 'not-allowed') {
        return;
    }

    const fantasia = document.getElementById('empresa-fantasia')?.value.trim() || '';
    const razon = document.getElementById('empresa-razon-social')?.value.trim() || '';

    const baseTexto = fantasia || razon;
    if (!baseTexto) {
        inputIniciales.value = '';
        return;
    }

    const stopwords = new Set(['de', 'del', 'la', 'las', 'el', 'los', 'y', 'e', 'en', 'por', 'para', 'spa', 'sa', 's.a.', 'limitada', 'ltda', 'eirl']);

    const palabras = baseTexto
        .split(/\s+/)
        .map(p => p.replace(/[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]/g, ''))
        .filter(p => p.length > 0 && !stopwords.has(p.toLowerCase()));

    let siglas = '';
    if (palabras.length > 0) {
        siglas = palabras.map(p => p[0].toUpperCase()).join('').slice(0, 10);
    } else {
        siglas = baseTexto.slice(0, 3).toUpperCase();
    }

    inputIniciales.value = siglas;
}

function sanitizarPalabraClave(texto) {
    return (texto || '')
        .toLowerCase()
        .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9\s]/g, " ")
        .split(/\s+/)
        .filter(w => w.length > 1);
}

// ==========================================================================
// 6. INICIALIZADOR DE LA VISTA PERFIL
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

    setupTerritoryTree();
    setupProductsTree();
    setupUcomTree();
    setupPasswordFunctionality(user);
    setupLogoutButton();

    ['profile-nombre1', 'profile-nombre2', 'profile-apellido1', 'profile-apellido2'].forEach(id => {
        const el = document.getElementById(id);
        if (el && el.dataset.initBound !== 'true') {
            el.dataset.initBound = 'true';
            el.addEventListener('input', () => {
                actualizarInicialesSidebar();
                actualizarPorcentajePerfil();
            });
        }
    });

    ['empresa-fantasia', 'empresa-razon-social'].forEach(id => {
        const el = document.getElementById(id);
        if (el && el.dataset.siglasBound !== 'true') {
            el.dataset.siglasBound = 'true';
            el.addEventListener('input', () => {
                autogenerarInicialesEmpresa();
                actualizarPorcentajePerfil();
            });
        }
    });

    const inputEmpresaInic = document.getElementById('empresa-iniciales');
    if (inputEmpresaInic && inputEmpresaInic.dataset.capsBound !== 'true') {
        inputEmpresaInic.dataset.capsBound = 'true';
        inputEmpresaInic.addEventListener('input', (e) => {
            e.target.value = e.target.value.toUpperCase();
            actualizarPorcentajePerfil();
        });
    }

    ['form-perfil-datos', 'form-perfil-empresa', 'form-perfil-preferencias'].forEach(formId => {
        const f = document.getElementById(formId);
        if (f && f.dataset.listenerAttached !== 'true') {
            f.dataset.listenerAttached = 'true';
            f.addEventListener('input', actualizarPorcentajePerfil);
            f.addEventListener('change', actualizarPorcentajePerfil);
        }
    });

    document.querySelectorAll('input[name="pref_tipo_lic_check"]').forEach(cb => {
        cb.addEventListener('change', actualizarPorcentajePerfil);
    });

    // Sugeridor ortográfico reactivo
    const inputPalabras = document.getElementById('pref-palabras');
    const boxSugerencia = document.getElementById('palabras-sugerencia-box');
    const txtSugerencia = document.getElementById('palabra-sugerida-texto');

    if (inputPalabras && boxSugerencia && txtSugerencia && inputPalabras.dataset.suggestBound !== 'true') {
        inputPalabras.dataset.suggestBound = 'true';
        let debounceSugerencia = null;

        inputPalabras.addEventListener('input', () => {
            clearTimeout(debounceSugerencia);
            const textoCompleto = inputPalabras.value;
            const partes = textoCompleto.split(',');
            const palabraActual = partes[partes.length - 1].trim();

            if (palabraActual.length < 3) {
                boxSugerencia.style.display = 'none';
                return;
            }

            debounceSugerencia = setTimeout(async () => {
                try {
                    const resp = await fetch(`/api/catalogos-preferencias/?tipo=sugerir_palabra&q=${encodeURIComponent(palabraActual)}`);
                    const data = await resp.json();

                    if (data.status === 'ok' && data.sugerencia) {
                        const sug = String(data.sugerencia).toLowerCase();
                        if (sug !== palabraActual.toLowerCase()) {
                            txtSugerencia.textContent = sug;
                            boxSugerencia.style.display = 'block';
                            return;
                        }
                    }
                    boxSugerencia.style.display = 'none';
                } catch (e) {
                    console.error('[SmartBids] Error en sugeridor ortográfico:', e);
                }
            }, 250);
        });

        txtSugerencia.addEventListener('click', () => {
            const sugWord = txtSugerencia.textContent.trim();
            if (!sugWord) return;

            const partes = inputPalabras.value.split(',');
            partes[partes.length - 1] = ' ' + sugWord;
            
            inputPalabras.value = partes.map(p => p.trim()).filter(Boolean).join(', ') + ', ';
            boxSugerencia.style.display = 'none';
            inputPalabras.focus();
            actualizarPorcentajePerfil();
        });
    }

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

            const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
            setVal('profile-nombre1', n1);
            setVal('profile-nombre2', n2);
            setVal('profile-apellido1', a1);
            setVal('profile-apellido2', a2);
            setVal('profile-nombre-social', data.sus_nombre_social);

            setVal('empresa-rut', emp.emp_rut);
            setVal('empresa-fantasia', emp.emp_fantasia || emp.emp_nombre_fantasia);
            setVal('empresa-razon-social', emp.emp_razon_social);
            setVal('empresa-contacto-nombre', emp.emp_contacto_nombre);
            setVal('empresa-correo', emp.emp_contacto_correo);
            setVal('empresa-iniciales', emp.emp_iniciales);
            setVal('empresa-telefono', emp.emp_contacto_telefono);

            const codComuna = emp.emp_codigo_comuna || '';
            const nomComuna = emp.emp_nombre_comuna || '';
            const tieneComunaPrevia = Boolean(codComuna);

            setFieldState('empresa-comuna', codComuna, !tieneComunaPrevia);
            setFieldState('empresa-comuna-label', nomComuna ? `${nomComuna} (${codComuna})` : (codComuna ? `Comuna ${codComuna}` : ''), !tieneComunaPrevia);

            setVal('empresa-direccion', emp.emp_direccion);

            if (emp.emp_rut && String(emp.emp_rut).trim() !== '') {
                bloquearFormularioEmpresa();
            }

            comunasManager.setItems(pref.comunas_detalle || []);
            productosManager.setItems(pref.productos_detalle || []);
            ucomManager.setItems(pref.ucom_detalle || []);

            const tiposRecibidos = Array.isArray(pref.pref_tipo_licitacion)
                ? pref.pref_tipo_licitacion
                : (typeof pref.pref_tipo_licitacion === 'string'
                    ? pref.pref_tipo_licitacion.split(',').map(s => s.trim().toUpperCase())
                    : []);
            const tiposSet = new Set(tiposRecibidos.map(t => String(t).trim().toUpperCase()));

            document.querySelectorAll('input[name="pref_tipo_lic_check"]').forEach(checkbox => {
                checkbox.checked = tiposSet.has(checkbox.value.toUpperCase());
            });

            setVal('pref-palabras', Array.isArray(pref.pref_palabras_claves) ? pref.pref_palabras_claves.join(', ') : (pref.pref_palabras_claves || ''));

            actualizarPorcentajePerfil();
        }
    } catch (err) {
        console.error('[SmartBids] Error al cargar perfil:', err);
    }

    const formDatos = document.getElementById('form-perfil-datos');
    if (formDatos && formDatos.dataset.bound !== 'true') {
        formDatos.dataset.bound = 'true';
        formDatos.onsubmit = async (e) => {
            e.preventDefault();
            const btn = formDatos.querySelector('button[type="submit"]');
            setButtonLoading(btn, true, 'Guardando...');

            const autoInitials = actualizarInicialesSidebar();

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
                        sus_iniciales: autoInitials,
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

            const tiposSeleccionados = Array.from(document.querySelectorAll('input[name="pref_tipo_lic_check"]:checked'))
                .map(cb => cb.value);

            const rawPalabras = document.getElementById('pref-palabras')?.value || '';
            const tokens = rawPalabras.split(',').flatMap(p => sanitizarPalabraClave(p));
            const palabrasLimpias = [...new Set(tokens)];

            const payload = {
                uid: targetUid,
                pref_comunas: getArrayOrHidden(comunasManager, 'pref-comunas'),
                pref_productos: getArrayOrHidden(productosManager, 'pref-productos'),
                pref_tipo_licitacion: tiposSeleccionados,
                pref_ucom: getArrayOrHidden(ucomManager, 'pref-ucom'),
                pref_palabras_claves: palabrasLimpias
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
                    if (boxSugerencia) boxSugerencia.style.display = 'none';
                    document.getElementById('pref-palabras').value = (res.palabras_sanitizadas || palabrasLimpias).join(', ');
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

// ==========================================================================
// 7. EVENTOS DE EMPRESA Y MODAL DE CONFIRMACIÓN
// ==========================================================================
const btnBuscarRut = document.getElementById('btn-buscar-rut-empresa');
const inputRutEmpresa = document.getElementById('empresa-rut');

if (btnBuscarRut && inputRutEmpresa) {
    const ejecutarBusqueda = async () => {
        const rutValor = inputRutEmpresa.value.trim();
        if (!rutValor) {
            mostrarMensaje('Ingresa un RUT para buscar la empresa.', 'error');
            return;
        }

        btnBuscarRut.disabled = true;
        btnBuscarRut.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Buscando...';

        try {
            const resp = await fetch('/api/buscar-empresa-rut/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rut: rutValor })
            });
            const res = await resp.json();

            if (res.status === 'ok' && res.datos) {
                const datos = res.datos;

                inputRutEmpresa.value = datos.emp_rut || rutValor;
                inputRutEmpresa.readOnly = false;
                inputRutEmpresa.style.backgroundColor = '#ffffff';
                inputRutEmpresa.style.cursor = 'text';

                setFieldState('empresa-fantasia', datos.emp_nombre_fantasia);
                setFieldState('empresa-razon-social', datos.emp_razon_social);
                setFieldState('empresa-contacto-nombre', '');
                setFieldState('empresa-direccion', datos.emp_direccion);

                const codCom = (datos.emp_codigo_comuna || '').trim();
                const nomCom = (datos.emp_nombre_comuna || '').trim();
                const tieneComunaOficial = Boolean(codCom);
                const textoComuna = nomCom ? `${nomCom} (${codCom})` : (codCom ? `Comuna ${codCom}` : '');

                setFieldState('empresa-comuna', codCom, !tieneComunaOficial);
                setFieldState('empresa-comuna-label', textoComuna, !tieneComunaOficial);

                setFieldState('empresa-correo', datos.emp_contacto_correo);
                setFieldState('empresa-telefono', datos.emp_contacto_telefono);

                if (datos.emp_iniciales && datos.emp_iniciales.trim()) {
                    setFieldState('empresa-iniciales', datos.emp_iniciales);
                } else {
                    setFieldState('empresa-iniciales', '', true);
                    autogenerarInicialesEmpresa();
                }

                mostrarMensaje('Datos de empresa cargados con éxito.', 'exito');
            } else {
                limpiarCamposEmpresa();
                mostrarMensaje(
                    res.mensaje || 'Empresa no encontrada en los registros. Puedes ingresar los datos manualmente.',
                    'alerta'
                );
            }

            actualizarPorcentajePerfil();
        } catch (error) {
            console.error('[SmartBids] Error al consultar RUT:', error);
            mostrarMensaje('Error de conexión al consultar el RUT.', 'error');
        } finally {
            btnBuscarRut.disabled = false;
            btnBuscarRut.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Buscar por RUT';
        }
    };

    btnBuscarRut.addEventListener('click', ejecutarBusqueda);
    inputRutEmpresa.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            ejecutarBusqueda();
        }
    });
}

const modalConfirmEmpresa = document.getElementById('modal-confirmar-empresa');
const btnAceptarEmpresa = document.getElementById('btn-aceptar-modal-empresa');
const btnCancelarEmpresa = document.getElementById('btn-cancelar-modal-empresa');

function abrirModalConfirmEmpresa(rut, razon, fantasia) {
    if (!modalConfirmEmpresa) return;

    const elRut = document.getElementById('modal-confirm-rut');
    const elRazon = document.getElementById('modal-confirm-razon');
    const elFantasia = document.getElementById('modal-confirm-fantasia');

    if (elRut) elRut.textContent = rut;
    if (elRazon) elRazon.textContent = razon;
    if (elFantasia) elFantasia.textContent = fantasia;

    modalConfirmEmpresa.style.display = 'flex';
    modalConfirmEmpresa.classList.remove('closing');
    requestAnimationFrame(() => {
        modalConfirmEmpresa.classList.add('active');
    });
}

function cerrarModalConfirmEmpresa() {
    if (!modalConfirmEmpresa) return;

    modalConfirmEmpresa.classList.remove('active');
    modalConfirmEmpresa.classList.add('closing');
    setTimeout(() => {
        modalConfirmEmpresa.classList.remove('closing');
        modalConfirmEmpresa.style.display = 'none';
    }, 350);
}

if (btnCancelarEmpresa && !btnCancelarEmpresa.dataset.bound) {
    btnCancelarEmpresa.dataset.bound = 'true';
    btnCancelarEmpresa.addEventListener('click', cerrarModalConfirmEmpresa);
}

const formEmpresa = document.getElementById('form-perfil-empresa');

if (formEmpresa && formEmpresa.dataset.bound !== 'true') {
    formEmpresa.dataset.bound = 'true';

    formEmpresa.onsubmit = (e) => {
        e.preventDefault();

        const rut = document.getElementById('empresa-rut')?.value.trim();
        const razonSocial = document.getElementById('empresa-razon-social')?.value.trim();
        const fantasia = document.getElementById('empresa-fantasia')?.value.trim();
        const correo = document.getElementById('empresa-correo')?.value.trim();
        const comuna = document.getElementById('empresa-comuna')?.value.trim();

        if (!rut || !razonSocial || !fantasia || !correo || !comuna) {
            mostrarMensaje('Por favor completa todos los campos obligatorios de la empresa (*) incluyendo la Comuna Casa Matriz.', 'error');
            return;
        }

        abrirModalConfirmEmpresa(rut, razonSocial, fantasia);
    };
}

if (btnAceptarEmpresa && btnAceptarEmpresa.dataset.bound !== 'true') {
    btnAceptarEmpresa.dataset.bound = 'true';

    btnAceptarEmpresa.addEventListener('click', async () => {
        cerrarModalConfirmEmpresa();

        const formBtn = formEmpresa ? formEmpresa.querySelector('button[type="submit"]') : null;
        if (formBtn) setButtonLoading(formBtn, true, 'Guardando...');

        const targetUid = auth.currentUser?.uid || localStorage.getItem('smartbids_uid');

        try {
            const resp = await fetch('/api/actualizar-empresa/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    uid: targetUid,
                    emp_rut: document.getElementById('empresa-rut')?.value.trim() || '',
                    emp_nombre_fantasia: document.getElementById('empresa-fantasia')?.value.trim() || '',
                    emp_razon_social: document.getElementById('empresa-razon-social')?.value.trim() || '',
                    emp_contacto_nombre: document.getElementById('empresa-contacto-nombre')?.value.trim() || '',
                    emp_contacto_correo: document.getElementById('empresa-correo')?.value.trim() || '',
                    emp_iniciales: document.getElementById('empresa-iniciales')?.value.trim() || '',
                    emp_contacto_telefono: document.getElementById('empresa-telefono')?.value.trim() || '',
                    emp_codigo_comuna: document.getElementById('empresa-comuna')?.value.trim() || '',
                    emp_direccion: document.getElementById('empresa-direccion')?.value.trim() || '',
                })
            });
            const res = await resp.json();

            if (res.status === 'ok') {
                mostrarMensaje(res.mensaje || 'Empresa guardada con éxito.', 'exito');
                bloquearFormularioEmpresa();
            } else {
                mostrarMensaje(res.mensaje || 'Error al guardar la empresa.', 'error');
            }

            actualizarPorcentajePerfil();
        } catch (err) {
            mostrarMensaje('Error de conexión al guardar los datos de empresa.', 'error');
        } finally {
            if (formBtn) setButtonLoading(formBtn, false);
        }
    });
}

// ==========================================================================
// 8. ESCUCHA DE SESIÓN Y MODAL DE COMPLETITUD
// ==========================================================================
auth.onAuthStateChanged((user) => {
    if (user) {
        localStorage.setItem('smartbids_uid', user.uid);
        document.cookie = `sb_firebase_uid=${user.uid}; path=/; max-age=604800; SameSite=Lax`;

        if (document.getElementById('form-perfil-preferencias')) {
            inicializarVistaPerfil(user);
        }

        const currentPath = window.location.pathname.toLowerCase();
        if (currentPath.includes('/mis-licitaciones') || currentPath.includes('/dashboard')) {
            evaluarYMostrarModalPerfil();
        }
    }
});

const KEY_OMITIR_MODAL = 'smartbids_omitir_modal_perfil_hasta';

export async function evaluarYMostrarModalPerfil(datosPerfil) {
    const modal = document.getElementById('modal-completar-perfil');
    if (!modal) return;

    const currentPath = window.location.pathname.toLowerCase();
    const esRutaObjetivo = currentPath.includes('/mis-licitaciones') || currentPath.includes('/dashboard');
    if (!esRutaObjetivo) return;

    let UMBRAL_CONFIGURADO = 90;
    let DIAS_CONFIGURADOS = 7;

    try {
        const respParam = await fetch('/api/parametros/alerta-perfil/');
        const resParam = await respParam.json();
        if (resParam.status === 'ok' && resParam.datos) {
            UMBRAL_CONFIGURADO = Number(resParam.datos.porcentaje_minimo) || 90;
            DIAS_CONFIGURADOS = Number(resParam.datos.dias_reaparicion) || 7;
        }
    } catch (e) {
        console.warn('[SmartBids] No se pudieron obtener los parámetros globales de BD, usando respaldo.');
    }

    const txtUmbralReq = document.getElementById('modal-umbral-requerido-texto');
    if (txtUmbralReq) {
        txtUmbralReq.textContent = `${UMBRAL_CONFIGURADO}%`;
    }

    const omitidoHasta = localStorage.getItem(KEY_OMITIR_MODAL);
    if (omitidoHasta && Date.now() < Number(omitidoHasta)) {
        return;
    }

    let data = datosPerfil;
    if (!data) {
        const uid = localStorage.getItem('smartbids_uid') || auth.currentUser?.uid;
        if (!uid) return;

        try {
            const respPerfil = await fetch('/api/obtener-perfil/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ uid })
            });
            const resData = await respPerfil.json();
            if (resData.status === 'ok') {
                data = resData.datos;
            }
        } catch (err) {
            console.error('[SmartBids] Error al recuperar perfil para modal:', err);
            return;
        }
    }

    if (!data) return;

    const { porcentaje, faltantes } = calcularMetricasPerfil(data);

    if (porcentaje >= UMBRAL_CONFIGURADO) return;

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

    const cerrarModal = (dias = DIAS_CONFIGURADOS) => {
        const tiempoMilisegundos = dias * 24 * 60 * 60 * 1000;
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
        btnOmitir.addEventListener('click', () => cerrarModal(DIAS_CONFIGURADOS));
    }

    if (btnX && !btnX.dataset.bound) {
        btnX.dataset.bound = 'true';
        btnX.addEventListener('click', () => cerrarModal(Math.max(1, Math.round(DIAS_CONFIGURADOS / 2))));
    }

    setTimeout(() => {
        modal.style.display = 'flex';
        modal.classList.remove('closing');
        requestAnimationFrame(() => {
            modal.classList.add('active');
        });
    }, 1200);
}

// ==========================================================================
// 9. FUNCIÓN GLOBAL DE CONTROL DE PESTAÑAS
// ==========================================================================
export function cambiarPestana(event, tabId) {
    document.querySelectorAll('.profile-menu-btn').forEach((btn) => {
        btn.classList.remove('active');
    });

    document.querySelectorAll('.tab-content-panel').forEach((panel) => {
        panel.classList.remove('active');
    });

    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }

    const target = document.getElementById(tabId);
    if (target) {
        target.classList.add('active');
    }
}
window.cambiarPestana = cambiarPestana;