"""
iniciar.py  —  Script de arranque do WiFi Share para Windows
Lê o hotspot activo, regista a rede na base de dados e inicia o servidor.
Execute com:  python iniciar.py
"""

import sys
import os
import subprocess
import socket
import webbrowser
import time
import threading

# ── Verificar Python ──────────────────────────────────────────────────────────
if sys.version_info < (3, 8):
    print("ERRO: Python 3.8 ou superior é necessário.")
    input("Pressione Enter para sair...")
    sys.exit(1)

# ── Verificar Flask ───────────────────────────────────────────────────────────
try:
    import flask
except ImportError:
    print("A instalar Flask...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask'])

# ── Importar o leitor de hotspot ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from hotspot_reader import obter_credenciais_hotspot, obter_ip_local

# ── Ler hotspot ───────────────────────────────────────────────────────────────
print("=" * 55)
print("  WiFi Share — Sistema de Partilha de Rede")
print("=" * 55)
print()
print("[*] A ler credenciais do hotspot Windows...")

credenciais = obter_credenciais_hotspot()

if credenciais:
    print(f"[✓] Rede encontrada: {credenciais['ssid']}")
    if credenciais['senha']:
        print(f"[✓] Senha: {'*' * len(credenciais['senha'])}")
    else:
        print("[!] Senha não encontrada (rede aberta ou sem permissão)")
else:
    print("[!] Hotspot não detectado automaticamente.")
    print()
    print("  Introduza os dados manualmente:")
    ssid  = input("  SSID (nome da rede): ").strip()
    senha = input("  Senha: ").strip()
    seg   = input("  Segurança [WPA2]: ").strip() or 'WPA2'
    credenciais = {'ssid': ssid, 'senha': senha, 'seguranca': seg}

ip_local = obter_ip_local()
porta    = 5000

print()
print(f"[*] IP local detectado: {ip_local}")

# ── Iniciar Flask e registar rede ─────────────────────────────────────────────
from app import create_app
from app.models import RedeModel, ConfigModel

app = create_app()

with app.app_context():
    # Verificar se já existe uma rede com este SSID
    todas = RedeModel.listar_todas()
    rede_existente = next(
        (r for r in todas if r['ssid'] == credenciais['ssid']), None
    )

    if rede_existente:
        rede_id = rede_existente['id']
        # Actualizar senha se mudou
        RedeModel.atualizar(
            rede_id=rede_id,
            nome=rede_existente['nome'],
            ssid=credenciais['ssid'],
            senha=credenciais['senha'],
            seguranca=credenciais.get('seguranca', 'WPA2'),
            descricao=rede_existente['descricao'] or 'Hotspot Windows — actualizado automaticamente',
            ativa=1
        )
        print(f"[✓] Rede '{credenciais['ssid']}' actualizada (id={rede_id})")
    else:
        rede_id = RedeModel.criar(
            nome=credenciais['ssid'],
            ssid=credenciais['ssid'],
            senha=credenciais['senha'],
            seguranca=credenciais.get('seguranca', 'WPA2'),
            descricao='Hotspot Windows — criado automaticamente'
        )
        print(f"[✓] Rede '{credenciais['ssid']}' registada (id={rede_id})")

    # Guardar URL pública nas configurações
    url_publica = f"http://{ip_local}:{porta}/rede/{rede_id}"
    ConfigModel.definir('url_publica', url_publica)
    ConfigModel.definir('ip_local', ip_local)
    ConfigModel.definir('porta', str(porta))

print()
print("=" * 55)
print(f"  Servidor a iniciar em: http://{ip_local}:{porta}")
print(f"  Página da rede:        http://{ip_local}:{porta}/rede/{rede_id}")
print(f"  Painel de admin:       http://{ip_local}:{porta}/admin")
print(f"  Senha admin:           admin123")
print()
print("  Outros dispositivos na mesma rede podem aceder via:")
print(f"  http://{ip_local}:{porta}/rede/{rede_id}")
print("=" * 55)
print()
print("  Pressione Ctrl+C para parar o servidor.")
print()

# Abrir browser automaticamente após 1.5s
def abrir_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{porta}/rede/{rede_id}")

threading.Thread(target=abrir_browser, daemon=True).start()

# ── Iniciar servidor ──────────────────────────────────────────────────────────
app.run(host='0.0.0.0', port=porta, debug=False)
