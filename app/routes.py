from flask import (
    Blueprint, render_template, request, jsonify,
    redirect, url_for, session, abort, Response
)
from functools import wraps
from .models import RedeModel, ConfigModel, SessaoModel
from .qr_generator import generate_svg

main_bp = Blueprint('main', __name__)
api_bp  = Blueprint('api',  __name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()


def requer_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated


# ── Rotas públicas ───────────────────────────────────────────────────────────

@main_bp.route('/')
def index():
    redes = RedeModel.listar_ativas()
    cfg   = ConfigModel.todas()
    return render_template('app/index.html', redes=redes, cfg=cfg)


@main_bp.route('/rede/<int:rede_id>')
def rede_detalhe(rede_id):
    rede = RedeModel.obter(rede_id)
    if not rede or not rede['ativa']:
        abort(404)

    ip = _get_ip()
    ua = request.headers.get('User-Agent', '')
    limite = int(ConfigModel.obter('limite_minutos', '30'))

    estado = SessaoModel.verificar(rede_id, ip, limite)

    if not estado['ok']:
        # IP bloqueado — mostrar página de bloqueio
        cfg = ConfigModel.todas()
        return render_template(
            'app/bloqueado.html',
            rede=rede, cfg=cfg,
            estado=estado,
            limite=limite
        ), 403

    # Registar acesso só na primeira visita
    if estado.get('nova'):
        RedeModel.registrar_acesso(rede_id, ip, ua)

    cfg = ConfigModel.todas()
    return render_template(
        'app/detalhe.html',
        rede=rede, cfg=cfg,
        segundos_restantes=estado['segundos_restantes']
    )


@main_bp.route('/rede/<int:rede_id>/qr.svg')
def rede_qr(rede_id):
    """Serve o QR code como SVG gerado no servidor."""
    rede = RedeModel.obter(rede_id)
    if not rede or not rede['ativa']:
        abort(404)
    wifi_str = f"WIFI:T:{rede['seguranca']};S:{rede['ssid']};P:{rede['senha']};;"
    try:
        svg = generate_svg(wifi_str, module_px=6, quiet=4)
    except Exception:
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="#eee"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="#999">QR indisponível</text></svg>'
    return Response(svg, mimetype='image/svg+xml',
                    headers={'Cache-Control': 'no-cache'})


# ── Login / Logout ────────────────────────────────────────────────────────────

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        senha = request.form.get('senha', '')
        senha_correta = ConfigModel.obter('senha_admin', 'admin123')
        if senha == senha_correta:
            session['admin'] = True
            session.permanent = True
            return redirect(url_for('main.admin'))
        erro = 'Senha incorrecta.'
    return render_template('app/login.html', erro=erro, cfg=ConfigModel.todas())


@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))


# ── Área de administração ─────────────────────────────────────────────────────

@main_bp.route('/admin')
@requer_admin
def admin():
    redes  = RedeModel.listar_todas()
    stats  = RedeModel.stats()
    cfg    = ConfigModel.todas()
    return render_template('app/admin.html', redes=redes, stats=stats, cfg=cfg)


@main_bp.route('/admin/rede/nova', methods=['GET', 'POST'])
@requer_admin
def nova_rede():
    if request.method == 'POST':
        RedeModel.criar(
            nome=request.form['nome'],
            ssid=request.form['ssid'],
            senha=request.form['senha'],
            seguranca=request.form.get('seguranca', 'WPA'),
            descricao=request.form.get('descricao', '')
        )
        return redirect(url_for('main.admin'))
    return render_template('app/form_rede.html', rede=None, cfg=ConfigModel.todas())


@main_bp.route('/admin/rede/<int:rede_id>/editar', methods=['GET', 'POST'])
@requer_admin
def editar_rede(rede_id):
    rede = RedeModel.obter(rede_id)
    if not rede:
        abort(404)
    if request.method == 'POST':
        RedeModel.atualizar(
            rede_id=rede_id,
            nome=request.form['nome'],
            ssid=request.form['ssid'],
            senha=request.form['senha'],
            seguranca=request.form.get('seguranca', 'WPA'),
            descricao=request.form.get('descricao', ''),
            ativa=1 if request.form.get('ativa') else 0
        )
        return redirect(url_for('main.admin'))
    return render_template('app/form_rede.html', rede=rede, cfg=ConfigModel.todas())


