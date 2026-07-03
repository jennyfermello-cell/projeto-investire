from datetime import datetime

class Ativo:
    def __init__(self, id, nome, preco_de_compra, preco_atual, qtd_comprada, usuario_id, data_compra=None):
        self.id = id
        self.nome = nome.upper().strip()
        self.preco_de_compra = float(preco_de_compra)
        self.preco_atual = float(preco_atual)
        self.qtd_comprada = int(qtd_comprada)  
        self.usuario_id = usuario_id
        self.data_compra = data_compra if data_compra else datetime.now().strftime("%Y-%m-%d")

    def calcular_total(self):
        return self.qtd_comprada*self.preco_atual

    def calcular_preco_medio(self):  
        custo_total_compra = self.qtd_comprada * self.preco_de_compra
        pre_med = custo_total_compra / self.qtd_comprada
        return pre_med

    def calcular_variacao(self):
        if self.preco_de_compra == 0:
            return 0.0
        return ((self.preco_atual - self.preco_de_compra) / self.preco_de_compra) * 100

    def calcular_porcentagem_ativo(self, total_carteira): #cada ativo
        if total_carteira == 0:
            porc_ativo = 0 
            return porc_ativo
        else: 
            porc_ativo = ((self.preco_atual * self.qtd_comprada) / total_carteira) * 100
            return porc_ativo

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
        else:
            return 0

    def calcular_variacao(self):
        p_medio = self.calcular_preco_medio()
        if p_medio == 0: return 0.0
        return ((self.preco_atual - p_medio) / p_medio) * 100

    def calcular_porcentagem_ativo(self, total_carteira):
        if total_carteira == 0: return 0.0
        return (self.calcular_total() / total_carteira) * 100

class Usuarios:
    def __init__(self,id,nome, email,senha,data_nascimento, genero, foto):
        self.id = id
        self.nome = nome
        self.email = email
        self.senha = senha
        self.data_nascimento = data_nascimento
        self.genero = genero
        self.foto = foto 

    def to_dict(self):
        return{
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "senha": self.senha,
            "data_nascimento": self.data_nascimento,
            "genero": self.genero,
            "foto": self.foto
        }