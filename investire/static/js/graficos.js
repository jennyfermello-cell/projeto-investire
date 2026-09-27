window.onload = loadData;

function loadData() {
    evolucao_aportes();
    distribuicao_por_ativo();
}

function evolucao_aportes() {
    fetch('/api/aportes_por_mes')
        .then(response => response.json())
        .then(dados => {
            const meses = Object.keys(dados);
            const valores = Object.values(dados);

            const ctx = document.getElementById('graficoEvolucao').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: meses,
                    datasets: [{
                        label: 'Total investido por mês (R$)',
                        data: valores,
                        backgroundColor: 'rgba(25, 135, 84, 0.15)',
                        borderColor: 'rgba(25, 135, 84, 1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#153623' } },
                        title: {
                            display: true,
                            text: 'Total investido por mês (R$)',
                            color: '#153623'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: '#153623' },
                            title: { display: true, text: 'Valor (R$)', color: '#153623' }
                        },
                        x: {
                            ticks: { color: '#153623' },
                            title: { display: true, text: 'Mês', color: '#153623' }
                        }
                    }
                }
            });
        })
        .catch(error => console.error("Erro ao carregar aportes por mês:", error));
}

function distribuicao_por_ativo() {
    fetch('/api/carteira_por_ativo')
        .then(response => response.json())
        .then(dados => {
            const ctx = document.getElementById('graficoDonut').getContext('2d');

            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(dados),
                    datasets: [{
                        label: 'Valor por ativo (R$)',
                        data: Object.values(dados),
                        backgroundColor: [
                            'rgba(25, 135, 84, 0.7)',
                            'rgba(13, 110, 253, 0.7)',
                            'rgba(255, 193, 7, 0.7)',
                            'rgba(220, 53, 69, 0.7)',
                            'rgba(111, 66, 193, 0.7)',
                            'rgba(253, 126, 20, 0.7)'
                        ],
                        borderColor: '#ffffff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#153623' }
                        }
                    },
                    layout: { padding: 20 }
                }
            });
        })
        .catch(error => console.error("Erro ao carregar distribuição por ativo:", error));
}