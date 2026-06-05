"""
hotspot_reader.py
Lê as credenciais do hotspot activo no Windows usando 'netsh'.
Funciona em Windows 10/11 sem dependências externas.
"""

import subprocess
import re
import socket


def _run(cmd):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            encoding='utf-8', errors='replace', timeout=8
        )
        return result.stdout
    except Exception:
        return ''


def obter_credenciais_hotspot():
    """
    Tenta ler o SSID e senha do hotspot móvel do Windows.
    Devolve dict com: ssid, senha, seguranca  ou None se não encontrar.
    """
    # Método 1: netsh wlan show hostednetwork
    out = _run('netsh wlan show hostednetwork')
    ssid_match  = re.search(r'SSID\s*:\s*(.+)', out, re.IGNORECASE)
    # A senha não aparece neste comando — precisa do método 2

    # Método 2: netsh wlan show profile name="..." key=clear
    # Primeiro listar todos os perfis
    profiles_out = _run('netsh wlan show profiles')
    perfis = re.findall(r'All User Profile\s*:\s*(.+)', profiles_out)

    credenciais = []
    for perfil in perfis:
        perfil = perfil.strip()
        detalhe = _run(f'netsh wlan show profile name="{perfil}" key=clear')
        ssid_m = re.search(r'SSID name\s*:\s*"(.+)"', detalhe)
        key_m  = re.search(r'Key Content\s*:\s*(.+)', detalhe)
        sec_m  = re.search(r'Authentication\s*:\s*(.+)', detalhe)
        if ssid_m and key_m:
            ssid = ssid_m.group(1).strip()
            senha = key_m.group(1).strip()
            seg_raw = sec_m.group(1).strip() if sec_m else 'WPA2'
            if 'WPA2' in seg_raw.upper():
                seg = 'WPA2'
            elif 'WPA' in seg_raw.upper():
                seg = 'WPA'
            else:
                seg = 'nopass'
            credenciais.append({'ssid': ssid, 'senha': senha, 'seguranca': seg})

    # Método 3: hotspot móvel via registro (mais fiável para hotspot do Windows 10/11)
    hotspot = _obter_hotspot_movel()
    if hotspot:
        return hotspot

    # Se encontrou perfis, devolver o primeiro
    if credenciais:
        return credenciais[0]

    # Fallback: ler rede WiFi à qual está ligado (sem senha)
    rede_ligada = _obter_rede_ligada()
    if rede_ligada:
        return rede_ligada

    return None


def _obter_hotspot_movel():
    """
    Lê o hotspot móvel do Windows 10/11 directamente do registo.
    Requer privilégios de administrador para a senha.
    """
    try:
        import winreg  # só existe no Windows
        # Caminho do registo do hotspot móvel Windows 10/11
        chave_path = r'SOFTWARE\Microsoft\WlanSvc\MicrosoftWifi'
        try:
            chave = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, chave_path)
            # tentar ler AllowedCombinedFeatures e outros
            winreg.CloseKey(chave)
        except Exception:
            pass

        # Caminho onde Windows guarda o perfil do hotspot
        chave_path2 = r'SYSTEM\CurrentControlSet\Services\icssvc\Settings'
        try:
            chave2 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, chave_path2)
            try:
                ssid, _ = winreg.QueryValueEx(chave2, 'TetheringSettingsData')
            except Exception:
                ssid = None
            winreg.CloseKey(chave2)
        except Exception:
            pass

    except ImportError:
        pass  # não estamos no Windows

    # Método mais directo: netsh wlan show hostednetwork + perfil
    out = _run('netsh wlan show hostednetwork setting=security')
    ssid_m = re.search(r'SSID\s*:\s*(.+)', out, re.IGNORECASE)
    key_m  = re.search(r'User Security Key\s*:\s*(.+)', out, re.IGNORECASE)

    if ssid_m and key_m:
        return {
            'ssid': ssid_m.group(1).strip(),
            'senha': key_m.group(1).strip(),
            'seguranca': 'WPA2'
        }

    # Tentar via PowerShell (Windows 10/11 hotspot)
    ps_cmd = (
        'powershell -NoProfile -Command "'
        '$ap = Get-NetConnectionProfile | Where-Object {$_.NetworkCategory -eq \'Private\'}; '
        '$ap.Name'
        '"'
    )
    # Mais directo: ler o hotspot via PowerShell API
    ps_hotspot = (
        'powershell -NoProfile -Command "'
        'Add-Type -AssemblyName System.Runtime.WindowsRuntime; '
        '$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | '
        '  Where-Object { $_.Name -eq \'AsTask\' -and $_.GetParameters().Count -eq 1 -and '
        '  $_.GetParameters()[0].ParameterType.Name -eq \'IAsyncOperation`1\' })[0]; '
        '$networkOperatorTetheringManager = '
        '  [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,Windows.Networking,'
        '  ContentType=WindowsRuntime]; '
        'Write-Output done'
        '"'
    )
    # Abordagem mais simples e fiável: netsh WLAN show hostednetwork
    out2 = _run('netsh wlan show hostednetwork')
    if 'Started' in out2 or 'Iniciado' in out2 or 'Not started' in out2:
        ssid_m2 = re.search(r'SSID\s*:\s*(.+)', out2, re.IGNORECASE)
        if ssid_m2:
            ssid2 = ssid_m2.group(1).strip()
            # Tentar obter senha do perfil com o mesmo nome
            detalhe = _run(f'netsh wlan show profile name="{ssid2}" key=clear')
            key_m2 = re.search(r'Key Content\s*:\s*(.+)', detalhe)
            if key_m2:
                return {'ssid': ssid2, 'senha': key_m2.group(1).strip(), 'seguranca': 'WPA2'}

    return None


def _obter_rede_ligada():
    """Devolve o SSID da rede WiFi à qual o PC está ligado (sem senha)."""
    out = _run('netsh wlan show interfaces')
    ssid_m = re.search(r'^\s+SSID\s*:\s*(.+)$', out, re.MULTILINE | re.IGNORECASE)
    if ssid_m:
        return {
            'ssid': ssid_m.group(1).strip(),
            'senha': '',
            'seguranca': 'WPA2'
        }
    return None


def obter_ip_local():
    """Devolve o IP local da máquina na rede."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'
