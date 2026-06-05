from .database import get_db
from datetime import datetime, timedelta


class RedeModel:

    @staticmethod
    def listar_ativas():
        db = get_db()
        return db.execute(
            'SELECT * FROM redes WHERE ativa = 1 ORDER BY criada_em DESC'
        ).fetchall()

    @staticmethod
    def listar_todas():
        db = get_db()
        return db.execute(
            'SELECT * FROM redes ORDER BY criada_em DESC'
        ).fetchall()

    @staticmethod
    def obter(rede_id):
        db = get_db()
        return db.execute(
            'SELECT * FROM redes WHERE id = ?', (rede_id,)
        ).fetchone()

    @staticmethod
    def criar(nome, ssid, senha, seguranca, descricao):
        db = get_db()
        cur = db.execute(
            '''INSERT INTO redes (nome, ssid, senha, seguranca, descricao)
               VALUES (?, ?, ?, ?, ?)''',
            (nome, ssid, senha, seguranca, descricao)
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def atualizar(rede_id, nome, ssid, senha, seguranca, descricao, ativa):
        db = get_db()
        db.execute(
            '''UPDATE redes SET nome=?, ssid=?, senha=?, seguranca=?, descricao=?, ativa=?
               WHERE id=?''',
            (nome, ssid, senha, seguranca, descricao, ativa, rede_id)
        )
        db.commit()

    @staticmethod
    def deletar(rede_id):
        db = get_db()
        db.execute('DELETE FROM redes WHERE id = ?', (rede_id,))
        db.commit()

    @staticmethod
    def registrar_acesso(rede_id, ip, user_agent):
        db = get_db()
        db.execute(
            'INSERT INTO acessos (rede_id, ip, user_agent) VALUES (?, ?, ?)',
            (rede_id, ip, user_agent)
        )
        db.execute(
            'UPDATE redes SET acessos = acessos + 1 WHERE id = ?', (rede_id,)
        )
        db.commit()

    @staticmethod
    def acessos_recentes(rede_id, limite=20):
        db = get_db()
        return db.execute(
            '''SELECT * FROM acessos WHERE rede_id = ?
               ORDER BY acessado_em DESC LIMIT ?''',
            (rede_id, limite)
        ).fetchall()

    @staticmethod
    def stats():
        db = get_db()
        total   = db.execute('SELECT COUNT(*) FROM redes').fetchone()[0]
        ativas  = db.execute('SELECT COUNT(*) FROM redes WHERE ativa=1').fetchone()[0]
        acessos = db.execute('SELECT SUM(acessos) FROM redes').fetchone()[0] or 0
        hoje    = db.execute(
            "SELECT COUNT(*) FROM acessos WHERE date(acessado_em)=date('now','localtime')"
        ).fetchone()[0]
        bloqueados = db.execute(
            "SELECT COUNT(DISTINCT ip) FROM sessoes WHERE bloqueada=1"
        ).fetchone()[0]
        return {'total': total, 'ativas': ativas, 'acessos': acessos,
                'hoje': hoje, 'bloqueados': bloqueados}


class SessaoModel:

    @staticmethod
    def obter_sessao(rede_id, ip):
        """Devolve a sessão mais recente deste IP para esta rede."""
        db = get_db()
        return db.execute(
            '''SELECT * FROM sessoes WHERE rede_id=? AND ip=?
               ORDER BY iniciada_em DESC LIMIT 1''',
            (rede_id, ip)
        ).fetchone()

    @staticmethod
    def criar_sessao(rede_id, ip, minutos=30):
        db = get_db()
        agora = datetime.now()
        expira = agora + timedelta(minutes=minutos)
        db.execute(
            '''INSERT INTO sessoes (rede_id, ip, iniciada_em, expira_em, bloqueada)
               VALUES (?, ?, ?, ?, 0)''',
            (rede_id, ip,
             agora.strftime('%Y-%m-%d %H:%M:%S'),
             expira.strftime('%Y-%m-%d %H:%M:%S'))
        )
        db.commit()

    @staticmethod
    def bloquear(rede_id, ip):
        db = get_db()
        db.execute(
            'UPDATE sessoes SET bloqueada=1 WHERE rede_id=? AND ip=?',
            (rede_id, ip)
        )
        db.commit()

    @staticmethod
    def desbloquear(rede_id, ip):
        db = get_db()
        db.execute(
            'DELETE FROM sessoes WHERE rede_id=? AND ip=?',
            (rede_id, ip)
        )
        db.commit()

    @staticmethod
    def verificar(rede_id, ip, minutos_limite=30):
        """
        Verifica o estado da sessão para um IP numa rede.
        Devolve um dict com:
          - 'ok': True → pode aceder normalmente
          - 'bloqueado': True → já passou o limite (retorna segundos restantes = 0)
          - 'nova': True → primeira visita, cria sessão
          - 'segundos_restantes': tempo até bloqueio (int)
          - 'segundos_bloqueado': tempo de bloqueio já cumprido (int, se bloqueado)
        """
        sessao = SessaoModel.obter_sessao(rede_id, ip)
        agora = datetime.now()

        if sessao is None:
            # Primeira visita — criar sessão
            SessaoModel.criar_sessao(rede_id, ip, minutos_limite)
            return {'ok': True, 'nova': True,
                    'segundos_restantes': minutos_limite * 60}

        if sessao['bloqueada']:
            # Já foi bloqueado
            expira_dt = datetime.strptime(sessao['expira_em'], '%Y-%m-%d %H:%M:%S')
            segundos = int((agora - expira_dt).total_seconds())
            return {'ok': False, 'bloqueado': True,
                    'segundos_bloqueado': max(0, segundos),
                    'iniciada_em': sessao['iniciada_em'],
                    'expira_em': sessao['expira_em']}

        expira_dt = datetime.strptime(sessao['expira_em'], '%Y-%m-%d %H:%M:%S')
        restantes = int((expira_dt - agora).total_seconds())

        if restantes <= 0:
            # Tempo esgotado — bloquear
            SessaoModel.bloquear(rede_id, ip)
            return {'ok': False, 'bloqueado': True,
                    'segundos_bloqueado': 0,
                    'iniciada_em': sessao['iniciada_em'],
                    'expira_em': sessao['expira_em']}

        return {'ok': True, 'nova': False,
                'segundos_restantes': restantes,
                'iniciada_em': sessao['iniciada_em'],
                'expira_em': sessao['expira_em']}

    @staticmethod
    def listar_sessoes(rede_id=None, apenas_bloqueadas=False):
        db = get_db()
        sql = 'SELECT s.*, r.nome as rede_nome FROM sessoes s JOIN redes r ON r.id=s.rede_id'
        conds, params = [], []
        if rede_id:
            conds.append('s.rede_id=?'); params.append(rede_id)
        if apenas_bloqueadas:
            conds.append('s.bloqueada=1')
        if conds:
            sql += ' WHERE ' + ' AND '.join(conds)
        sql += ' ORDER BY s.iniciada_em DESC'
        return db.execute(sql, params).fetchall()


class ConfigModel:

    @staticmethod
    def obter(chave, default=None):
        db = get_db()
        row = db.execute('SELECT valor FROM config WHERE chave=?', (chave,)).fetchone()
        return row['valor'] if row else default

    @staticmethod
    def definir(chave, valor):
        db = get_db()
        db.execute(
            'INSERT OR REPLACE INTO config (chave, valor) VALUES (?,?)',
            (chave, valor)
        )
        db.commit()

    @staticmethod
    def todas():
        db = get_db()
        rows = db.execute('SELECT chave, valor FROM config').fetchall()
        return {r['chave']: r['valor'] for r in rows}
