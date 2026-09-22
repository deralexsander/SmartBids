import { mostrarMensaje } from './mensaje.js';

// ==========================================================================
// 9. GESTIÓN DE ALERTAS (PANEL ADMIN CONECTADO A POSTGRESQL)
// ==========================================================================
const formMensajeria = document.getElementById('form-mensajeria');
const listaAlertasAdmin = document.getElementById('lista-alertas-admin');
const inputMsgId = document.getElementById('msg-id');
const selectEstado = document.getElementById('msg-estado');
const selectTipo = document.getElementById('msg-tipo');
const btnCancelar = document.getElementById('btn-cancelar-edicion');
const statusFeedback = document.getElementById('mensaje-status-feedback');

if (formMensajeria) {
    async function cargarListaAlertasAdmin() {
        if (!listaAlertasAdmin) return;

        try {
            const res = await fetch('/api/mensajeria/');
            if (!res.ok) throw new Error('Error al consultar alertas');
            const dataList = await res.json();

            listaAlertasAdmin.innerHTML = '';

            if (dataList.length === 0) {
                listaAlertasAdmin.innerHTML = `
                    <div class="mockup-item" style="justify-content: center; padding: 2rem; color: var(--gray-text);">
                        <p style="margin: 0; font-size: 0.95rem;">No hay alertas registradas actualmente en PostgreSQL.</p>
                    </div>
                `;
                return;
            }

            dataList.forEach((data) => {
                const id = data.id;
                const esActivo = data.estado === 'activo';
                const estadoTexto = esActivo ? 'Activo' : 'Inactivo';
                const tipoAlerta = data.tipoAlerta || 'alerta';

                let colorTipo = 'var(--muted-teal)';
                let bgTipo = 'rgba(92, 150, 136, 0.12)';
                if (tipoAlerta === 'precaucion') {
                    colorTipo = '#e53e3e';
                    bgTipo = '#fff5f5';
                } else if (tipoAlerta === 'alerta') {
                    colorTipo = '#d97706';
                    bgTipo = '#fffbeb';
                } else if (tipoAlerta === 'exito') {
                    colorTipo = 'var(--accent-green)';
                    bgTipo = 'rgba(30, 196, 152, 0.15)';
                }

                const item = document.createElement('div');
                item.className = 'mockup-item';
                item.style.cssText = 'display: flex; flex-direction: column; align-items: stretch; gap: 0.75rem; margin-bottom: 1rem; border-radius: 14px;';

                item.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;">
                        <div style="display: flex; align-items: center; gap: 0.6rem;">
                            <h4 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: var(--dark-green);">
                                ${data.asunto || 'Sin Asunto'}
                            </h4>
                            <span class="dash-badge" style="background: ${bgTipo}; color: ${colorTipo}; text-transform: uppercase; font-size: 0.75rem;">
                                ${tipoAlerta}
                            </span>
                        </div>
                        <span class="mockup-status" style="${esActivo ? 'background: rgba(30, 196, 152, 0.15); color: var(--dark-green);' : 'background: #edf2f7; color: var(--gray-text);'}">
                            ${estadoTexto}
                        </span>
                    </div>

                    <div class="mockup-info" style="margin: 0;">
                        <p style="color: var(--gray-text); font-size: 0.92rem; line-height: 1.5; margin: 0; word-break: break-word;">
                            ${data.cuerpo || ''}
                        </p>
                    </div>

                    <div style="display: flex; justify-content: flex-end; gap: 0.6rem; padding-top: 0.5rem; border-top: 1px solid var(--border-color);">
                        <button type="button" class="btn btn-outline btn-edit" style="padding: 0.4rem 0.9rem; font-size: 0.85rem;">
                            Editar
                        </button>
                        <button type="button" class="btn btn-delete" style="padding: 0.4rem 0.9rem; font-size: 0.85rem; background: #fff5f5; color: #e53e3e; border: 1.5px solid #feb2b2;">
                            Eliminar
                        </button>
                    </div>
                `;

                // Botón Editar
                item.querySelector('.btn-edit').addEventListener('click', () => {
                    inputMsgId.value = id;
                    document.getElementById('msg-asunto').value = data.asunto || '';
                    document.getElementById('msg-cuerpo').value = data.cuerpo || '';
                    if (selectEstado) selectEstado.value = data.estado || 'activo';
                    if (selectTipo) selectTipo.value = data.tipoAlerta || 'alerta';

                    if (btnCancelar) btnCancelar.hidden = false;
                    formMensajeria.scrollIntoView({ behavior: 'smooth' });
                });

                // Botón Eliminar
                const btnDelete = item.querySelector('.btn-delete');
                btnDelete.addEventListener('click', async (e) => {
                    e.preventDefault();

                    if (!btnDelete.dataset.confirming) {
                        btnDelete.dataset.confirming = "true";
                        btnDelete.textContent = "¿Confirmar?";
                        btnDelete.style.background = "#e53e3e";
                        btnDelete.style.color = "var(--white)";

                        setTimeout(() => {
                            btnDelete.dataset.confirming = "";
                            btnDelete.textContent = "Eliminar";
                            btnDelete.style.background = "#fff5f5";
                            btnDelete.style.color = "#e53e3e";
                        }, 4000);
                        return;
                    }

                    try {
                        btnDelete.disabled = true;
                        btnDelete.textContent = "Borrando...";

                        const res = await fetch(`/api/mensajeria/${id}/`, { method: 'DELETE' });
                        if (!res.ok) throw new Error('Error al borrar');

                        mostrarMensaje('Alerta eliminada correctamente.', 'exito');
                        cargarListaAlertasAdmin();
                    } catch (error) {
                        console.error('Error al eliminar mensaje en PostgreSQL:', error);
                        mostrarMensaje('No se pudo eliminar el mensaje.', 'error');
                        btnDelete.disabled = false;
                        btnDelete.textContent = "Eliminar";
                        btnDelete.style.background = "#fff5f5";
                        btnDelete.style.color = "#e53e3e";
                    }
                });

                listaAlertasAdmin.appendChild(item);
            });
        } catch (error) {
            console.error('Error al listar mensajes desde PostgreSQL:', error);
            listaAlertasAdmin.innerHTML = '<p style="color: #e53e3e; padding: 1rem;">Error al cargar alertas desde el servidor.</p>';
        }
    }

    formMensajeria.addEventListener('submit', async (e) => {
        e.preventDefault();

        const idActual = inputMsgId.value;
        const asunto = document.getElementById('msg-asunto').value.trim();
        const cuerpo = document.getElementById('msg-cuerpo').value.trim();
        const estado = selectEstado ? selectEstado.value : 'activo';
        const tipoAlerta = selectTipo ? selectTipo.value : 'alerta';

        const payload = {
            asunto: asunto,
            cuerpo: cuerpo,
            estado: estado,
            tipoAlerta: tipoAlerta
        };

        if (statusFeedback) {
            statusFeedback.style.display = 'inline-flex';
            statusFeedback.textContent = 'Guardando...';
        }

        try {
            const url = idActual ? `/api/mensajeria/${idActual}/` : '/api/mensajeria/';
            const metodo = idActual ? 'PUT' : 'POST';

            const res = await fetch(url, {
                method: metodo,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error('Error en el guardado');

            formMensajeria.reset();
            inputMsgId.value = '';

            if (btnCancelar) btnCancelar.hidden = true;

            if (statusFeedback) {
                statusFeedback.textContent = '¡Guardado con éxito!';
                setTimeout(() => { 
                    statusFeedback.textContent = ''; 
                    statusFeedback.style.display = 'none';
                }, 3000);
            }
            mostrarMensaje('Mensaje guardado correctamente en la base de datos.', 'exito');
            cargarListaAlertasAdmin();
        } catch (error) {
            console.error('Error al guardar mensaje en PostgreSQL:', error);
            if (statusFeedback) {
                statusFeedback.textContent = 'Error al guardar.';
            }
            mostrarMensaje('Error al guardar el mensaje.', 'error');
        }
    });

    if (btnCancelar) {
        btnCancelar.addEventListener('click', () => {
            formMensajeria.reset();
            inputMsgId.value = '';
            btnCancelar.hidden = true;
        });
    }

    cargarListaAlertasAdmin();
}