@main_bp.route('/admin/rede/<int:rede_id>/acessos')
@requer_admin
def ver_acessos(rede_id):
    rede    = RedeModel.obter(rede_id)
    if not rede:
        abort(404)
    acessos = RedeModel.acessos_recentes(rede_id, 50)
    sessoes = SessaoModel.listar_sessoes(rede_id)
    cfg     = ConfigModel.todas()
    return render_template('app/acessos.html', rede=rede, acessos=acessos,
                           sessoes=sessoes, cfg=cfg)


@main_bp.route('/admin/sessoes')
@requer_admin
def ver_sessoes():
    sessoes = SessaoModel.listar_sessoes()
    cfg     = ConfigModel.todas()
    return render_template('app/sessoes.html', sessoes=sessoes, cfg=cfg)


@main_bp.route('/admin/configuracoes', methods=['GET', 'POST'])
@requer_admin
def configuracoes():
    if request.method == 'POST':
        for chave in ['titulo_site', 'subtitulo', 'senha_admin', 'limite_minutos']:
            valor = request.form.get(chave, '').strip()
            if valor:
                ConfigModel.definir(chave, valor)
        return redirect(url_for('main.admin'))
    return render_template('app/configuracoes.html', cfg=ConfigModel.todas())


# ── API ───────────────────────────────────────────────────────────────────────

@api_bp.route('/redes')
def api_redes():
    redes = RedeModel.listar_ativas()
    return jsonify([dict(r) for r in redes])


@api_bp.route('/redes/<int:rede_id>/deletar', methods=['POST'])
@requer_admin
def api_deletar(rede_id):
    RedeModel.deletar(rede_id)
    return jsonify({'ok': True})


@api_bp.route('/redes/<int:rede_id>/toggle', methods=['POST'])
@requer_admin
def api_toggle(rede_id):
    rede = RedeModel.obter(rede_id)
    if not rede:
        return jsonify({'erro': 'Não encontrado'}), 404
    nova = 0 if rede['ativa'] else 1
    from .database import get_db
    db = get_db()
    db.execute('UPDATE redes SET ativa=? WHERE id=?', (nova, rede_id))
    db.commit()
    return jsonify({'ativa': nova})


@api_bp.route('/sessoes/<int:rede_id>/desbloquear', methods=['POST'])
@requer_admin
def api_desbloquear(rede_id):
    ip = request.json.get('ip') if request.is_json else request.form.get('ip')
    if not ip:
        return jsonify({'erro': 'IP obrigatório'}), 400
    SessaoModel.desbloquear(rede_id, ip)
    return jsonify({'ok': True})


@api_bp.route('/sessoes/estado')
def api_estado_sessao():
    """Permite ao cliente verificar quanto tempo de sessão resta."""
    rede_id = request.args.get('rede_id', type=int)
    if not rede_id:
        return jsonify({'erro': 'rede_id obrigatório'}), 400
    ip = _get_ip()
    limite = int(ConfigModel.obter('limite_minutos', '30'))
    sessao = SessaoModel.obter_sessao(rede_id, ip)
    if not sessao:
        return jsonify({'estado': 'sem_sessao'})
    from datetime import datetime
    agora = datetime.now()
    expira_dt = datetime.strptime(sessao['expira_em'], '%Y-%m-%d %H:%M:%S')
    restantes = int((expira_dt - agora).total_seconds())
    if sessao['bloqueada'] or restantes <= 0:
        return jsonify({'estado': 'bloqueado', 'segundos_restantes': 0})
    return jsonify({'estado': 'activo', 'segundos_restantes': max(0, restantes)})


# ── 404 ───────────────────────────────────────────────────────────────────────

@main_bp.errorhandler(404)
def not_found(e):
    return render_template('app/404.html', cfg=ConfigModel.todas()), 404


@main_bp.route('/rede/<int:rede_id>/qr-acesso.svg')
def rede_qr_acesso(rede_id):
    """QR code que aponta para o URL desta página (para outros dispositivos acederem)."""
    from .qr_generator import generate_svg
    from .models import ConfigModel
    ip    = ConfigModel.obter('ip_local', request.host.split(':')[0])
    porta = ConfigModel.obter('porta', '5000')
    url   = f"http://{ip}:{porta}/rede/{rede_id}"
    try:
        svg = generate_svg(url, module_px=6, quiet=4)
    except Exception:
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="#eee"/></svg>'
    return Response(svg, mimetype='image/svg+xml',
                    headers={'Cache-Control': 'no-cache'})
