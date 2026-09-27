window.onload = loadData;

function loadData() {
    carregar_dados_dashboard();
}

function fmtBRL(v) {
    return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function carregar_dados_dashboard() {
    fetch('/api/dados_dashboard')
        .then(r => r.json())
        .then(dados => {
            // 1. Cards
            document.getElementById('cardInvestido').innerText = fmtBRL(dados.total_investido);
            document.getElementById('cardAtual').innerText = fmtBRL(dados.total_atual);
            document.getElementById('cardAtivos').innerText = dados.ativos_distintos;
            document.getElementById('cardEngajamento').innerText =
                `${dados.total_dicas} / ${dados.total_grupos}`;

            // 2. Tabela
            const tbody = document.getElementById('tabelaRecentes');
            tbody.innerHTML = '';

            if (!dados.recentes || dados.recentes.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">
                    Nenhum ativo cadastrado ainda.</td></tr>`;
            } else {
                dados.recentes.forEach(a => {
                    const cor = a.variacao >= 0 ? 'text-success' : 'text-danger';
                    tbody.innerHTML += `
                        <tr>
                            <td><span class="badge bg-success">${a.nome}</span></td>
                            <td>${a.qtd}</td>
                            <td>${fmtBRL(a.preco_de_compra)}</td>
                            <td>${fmtBRL(a.preco_atual)}</td>
                            <td class="${cor} fw-bold">${a.variacao.toFixed(2)}%</td>
                        </tr>
                    `;
                });
            }

            // 3. Gráfico de linha (aportes)
            const ctxL = document.getElementById('graficoLinha').getContext('2d');
            new Chart(ctxL, {
                type: 'line',
                data: {
                    labels: dados.aportes.map(x => x.mes),
                    datasets: [{
                        label: 'Investido por mês (R$)',
                        data: dados.aportes.map(x => x.valor),
                        borderColor: 'rgba(40, 167, 69, 1)',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#153623' } } },
                    scales: {
                        y: { beginAtZero: true, ticks: { color: '#153623' } },
                        x: { ticks: { color: '#153623' } }
                    }
                }
            });

            // 4. Gráfico de donut (distribuição)
            const ctxD = document.getElementById('graficoDonut').getContext('2d');
            new Chart(ctxD, {
                type: 'doughnut',
                data: {
                    labels: dados.dados_ativo.map(x => x.nome),
                    datasets: [{
                        data: dados.dados_ativo.map(x => x.valor),
                        backgroundColor: [
                            'rgba(40, 167, 69, 0.7)',
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
                    }
                }
            });
        })
        .catch(erro => console.error('Erro ao carregar dashboard:', erro));
}