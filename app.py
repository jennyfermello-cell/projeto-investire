from datetime import datetime
import json 
import os
from flask import Flask, render_template, request, redirect, url_for, session
from classes import Ativo, Usuarios, AtivoAgrupado
from functools import wraps
from werkzeug.utils import secure_filename 
import yfinance as yf

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'static/uploads'

app.secret_key = 'chave_secreta'
app.permanent_session_lifetime = 3600

ativos = []
usuarios = []

try:
    with open("usuarios.json", "r") as arquivo:
        dados = json.load(arquivo)
        usuarios = [Usuarios(**usuario) for usuario in dados]
    with open("ativos.json", "r") as arquivo:
        dados = json.load(arquivo)
        ativos = [Ativo(**ativo) for ativo in dados]
except (FileNotFoundError, json.JSONDecodeError):
    usuarios = []
    ativos = []

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
     
@app.route("/")
@login_required
def home():
    usuario_id_atual = int(session.get('usuario_id', -1))
    ativos_do_usuario = [a for a in ativos if int(a.usuario_id) == usuario_id_atual]
    for ativo in ativos_do_usuario:
        preco_real = obter_preco_atual(ativo.nome)
        if preco_real and preco_real > 0:
            ativo.preco_atual = preco_real
        elif ativo.preco_atual == 0:
            ativo.preco_atual = float(ativo.preco_de_compra)
    valor_total = calcular_total_carteira()
    carteira_organizada = {}
    for ativo in ativos_do_usuario:
        if ativo.nome not in carteira_organizada:
            carteira_organizada[ativo.nome] = AtivoAgrupado(ativo.nome, ativo.preco_atual)
        carteira_organizada[ativo.nome].adicionar_aporte(ativo)
    lista_final = list(carteira_organizada.values())
    dados_grafico = []
    for ativo in lista_final:
        total_ativo = ativo.calcular_total()
        if total_ativo == 0 and ativo.qtd_total > 0:
            total_ativo = ativo.qtd_total * ativo.calcular_preco_medio()
        if total_ativo > 0:
            dados_grafico.append({
                "nome": ativo.nome, 
                "valor": float(total_ativo)
            })
    dados_grafico_json = json.dumps(dados_grafico)
    return render_template("index.html", ativos=lista_final, valor_total=valor_total, dados_grafico=dados_grafico_json)

@app.route("/login")
def login():
    return render_template("login.html", resultado=None)

@app.route("/autenticar", methods=["POST"])
def autenticar():
    email = request.form.get("email")
    senha = request.form.get("senha")

    for usuario in usuarios:
        if usuario.email == email and usuario.senha == senha:
            session.permanent = True
            session['usuario_id'] = int(usuario.id)
            session['usuario'] = usuario.email
            session['nome_usuario'] = usuario.nome
            return redirect(url_for("home"))
    return render_template("login.html", resultado="falha")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route("/cadastro_usuario", methods=["GET"])
def cadastro_usuario():
    return render_template("cadastro_usuario.html", resultado=None)

@app.route("/salvar_usuario", methods=["POST"])
def salvar_usuario():
    novo_id = max([usuario.id for usuario in usuarios], default=-1) + 1
    nome = request.form.get("nome")
    email = request.form.get("email")
    senha = request.form.get("senha")
    data_nascimento = request.form.get("data_nascimento")
    genero = request.form.get("genero")

    if nome and email and senha and data_nascimento and genero:
        for usuario in usuarios:
            if usuario.email == email:
                return render_template("cadastro_usuario.html", resultado="email_existe")
        usuarios.append(Usuarios(novo_id, nome, email, senha, data_nascimento, genero, foto=None))
        salvar_usuarios_json()
    return render_template("login.html", resultado="cadastrado")  

@app.route("/perfil")
@login_required
def perfil():
    usuario = [usuario for usuario in usuarios if usuario.id == session.get('usuario_id')]
    return render_template("perfil.html", usuario=usuario[0] if usuario else None)

@app.route("/atualizar_perfil", methods=["POST"])
def atualizar_perfil():
    nome = request.form.get("nome")
    email = request.form.get("email")
    data_nascimento = request.form.get("data_nascimento")
    genero = request.form.get("genero")
    foto = upload_imagem()

    if nome and email and data_nascimento and genero:
        if usuario := [usuario for usuario in usuarios if usuario.id == session.get('usuario_id')]:
            if foto is None:
                foto = usuario[0].foto
            usuario_atualizado = Usuarios(usuario[0].id, nome, email, usuario[0].senha, data_nascimento, genero, foto)
            usuarios[usuarios.index(usuario[0])] = usuario_atualizado
            session['nome_usuario'] = usuario_atualizado.nome
            salvar_usuarios_json()
            return render_template("perfil.html", usuario=usuario_atualizado, resultado="atualizado")
    return redirect(url_for("home"))      

