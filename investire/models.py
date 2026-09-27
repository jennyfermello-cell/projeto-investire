from datetime import datetime
from investire import db, bcrypt


membros_grupo = db.Table('membros_grupo',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('grupo_id', db.Integer, db.ForeignKey('grupos.id'), primary_key=True)
)

curtidas_dica = db.Table('curtidas_dica',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('dica_id', db.Integer, db.ForeignKey('dicas.id'), primary_key=True)
)


class Ativo(db.Model):
    __tablename__ = 'ativos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(20), nullable=False)
    preco_de_compra = db.Column(db.Float, nullable=False)
    preco_atual = db.Column(db.Float, nullable=False, default=0.0)
    qtd_comprada = db.Column(db.Integer, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_compra = db.Column(db.String(20), nullable=True)

    def __init__(self, nome=None, preco_de_compra=None, preco_atual=0.0,
                 qtd_comprada=None, usuario_id=None, data_compra=None, **kwargs):
        super().__init__(**kwargs)
        if nome is not None:
            self.nome = nome.upper().strip()
        if preco_de_compra is not None:
            self.preco_de_compra = float(preco_de_compra)
        if preco_atual is not None:
            self.preco_atual = float(preco_atual)
        if qtd_comprada is not None:
            self.qtd_comprada = int(qtd_comprada)
        if usuario_id is not None:
            self.usuario_id = usuario_id
        self.data_compra = data_compra if data_compra else datetime.now().strftime("%d-%m-%Y")

    def calcular_total(self):
        return self.qtd_comprada * self.preco_atual

    def calcular_preco_medio(self):
        return self.calcular_total() / self.qtd_comprada if self.qtd_comprada else 0

    def calcular_variacao(self):
        if self.preco_de_compra == 0:
            return 0.0
        return ((self.preco_atual - self.preco_de_compra) / self.preco_de_compra) * 100

    def calcular_porcentagem_ativo(self, total_carteira):
        if total_carteira == 0:
            return 0.0
        return ((self.preco_atual * self.qtd_comprada) / total_carteira) * 100

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "preco_de_compra": self.preco_de_compra,
            "qtd_comprada": self.qtd_comprada,
            "preco_atual": self.preco_atual,
            "usuario_id": self.usuario_id,
            "data_compra": self.data_compra
        }


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    genero = db.Column(db.String(20), nullable=False)
    foto = db.Column(db.String(200), nullable=True)

    ativos = db.relationship('Ativo', backref='ativo_usuario', lazy=True)
    grupos = db.relationship('Grupo', secondary=membros_grupo, backref='membros')

    @property
    def senha_criptografada(self):
        return self.senha

    @senha_criptografada.setter
    def senha_criptografada(self, senha_texto):
        self.senha = bcrypt.generate_password_hash(senha_texto).decode('utf-8')

    def verificar_senha(self, senha_texto):
        return bcrypt.check_password_hash(self.senha, senha_texto)

class AtivoAgrupado:
    def __init__(self, nome, preco_atual):
        self.nome = nome
        self.preco_atual = preco_atual
        self.qtd_total = 0
        self.custo_total_compra = 0.0

    def adicionar_aporte(self, ativo):
        self.qtd_total += ativo.qtd_comprada
        self.custo_total_compra += (ativo.preco_de_compra * ativo.qtd_comprada)

    def calcular_total(self):
        return self.qtd_total * self.preco_atual

    def calcular_preco_medio(self):
        if self.qtd_total > 0:
            return self.custo_total_compra / self.qtd_total
        return 0

    def calcular_variacao(self):
        p_medio = self.calcular_preco_medio()
        if p_medio == 0:
            return 0.0
        return ((self.preco_atual - p_medio) / p_medio) * 100

    def calcular_porcentagem_ativo(self, total_carteira):
        if total_carteira == 0:
            return 0.0
        return (self.calcular_total() / total_carteira) * 100


class Grupo(db.Model):
    __tablename__ = 'grupos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255))
    criador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.now)
    dicas = db.relationship('Dica', backref='grupo', lazy=True,
                            cascade='all, delete-orphan')

    def total_membros(self):
        return len(self.membros) 


class Dica(db.Model):
    __tablename__ = 'dicas'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    ticker = db.Column(db.String(20), nullable=True)   # ex.: "PETR4"
    preco = db.Column(db.Float, nullable=True)         # ex.: 32.50
    criado_em = db.Column(db.DateTime, default=datetime.now)

    autor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos.id'), nullable=False)

    # relacionamentos
    autor = db.relationship('Usuario', backref='dicas_criadas')
    curtidas = db.relationship('Usuario', secondary=curtidas_dica, backref='dicas_curtidas')

    def total_curtidas(self):
        return len(self.curtidas)