import { auth } from './firebase-config.js';
import { mostrarMensaje } from './mensaje.js';

const usersPage = document.getElementById('admin-users-section');
const usersTableBody = document.getElementById('admin-users-body');
const usersSearch = document.getElementById('admin-users-search');
const usersMessage = document.getElementById('admin-users-message');
const deleteUserModal = document.getElementById('delete-user-modal');
const deleteUserEmail = document.getElementById('delete-user-email');
const confirmDeleteButton = document.getElementById('btn-confirm-delete-user');
const cancelDeleteButton = document.getElementById('btn-cancel-delete-user');
const changeRoleModal = document.getElementById('change-role-modal');
const changeRoleUser = document.getElementById('change-role-user');
const changeRoleValue = document.getElementById('change-role-value');
const confirmChangeRoleButton = document.getElementById('btn-confirm-change-role');
const cancelChangeRoleButton = document.getElementById('btn-cancel-change-role');
let users = [];
let states = [];
let pendingDeleteUid = null;
let pendingRoleChange = null;

function adminHeaders() {
    const uid = auth.currentUser?.uid;
    return uid ? { 'X-Firebase-UID': uid } : {};
}

function setUsersMessage(text, type = 'info') {
    if (!usersMessage) return;
    usersMessage.textContent = text;
    usersMessage.style.color = type === 'error' ? '#c53030' : 'var(--gray-text)';
}

