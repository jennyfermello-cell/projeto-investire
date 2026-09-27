import os
import yfinance as yf
from flask import render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime
from investire import app, db
from investire.models import Usuario, Ativo, AtivoAgrupado, Grupo, Dica, curtidas_dica
from sqlalchemy import func


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    if 'usuario' in session:
        return redirect(url_for('home'))
    return render_template("landing.html")


@app.route("/dashboard")
@login_required
def home():
    """Painel inicial (dashboard)."""
    return render_template("dashboard.html")

@app.route("/carteira")
@login_required
def carteira():
    """Página com a tabela da carteira."""
    ativos_do_usuario = Ativo.query.filter_by(usuario_id=session.get('usuario_id')).all()
    for ativo in ativos_do_usuario:
        preco_real = obter_preco_atual(ativo.nome)
        if preco_real is not None:
            ativo.preco_atual = preco_real
    db.session.commit()

    valor_total = calcular_total_carteira()

    carteira_organizada = {}
    for ativo in ativos_do_usuario:
        if ativo.nome not in carteira_organizada:
            carteira_organizada[ativo.nome] = AtivoAgrupado(ativo.nome, ativo.preco_atual)
        carteira_organizada[ativo.nome].adicionar_aporte(ativo)

    return render_template("index.html",
                           ativos=list(carteira_organizada.values()),
                           valor_total=valor_total)


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/autenticar", methods=["POST"])
def autenticar():
    email = request.form.get("email")
    senha = request.form.get("senha")

    usuario = Usuario.query.filter_by(email=email).first()

    if usuario and usuario.verificar_senha(senha):
        session.permanent = True
        session['usuario_id'] = usuario.id
        session['usuario'] = usuario.email
        session['nome_usuario'] = usuario.nome
        flash(f"Seja bem-vindo(a), {usuario.nome}", category="success")
        return redirect(url_for("home"))

    flash("E-mail e/ou senha inválidos. Tente novamente!", category="danger")
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    flash("Você foi desconectado!", category="warning")
    return redirect('/')


@app.route("/cadastro_usuario", methods=["GET"])
def cadastro_usuario():
    return render_template("cadastro_usuario.html")


@app.route("/salvar_usuario", methods=["POST"])
def salvar_usuario():
    nome = request.form.get("nome")
    email = request.form.get("email")
    senha = request.form.get("senha")
    data_nascimento = request.form.get("data_nascimento")
    genero = request.form.get("genero")

    if nome and email and senha and data_nascimento and genero:
        emailExistente = Usuario.query.filter_by(email=email).first()
        if emailExistente:
            flash("E-mail já existente. Tente novamente, por favor.", category="danger")
            return render_template("cadastro_usuario.html")

        data_obj = datetime.strptime(data_nascimento, "%Y-%m-%d").date()
        usuario = Usuario(
            nome=nome,
            email=email,
            senha="",
            data_nascimento=data_obj,
            genero=genero
        )
        usuario.senha_criptografada = senha
        db.session.add(usuario)
        db.session.commit()
        flash("Usuário cadastrado com sucesso! Faça o login, por favor.", category="success")
        return render_template("login.html")

    flash("Erro ao cadastrar o usuário.", category="danger")
    return render_template("cadastro_usuario.html")


@app.route("/perfil")
@login_required
def perfil():
    usuario = Usuario.query.get(session.get('usuario_id'))
    return render_template("perfil.html", usuario=usuario)


@app.route("/atualizar_perfil", methods=["POST"])
def atualizar_perfil():
    nome = request.form.get("nome")
    email = request.form.get("email")
    data_nascimento = request.form.get("data_nascimento")
    genero = request.form.get("genero")
    foto = upload_imagem()

    if nome and email and data_nascimento and genero:
        usuario = Usuario.query.filter_by(id=session.get('usuario_id')).first()

        if foto is None:
            foto = usuario.foto

        data_obj = datetime.strptime(data_nascimento, "%Y-%m-%d").date()
        usuario.nome = nome
        usuario.email = email
        usuario.data_nascimento = data_obj
        usuario.genero = genero
        usuario.foto = foto

        session['nome_usuario'] = usuario.nome
        db.session.commit()

        flash("Perfil do usuário alterado com sucesso.", category="success")
        return render_template("perfil.html", usuario=usuario)

    flash("Erro ao atualizar o perfil do usuário.", category="danger")
    return redirect(url_for("home"))