def obter_preco_atual(ticker_nome):
    try:
        ticker_nome = ticker_nome.upper().strip()
        if not ticker_nome.endswith('.SA'):
            ticker_nome = f"{ticker_nome}.SA"
        ticker = yf.Ticker(ticker_nome)
        dados = ticker.history(period="1d")
        if not dados.empty:
            return float(dados['Close'].iloc[-1])
        return None
    except Exception as e:
        print(f"Erro ao buscar cotação de {ticker_nome}: {e}")
        return None

#total dos preços dos ativos
def calcular_total_carteira(): 
    total_carteira = 0
    usuario_id_atual = int(session.get('usuario_id', -1))
    ativos_do_usuario = [a for a in ativos if int(a.usuario_id) == usuario_id_atual]
    for ativo in ativos_do_usuario:
        total_carteira += (ativo.preco_atual * ativo.qtd_comprada) 
    return total_carteira

@app.route("/lancamentos", methods=["GET"])
@login_required
def lancar():
    novo_id=max([ativo.id for ativo in ativos], default=-1) +1
    return render_template("lancamentos.html", id = novo_id, ativo=None)

@app.route("/salvar_ativo/<int:id>", methods=["POST"])
@login_required
def salvar_ativo(id):
    nome = request.form.get("nome")
    preco_de_compra = request.form.get("preco_de_compra")
    qtd_comprada = request.form.get("qtd_comprada")
    data_compra = request.form.get("data_compra")

    if data_compra:
        try:
            data_compra = datetime.strptime(data_compra, '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            pass

    preco_atual_api = obter_preco_atual(nome)
    if preco_atual_api is None:
        preco_atual_api = 0.0

    if nome and preco_de_compra and qtd_comprada:
        if ativo := [ativo for ativo in ativos if ativo.id == id]:
            data_final = data_compra if data_compra else ativo[0].data_compra
            ativos[ativos.index(ativo[0])] = Ativo(id, nome, preco_de_compra, preco_atual_api, qtd_comprada, session['usuario_id'], data_final)
        else:
            novo_id = max([ativo.id for ativo in ativos], default=-1) + 1
            ativos.append(Ativo(novo_id, nome, preco_de_compra, preco_atual_api, qtd_comprada, session['usuario_id'], data_compra))
        salvar_ativos_json()
    return redirect(url_for("home"))

@app.route("/detalhes/<string:nome_ativo>")
@login_required
def detalhes_ativo(nome_ativo):
    nome_ativo = nome_ativo.upper().strip()
    lancamentos = [a for a in ativos if a.nome == nome_ativo and a.usuario_id == session.get('usuario_id')]
    return render_template("detalhes_ativo.html", nome_ativo=nome_ativo, lancamentos=lancamentos)

@app.route("/editar/<int:id>")
@login_required
def exibir_edicao(id):
    ativo = [ativo for ativo in ativos if ativo.id == id and ativo.usuario_id == session.get('usuario_id')]
    if ativo:
        return render_template("lancamentos.html", ativo=ativo[0], id=id, resultado=None)
    return redirect(url_for("home"))

@app.route("/excluir_ativo/<int:id>")
@login_required
def excluir_ativo(id):
    ativo = [ativo for ativo in ativos if ativo.id == id]
    if ativo:
        ativos.remove(ativo[0])
        salvar_ativos_json()
    return redirect(url_for("home"))

#json
def ler_ativos_usuario():
    try:
        with open("ativos.json", "r") as arquivo:
            dados = json.load(arquivo)
            return [Ativo(**ativo) for ativo in dados if ativo["usuario_id"] == session.get('usuario_id')]
    except (FileNotFoundError):
        return []    

def salvar_usuarios_json():
    with open("usuarios.json", "w") as arquivo:
        json.dump([usuario.to_dict() for usuario in usuarios], arquivo)

def salvar_ativos_json():
    with open("ativos.json", "w") as arquivo:
        json.dump([ativo.to_dict() for ativo in ativos], arquivo)

#imagem
def upload_imagem():
    arquivo = request.files.get("foto")
    
    if arquivo:
        nome_seguro = secure_filename(arquivo.filename)
        caminho = os.path.join("static/uploads", nome_seguro) 
        arquivo.save(caminho)
        return caminho.replace('\\', '/')
    return None