function formatDate(value) {
    if (!value) return '--';
    const date = new Date(value);
    if (isNaN(date.getTime())) return '--';

    return date.toLocaleString('es-CL', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

function renderUsers() {
    if (!usersTableBody) return;
    const term = (usersSearch?.value || '').trim().toLowerCase();
    const filtered = users.filter((user) => [
        user.email,
        user.uid,
        user.estado
    ].join(' ').toLowerCase().includes(term));

    usersTableBody.innerHTML = '';
    if (!filtered.length) {
        usersTableBody.innerHTML = '<tr><td colspan="6" style="padding: 2rem; text-align: center; color: var(--muted-teal);">No se encontraron usuarios.</td></tr>';
        return;
    }

    filtered.forEach((user) => {
        const row = document.createElement('tr');
        row.style.cssText = 'border-bottom: 1px solid var(--border-color); transition: background-color 0.2s ease;';
        const esAdmin = (user.estado || '').toLowerCase().includes('admin') || user.rol === 'admin';
        const estadoTexto = user.estado || (esAdmin ? 'Administrador' : 'Pendiente');
        const opcionesEstado = states.map((state) => `
            <option value="${state.codigo_estado}" ${String(state.codigo_estado) === String(user.codigo_estado) ? 'selected' : ''}>
                ${state.nombre_estado}
            </option>
        `).join('');

        row.innerHTML = `
            <!-- Usuario / Correo -->
            <td style="padding: 0.9rem 0.8rem; vertical-align: middle;">
                <div style="font-weight: 700; color: var(--dark-green); font-size: 0.9rem; word-break: break-all;">
                    ${user.email || 'Sin correo'}
                </div>
                <small style="color: ${user.emailVerified ? 'var(--accent-green)' : 'var(--muted-teal)'}; font-size: 0.75rem; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; margin-top: 2px;">
                    <i class="fa-solid ${user.emailVerified ? 'fa-check' : 'fa-circle-xmark'}"></i>
                    ${user.emailVerified ? 'Verificado' : 'No verificado'}
                </small>
            </td>

            <!-- Fecha de Registro -->
            <td style="padding: 0.9rem 0.8rem; vertical-align: middle; font-size: 0.82rem; color: var(--gray-text); white-space: nowrap;">
                <i class="fa-regular fa-calendar" style="color: var(--muted-teal); margin-right: 4px;"></i>
                ${formatDate(user.createdAt || user.fecha_creacion)}
            </td>

            <!-- Último Acceso -->
            <td style="padding: 0.9rem 0.8rem; vertical-align: middle; font-size: 0.82rem; color: var(--gray-text); white-space: nowrap;">
                <i class="fa-regular fa-clock" style="color: var(--muted-teal); margin-right: 4px;"></i>
                ${formatDate(user.lastLoginAt || user.ultima_conexion || user.fecha_acceso)}
            </td>

            <!-- Identificador (UID) -->
            <td style="padding: 0.9rem 0.8rem; vertical-align: middle;">
                <span style="font-family: monospace; font-size: 0.78rem; background: var(--light-bg); border: 1px solid var(--soft-mint); padding: 3px 6px; border-radius: 6px; color: var(--dark-green); display: inline-block;" title="${user.uid}">
                    ${user.uid ? user.uid.substring(0, 8) + '...' : '--'}
                </span>
            </td>

            <!-- Selector de Estado con ajuste visual limpio -->
            <td style="padding: 0.9rem 0.6rem; vertical-align: middle;">
                <div class="form-inline" style="max-width: 100%; margin: 0;">
                    <select class="user-role-select admin-user-state" data-uid="${user.uid}" ${user.codigo_estado === null ? 'disabled title="Cuenta sin registro en PostgreSQL"' : ''} style="width: 100%; padding: 0.5rem 0.7rem; border-radius: 10px; border: 1.5px solid var(--soft-mint); font-size: 0.85rem; outline: none; background-color: var(--white); color: var(--dark-green); font-weight: 600; cursor: ${user.codigo_estado === null ? 'not-allowed' : 'pointer'}; opacity: ${user.codigo_estado === null ? '0.65' : '1'};">
                        ${opcionesEstado || `<option selected>${estadoTexto}</option>`}
                    </select>
                </div>
            </td>

            <!-- Acciones -->
            <td style="padding: 0.9rem 0.8rem; vertical-align: middle; text-align: center; white-space: nowrap;">
                <button type="button" class="btn btn-outline btn-delete-user admin-user-delete" data-uid="${user.uid}" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; border-color: #feb2b2; color: #e53e3e; background: #fff5f5; border-radius: 8px;">
                    <i class="fa-regular fa-trash-can"></i>
                </button>
            </td>
        `;
        usersTableBody.appendChild(row);
    });
}

async function loadUsers() {
    setUsersMessage('Cargando usuarios...');
    try {
        const response = await fetch('/api/firebase/usuarios/', { headers: adminHeaders() });
        const data = await response.json();
        if (!response.ok) throw new Error(data.mensaje || 'No se pudieron cargar los usuarios.');
        users = data.usuarios || [];
        states = data.estados || [];
        renderUsers();
        setUsersMessage(`${users.length} usuario(s) encontrado(s).`);
    } catch (error) {
        setUsersMessage(error.message, 'error');
    }
}

async function updateUserState(uid, codigoEstado) {
    const response = await fetch('/api/firebase/usuarios/', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...adminHeaders() },
        body: JSON.stringify({ uid, codigo_estado: codigoEstado })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.mensaje || 'No se pudo actualizar el estado.');
    mostrarMensaje(data.mensaje, 'exito');
    await loadUsers();
}

function closeDeleteModal() {
    deleteUserModal?.classList.remove('active');
    pendingDeleteUid = null;
}

function openDeleteModal(user) {
    pendingDeleteUid = user.uid;
    if (deleteUserEmail) deleteUserEmail.textContent = user.email || user.uid;
    deleteUserModal?.classList.add('active');
}

function closeChangeRoleModal(restore = true) {
    if (restore && pendingRoleChange) {
        pendingRoleChange.select.value = pendingRoleChange.previousValue;
    }
    changeRoleModal?.classList.remove('active');
    pendingRoleChange = null;
}

function openChangeRoleModal(select) {
    const user = users.find((item) => item.uid === select.dataset.uid);
    const selectedOption = select.options[select.selectedIndex];
    pendingRoleChange = {
        select,
        uid: select.dataset.uid,
        previousValue: select.dataset.previousValue || String(user?.codigo_estado ?? select.value),
        nextValue: select.value
    };
    if (changeRoleUser) changeRoleUser.textContent = user?.email || select.dataset.uid;
    if (changeRoleValue) changeRoleValue.textContent = selectedOption?.textContent.trim() || 'nuevo estado';
    changeRoleModal?.classList.add('active');
}

async function deleteUser(uid) {
    const response = await fetch(`/api/firebase/usuarios/?uid=${encodeURIComponent(uid)}`, {
        method: 'DELETE',
        headers: { ...adminHeaders() }
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.mensaje || 'No se pudo eliminar el usuario.');
    mostrarMensaje(data.mensaje, 'exito');
    await loadUsers();
}

if (usersPage) {
    usersSearch?.addEventListener('input', renderUsers);
    usersTableBody?.addEventListener('change', async (event) => {
        if (!event.target.classList.contains('admin-user-state')) return;
        openChangeRoleModal(event.target);
    });
    usersTableBody?.addEventListener('click', async (event) => {
        const button = event.target.closest('.admin-user-delete');
        if (!button) return;
        const user = users.find((item) => item.uid === button.dataset.uid);
        if (user) openDeleteModal(user);
    });
    document.addEventListener('smartbids:admin-ready', loadUsers, { once: true });
}

usersTableBody?.addEventListener('mousedown', (event) => {
    if (event.target.classList.contains('admin-user-state')) {
        event.target.dataset.previousValue = event.target.value;
    }
});

confirmDeleteButton?.addEventListener('click', async () => {
    if (!pendingDeleteUid) return;
    confirmDeleteButton.disabled = true;
    confirmDeleteButton.textContent = 'Eliminando...';
    try {
        await deleteUser(pendingDeleteUid);
        closeDeleteModal();
    } catch (error) {
        setUsersMessage(error.message, 'error');
    } finally {
        confirmDeleteButton.disabled = false;
        confirmDeleteButton.textContent = 'Sí, eliminar';
    }
});

confirmChangeRoleButton?.addEventListener('click', async () => {
    if (!pendingRoleChange) return;
    const { uid, nextValue } = pendingRoleChange;
    confirmChangeRoleButton.disabled = true;
    confirmChangeRoleButton.textContent = 'Guardando...';
    try {
        await updateUserState(uid, nextValue);
        closeChangeRoleModal(false);
    } catch (error) {
        setUsersMessage(error.message, 'error');
        closeChangeRoleModal();
    } finally {
        confirmChangeRoleButton.disabled = false;
        confirmChangeRoleButton.textContent = 'Sí, cambiar';
    }
});

cancelDeleteButton?.addEventListener('click', closeDeleteModal);
cancelChangeRoleButton?.addEventListener('click', () => closeChangeRoleModal());
deleteUserModal?.addEventListener('click', (event) => {
    if (event.target === deleteUserModal) closeDeleteModal();
});
changeRoleModal?.addEventListener('click', (event) => {
    if (event.target === changeRoleModal) closeChangeRoleModal();
});