function cambiarDashboard(tabId, btn) {
    document.querySelectorAll('.dashboard-view').forEach((view) => {
        view.style.display = 'none';
    });
    document.querySelectorAll('.tab-dash-btn').forEach((button) => {
        button.classList.remove('active');
    });

    document.getElementById(tabId).style.display = 'block';
    btn.classList.add('active');
}

document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-dashboard-tab]');
    if (button) cambiarDashboard(button.dataset.dashboardTab, button);
});

document.addEventListener('DOMContentLoaded', () => {
    const graficoProductos = document.getElementById('graficoProductos');
    const graficoCompetencia = document.getElementById('graficoCompetencia');
    const graficoCompradores = document.getElementById('graficoCompradores');
    if (!window.Chart || !graficoProductos || !graficoCompetencia || !graficoCompradores) {
        console.error('No se pudo inicializar el dashboard: faltan Chart.js o los elementos de gráficos.');
        return;
    }

    new Chart(graficoProductos, {
        type: 'bar',
        data: {
            labels: ['Software & TI', 'Equipos Hardware', 'Consultoría', 'Servicios Cloud', 'Seguridad'],
            datasets: [{
                label: 'Cantidad de Licitaciones',
                data: [84, 52, 39, 61, 28],
                backgroundColor: '#1ec498',
                borderRadius: 6
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    new Chart(graficoCompetencia, {
        type: 'doughnut',
        data: {
            labels: ['Soluciones TI', 'TechCloud', 'Informatica Austral', 'Otros Oferentes'],
            datasets: [{
                data: [41, 28, 15, 16],
                backgroundColor: ['#11634e', '#1ec498', '#5c9688', '#b1d2ca']
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    new Chart(graficoCompradores, {
        type: 'bar',
        data: {
            labels: ['SUBTEL', 'Municipalidad de Valparaíso', 'Servicio de Salud Biobío', 'Ministerio de Hacienda', 'FONASA'],
            datasets: [{
                label: 'Presupuesto Licitado (en Millones CLP)',
                data: [450, 310, 280, 240, 200],
                backgroundColor: '#11634e',
                borderRadius: 6
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
});