@app.route("/lancamentos", methods=["GET"])
def lancar():
    return render_template("lancamentos.html", id=0, ativo=None)


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

    preco_atual_api = obter_preco_atual(nome) or 0.0

    if nome and preco_de_compra and qtd_comprada:
        ativo = Ativo.query.filter_by(id=id, usuario_id=session.get('usuario_id')).first()
        if ativo:
            ativo.nome = nome.upper().strip()
            ativo.preco_de_compra = float(preco_de_compra)
            ativo.preco_atual = preco_atual_api
            ativo.qtd_comprada = int(qtd_comprada)
            if data_compra:
                ativo.data_compra = data_compra
            flash("Ativo atualizado com sucesso!", category="success")
        else:
            novo = Ativo(nome=nome, preco_de_compra=preco_de_compra,
                         preco_atual=preco_atual_api, qtd_comprada=qtd_comprada,
                         usuario_id=session['usuario_id'], data_compra=data_compra)
            db.session.add(novo)
            flash("Ativo cadastrado com sucesso!", category="success")
        db.session.commit()
    else:
        flash("Erro ao salvar o ativo. Preencha todos os campos.", category="danger")

    return redirect(url_for("carteira"))

@app.route("/detalhes/<string:nome_ativo>")
@login_required
def detalhes_ativo(nome_ativo):
    nome_ativo = nome_ativo.upper().strip()
    lancamentos = Ativo.query.filter_by(nome=nome_ativo, usuario_id=session.get('usuario_id')).all()
    return render_template("detalhes_ativo.html", nome_ativo=nome_ativo, lancamentos=lancamentos)


@app.route("/editar/<int:id>")
@login_required
def exibir_edicao(id):
    ativo = Ativo.query.filter_by(id=id, usuario_id=session.get('usuario_id')).first()
    if ativo:
        return render_template("lancamentos.html", ativo=ativo, id=id)
    return redirect(url_for("carteira"))


@app.route("/excluir_ativo/<int:id>")
@login_required
def excluir_ativo(id):
    ativo = Ativo.query.filter_by(id=id, usuario_id=session.get('usuario_id')).first()
    if ativo:
        db.session.delete(ativo)
        db.session.commit()
        flash("Ativo excluído com sucesso!", category="success")
    else:
        flash("Ativo não encontrado.", category="danger")
    return redirect(url_for("carteira"))


@app.route("/dados_grafico")
@login_required
def dados_grafico():
    ativos_do_usuario = Ativo.query.filter_by(usuario_id=session.get('usuario_id')).all()
    for ativo in ativos_do_usuario:
        preco_real = obter_preco_atual(ativo.nome)
        if preco_real is not None:
            ativo.preco_atual = preco_real
    db.session.commit()

    valor_total = calcular_total_carteira()

    carteira_organizada = {}
    for ativo in ativos_do_usuario:
        if ativo.nome not in carteira_organizada:
            carteira_organizada[ativo.nome] = AtivoAgrupado(ativo.nome, ativo.preco_atual)
        carteira_organizada[ativo.nome].adicionar_aporte(ativo)

    dados = []
    for ativo in carteira_organizada.values():
        valor = ativo.calcular_total()
        porcentagem = ativo.calcular_porcentagem_ativo(valor_total)
        dados.append({"nome": ativo.nome, "valor": round(valor, 2),
                      "porcentagem": round(porcentagem, 2)})
    dados.sort(key=lambda x: x["valor"], reverse=True)
    return jsonify({"total": round(valor_total, 2), "ativos": dados})


# ---------- funções auxiliares ----------
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


def calcular_total_carteira():
    total_carteira = 0
    ativos_do_usuario = Ativo.query.filter_by(usuario_id=session.get('usuario_id')).all()
    for ativo in ativos_do_usuario:
        total_carteira += (ativo.preco_atual * ativo.qtd_comprada)
    return total_carteira


def upload_imagem():
    arquivo = request.files.get("foto")
    if arquivo:
        os.makedirs("investire/static/uploads", exist_ok=True)
        nome_seguro = secure_filename(arquivo.filename)
        caminho = os.path.join("investire/static/uploads", nome_seguro)
        arquivo.save(caminho)
        return f"uploads/{nome_seguro}"
    return None

@app.route("/grafico")
@login_required
def grafico():
    return render_template("grafico.html")

# ---------- GRUPOS ----------

@app.route("/grupos")
@login_required
def painel_grupos():
    """Lista todos os grupos que o usuário participa + opção de descobrir novos."""
    usuario_atual = Usuario.query.get(session.get('usuario_id'))
    todos_grupos = Grupo.query.order_by(Grupo.criado_em.desc()).all()
    return render_template("painel_grupos.html",
                           usuario=usuario_atual,
                           todos_grupos=todos_grupos)


