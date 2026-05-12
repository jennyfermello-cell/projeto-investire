import flask from Flask, render_template, request, url_for

app = Flask(__init__)
ativos = []

@app.route("/")
    return render_template("index.html", ativos=ativos)

@app.route("/lancamentos")
    return render_template ("lancamentos.html")

class Ativo:
    def __init__(self, name, qtd_total_comprada, preco_med, preco_atual):
        self.name = name,
        self.qtd_total = qtd_total_comprada,
        self.preco_med = preco_med,
        self.preco_atual = preco_atual

    def calcular_saldo(self):
        total = 0
        for ativo in ativos:
            total += ativo.preco_atual
        return total

    def calcular_rentabilidade(self):

    def calcular_qtd_total(self):
        