@app.route("/criar_grupo", methods=["GET", "POST"])
@login_required
def criar_grupo():
    if request.method == "POST":
        nome = request.form.get("nome")
        descricao = request.form.get("descricao")

        if nome:
            novo = Grupo(nome=nome, descricao=descricao,
                         criador_id=session.get('usuario_id'))
            db.session.add(novo)
            db.session.flush()  # pega o ID antes do commit

            # criador entra automaticamente no grupo
            usuario = Usuario.query.get(session.get('usuario_id'))
            usuario.grupos.append(novo)
            db.session.commit()

            flash(f"Grupo '{nome}' criado com sucesso!", category="success")
            return redirect(url_for("ver_grupo", grupo_id=novo.id))

    return render_template("criar_grupo.html")


@app.route("/entrar_grupo/<int:grupo_id>")
@login_required
def entrar_grupo(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    usuario = Usuario.query.get(session.get('usuario_id'))

    if usuario not in grupo.membros:
        grupo.membros.append(usuario)
        db.session.commit()
        flash(f"Você entrou no grupo '{grupo.nome}'!", category="success")
    else:
        flash("Você já participa deste grupo.", category="info")

    return redirect(url_for("ver_grupo", grupo_id=grupo.id))


@app.route("/sair_grupo/<int:grupo_id>")
@login_required
def sair_grupo(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    usuario = Usuario.query.get(session.get('usuario_id'))

    if usuario in grupo.membros:
        grupo.membros.remove(usuario)
        db.session.commit()
        flash(f"Você saiu do grupo '{grupo.nome}'.", category="warning")

    return redirect(url_for("painel_grupos"))


@app.route("/grupo/<int:grupo_id>")
@login_required
def ver_grupo(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    usuario = Usuario.query.get(session.get('usuario_id'))

    # ordena dicas da mais recente para a mais antiga
    dicas = Dica.query.filter_by(grupo_id=grupo_id)\
                      .order_by(Dica.criado_em.desc()).all()

    return render_template("ver_grupo.html",
                           grupo=grupo, dicas=dicas, usuario=usuario)


# ---------- DICAS ----------

@app.route("/grupo/<int:grupo_id>/nova_dica", methods=["POST"])
@login_required
def nova_dica(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    usuario = Usuario.query.get(session.get('usuario_id'))

    if usuario not in grupo.membros:
        flash("Você precisa entrar no grupo para postar.", category="danger")
        return redirect(url_for("ver_grupo", grupo_id=grupo_id))

    titulo = request.form.get("titulo")
    conteudo = request.form.get("conteudo")
    ticker = request.form.get("ticker", "").upper().strip() or None
    preco_str = request.form.get("preco", "").strip()

    if titulo and conteudo:
        try:
            preco = float(preco_str) if preco_str else None
        except ValueError:
            preco = None

        nova = Dica(titulo=titulo, conteudo=conteudo, ticker=ticker,
                    preco=preco, autor_id=usuario.id, grupo_id=grupo.id)
        db.session.add(nova)
        db.session.commit()
        flash("Dica compartilhada!", category="success")
    else:
        flash("Preencha título e conteúdo.", category="danger")

    return redirect(url_for("ver_grupo", grupo_id=grupo_id))


@app.route("/curtir_dica/<int:dica_id>")
@login_required
def curtir_dica(dica_id):
    dica = Dica.query.get_or_404(dica_id)
    usuario = Usuario.query.get(session.get('usuario_id'))

    if usuario in dica.curtidas:
        dica.curtidas.remove(usuario)     
    else:
        dica.curtidas.append(usuario)     

    db.session.commit()
    return redirect(url_for("ver_grupo", grupo_id=dica.grupo_id))


@app.route("/excluir_dica/<int:dica_id>")
@login_required
def excluir_dica(dica_id):
    dica = Dica.query.get_or_404(dica_id)
    usuario = Usuario.query.get(session.get('usuario_id'))

    
    grupo = Grupo.query.get(dica.grupo_id)
    if dica.autor_id == usuario.id or grupo.criador_id == usuario.id:
        db.session.delete(dica)
        db.session.commit()
        flash("Dica excluída.", category="success")
    else:
        flash("Você não pode excluir esta dica.", category="danger")

    return redirect(url_for("ver_grupo", grupo_id=dica.grupo_id))

@app.route("/associar_grupo", methods=["GET", "POST"])
@login_required
def associar_grupo():
    if request.method == "POST":
        grupo_id = request.form.get("grupo_id")
        usuario_atual = Usuario.query.get(session.get('usuario_id'))
        grupo = Grupo.query.get(grupo_id)

        if usuario_atual and grupo:
            if grupo not in usuario_atual.grupos:
                usuario_atual.grupos.append(grupo)
                db.session.commit()
            return redirect(url_for("meus_grupos"))

    grupos_disponiveis = Grupo.query.all()
    return render_template("associar_grupo.html", grupos_disponiveis=grupos_disponiveis)


@app.route("/meus_grupos")
@login_required
def meus_grupos():
    usuario_atual = Usuario.query.get(session.get('usuario_id'))
    return render_template("meus_grupos.html", usuario=usuario_atual)


@app.route("/grupo/<int:grupo_id>/membros")
@login_required
def membros_grupo(grupo_id):
    grupo = Grupo.query.get(grupo_id)
    if grupo:
        return render_template("membros_grupo.html", grupo=grupo)
    return redirect(url_for("meus_grupos"))

# ---------- ESTATÍSTICAS ----------

@app.route("/estatisticas")
@login_required
def estatisticas():
    return render_template("estatisticas.html")


@app.route("/api/carteira_por_ativo")
@login_required
def api_carteira_por_ativo():
    """Retorna {ticker: valor_total} da carteira do usuário."""
    usuario_id = session.get('usuario_id')

    resultados = db.session.query(
        Ativo.nome,
        func.sum(Ativo.preco_atual * Ativo.qtd_comprada).label("total")
    ).filter(Ativo.usuario_id == usuario_id)\
     .group_by(Ativo.nome).all()

    dados = {r.nome: round(float(r.total or 0), 2) for r in resultados}
    return jsonify(dados)


@app.route("/api/aportes_por_mes")
@login_required
def api_aportes_por_mes():
    """Retorna a soma investida por mês (baseado em data_compra)."""
    usuario_id = session.get('usuario_id')

    ativos_usuario = Ativo.query.filter_by(usuario_id=usuario_id).all()

    # agrupa em Python (data_compra é String DD/MM/YYYY ou YYYY-MM-DD)
    por_mes = {}
    for ativo in ativos_usuario:
        data = ativo.data_compra or ""
        # tenta extrair YYYY-MM de "DD/MM/YYYY" ou "YYYY-MM-DD"
        mes = None
        if "/" in data:
            partes = data.split("/")
            if len(partes) == 3:
                mes = f"{partes[2]}-{partes[1]}"
        elif "-" in data:
            partes = data.split("-")
            if len(partes) >= 2:
                # se for "YYYY-MM-DD"
                if len(partes[0]) == 4:
                    mes = f"{partes[0]}-{partes[1]}"
                # se for "DD-MM-YYYY"
                elif len(partes[2]) == 4:
                    mes = f"{partes[2]}-{partes[1]}"

        if mes:
            valor = ativo.preco_de_compra * ativo.qtd_comprada
            por_mes[mes] = por_mes.get(mes, 0) + valor

    # ordena por mês
    ordenado = dict(sorted(por_mes.items()))
    return jsonify(ordenado)


@app.route("/api/quantidade_por_ativo")
@login_required
def api_quantidade_por_ativo():
    """Retorna a quantidade comprada de cada ativo (para o donut)."""
    usuario_id = session.get('usuario_id')

    resultados = db.session.query(
        Ativo.nome,
        func.sum(Ativo.qtd_comprada).label("total")
    ).filter(Ativo.usuario_id == usuario_id)\
     .group_by(Ativo.nome).all()

    dados = {r.nome: int(r.total or 0) for r in resultados}
    return jsonify(dados)

# ---------- QUADRO DE LÍDERES ----------

@app.route("/quadro_lideres")
@login_required
def quadro_lideres():
    """Ranking de engajamento: dicas publicadas + curtidas recebidas."""

    # 1. Total de dicas por autor
    dicas_por_autor = db.session.query(
        Dica.autor_id,
        func.count(Dica.id).label("total_dicas")
    ).group_by(Dica.autor_id).subquery()

    # 2. Total de curtidas RECEBIDAS por autor
    #    (curtidas_dica liga usuario_id → dica_id; aqui queremos
    #     contar quantas curtidas as dicas de cada autor receberam)
    curtidas_recebidas = db.session.query(
        Dica.autor_id,
        func.count(curtidas_dica.c.usuario_id).label("total_curtidas")
    ).join(curtidas_dica, Dica.id == curtidas_dica.c.dica_id) \
     .group_by(Dica.autor_id).subquery()

    # 3. Query final: junta tudo com Usuario
    #    Usamos OUTER JOIN porque um usuário pode não ter dicas nem curtidas
    ranking = db.session.query(
        Usuario,
        func.coalesce(dicas_por_autor.c.total_dicas, 0).label("total_dicas"),
        func.coalesce(curtidas_recebidas.c.total_curtidas, 0).label("total_curtidas"),
    ).outerjoin(dicas_por_autor, Usuario.id == dicas_por_autor.c.autor_id) \
     .outerjoin(curtidas_recebidas, Usuario.id == curtidas_recebidas.c.autor_id) \
     .all()

    # 4. Calcula pontuação em Python (mais legível que CASE WHEN no SQL)
    linhas = []
    for usuario, dicas, curtidas in ranking:
        pontuacao = (dicas * 10) + (curtidas * 3)
        if pontuacao > 0:  # ignora quem não interage
            linhas.append({
                "usuario": usuario,
                "dicas": dicas,
                "curtidas": curtidas,
                "pontuacao": pontuacao,
            })

    # 5. Ordena por pontuação (desempate por curtidas)
    linhas.sort(key=lambda x: (x["pontuacao"], x["curtidas"]), reverse=True)

    return render_template("quadro_lideres.html", ranking=linhas)

# ---------- DASHBOARD ----------

@app.route("/api/dados_dashboard")
@login_required
def api_dados_dashboard():
    usuario_id = session.get('usuario_id')

    # Métricas gerais
    ativos_do_usuario = Ativo.query.filter_by(usuario_id=usuario_id).all()

    # recalcula preços antes de somar
    for ativo in ativos_do_usuario:
        preco_real = obter_preco_atual(ativo.nome)
        if preco_real is not None:
            ativo.preco_atual = preco_real
    db.session.commit()

    total_investido = 0.0
    for ativo in ativos_do_usuario:
        total_investido += ativo.preco_de_compra * ativo.qtd_comprada

    total_atual = sum(a.preco_atual * a.qtd_comprada for a in ativos_do_usuario)

    ativos_distintos = len({a.nome for a in ativos_do_usuario})

    # Quantidade de dicas criadas pelo usuário
    total_dicas = Dica.query.filter_by(autor_id=usuario_id).count()

    # Quantidade de grupos em que participa
    usuario = Usuario.query.get(usuario_id)
    total_grupos = len(usuario.grupos) if usuario else 0

    # Distribuição por ativo (para o donut)
    por_ativo = {}
    for a in ativos_do_usuario:
        por_ativo[a.nome] = por_ativo.get(a.nome, 0) + (a.preco_atual * a.qtd_comprada)

    dados_ativo = [
        {"nome": k, "valor": round(v, 2)}
        for k, v in sorted(por_ativo.items(), key=lambda x: -x[1])
    ]

   
    aportes = {}
    for a in ativos_do_usuario:
        data = a.data_compra or ""
        mes = None
        if "/" in data:
            p = data.split("/")
            if len(p) == 3:
                mes = f"{p[2]}-{p[1]}"
        elif "-" in data:
            p = data.split("-")
            if len(p) >= 2:
                if len(p[0]) == 4:
                    mes = f"{p[0]}-{p[1]}"
                elif len(p[2]) == 4:
                    mes = f"{p[2]}-{p[1]}"
        if mes:
            aportes[mes] = aportes.get(mes, 0) + (a.preco_de_compra * a.qtd_comprada)

    aportes_ordenado = [{"mes": k, "valor": round(v, 2)} for k, v in sorted(aportes.items())]

   
    ultimos = Ativo.query.filter_by(usuario_id=usuario_id)\
                         .order_by(Ativo.id.desc()).limit(5).all()
    recentes = [{
        "nome": a.nome,
        "qtd": a.qtd_comprada,
        "preco_de_compra": round(a.preco_de_compra, 2),
        "preco_atual": round(a.preco_atual, 2),
        "variacao": round(a.calcular_variacao(), 2),
    } for a in ultimos]

    return jsonify({
        "total_investido": round(total_investido, 2),
        "total_atual": round(total_atual, 2),
        "ativos_distintos": ativos_distintos,
        "total_dicas": total_dicas,
        "total_grupos": total_grupos,
        "dados_ativo": dados_ativo,
        "aportes": aportes_ordenado,
        "recentes": recentes,
    })