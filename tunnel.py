"""Túnel público: ngrok (se houver token) ou Cloudflare quick tunnel."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from paths_util import base_dir

BASE_DIR = base_dir()
TOOLS_DIR = BASE_DIR / "tools"
CLOUDFLARED_EXE = TOOLS_DIR / "cloudflared.exe"


@dataclass
class TunnelInfo:
    public_url: str | None = None
    error: str | None = None
    provider: str | None = None


tunnel_info = TunnelInfo()
_cloudflared_proc: subprocess.Popen | None = None


def get_public_url() -> str | None:
    return tunnel_info.public_url


def _resolve_ngrok_path() -> str | None:
    """Usa ngrok do sistema (winget) ou tools/ngrok.exe, se existir."""
    local = BASE_DIR / "tools" / "ngrok.exe"
    if local.exists():
        return str(local)
    which = shutil.which("ngrok")
    if which:
        return which
    # caminhos comuns do winget no Windows
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "ngrok.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "ngrok" / "ngrok.exe",
        Path("C:/Program Files/ngrok/ngrok.exe"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def _start_ngrok(port: int, authtoken: str) -> TunnelInfo:
    global tunnel_info
    try:
        from pyngrok import conf, ngrok

        pyngrok_config = conf.get_default()
        pyngrok_config.auth_token = authtoken.strip()
        ngrok_path = _resolve_ngrok_path()
        if ngrok_path:
            pyngrok_config.ngrok_path = ngrok_path
        try:
            ngrok.kill()
        except Exception:
            pass
        tunnel = ngrok.connect(addr=port, proto="http", bind_tls=True)
        url = tunnel.public_url
        if url.startswith("http://"):
            url = "https://" + url[len("http://") :]
        tunnel_info = TunnelInfo(public_url=url, provider="ngrok")
        return tunnel_info
    except Exception as exc:  # noqa: BLE001
        tunnel_info = TunnelInfo(error=f"Falha no ngrok: {exc}", provider="ngrok")
        return tunnel_info


def _ensure_cloudflared() -> Path | None:
    TOOLS_DIR.mkdir(exist_ok=True)
    if CLOUDFLARED_EXE.exists():
        return CLOUDFLARED_EXE

    which = shutil.which("cloudflared")
    if which:
        return Path(which)

    # Baixa binário Windows amd64 oficial
    url = (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-windows-amd64.exe"
    )
    try:
        print("[tunnel] Baixando cloudflared...")
        urllib.request.urlretrieve(url, CLOUDFLARED_EXE)
        return CLOUDFLARED_EXE
    except Exception as exc:  # noqa: BLE001
        print(f"[tunnel] Não foi possível baixar cloudflared: {exc}")
        return None


def _start_cloudflared(port: int) -> TunnelInfo:
    global tunnel_info, _cloudflared_proc

    exe = _ensure_cloudflared()
    if not exe:
        tunnel_info = TunnelInfo(
            error="Não foi possível iniciar túnel (cloudflared ausente).",
            provider="cloudflare",
        )
        return tunnel_info

    try:
        _cloudflared_proc = subprocess.Popen(
            [str(exe), "tunnel", "--url", f"http://127.0.0.1:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception as exc:  # noqa: BLE001
        tunnel_info = TunnelInfo(error=f"Falha ao iniciar cloudflared: {exc}", provider="cloudflare")
        return tunnel_info

    url_re = re.compile(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com")
    found: str | None = None
    deadline = time.time() + 45

    assert _cloudflared_proc.stdout is not None
    while time.time() < deadline:
        line = _cloudflared_proc.stdout.readline()
        if not line:
            if _cloudflared_proc.poll() is not None:
                break
            time.sleep(0.05)
            continue
        match = url_re.search(line)
        if match:
            found = match.group(0)
            break

    if found:
        tunnel_info = TunnelInfo(public_url=found, provider="cloudflare")
        # continua lendo em background para não encher o buffer
        def _drain() -> None:
            try:
                while _cloudflared_proc and _cloudflared_proc.poll() is None:
                    _cloudflared_proc.stdout.readline()
            except Exception:
                pass

        threading.Thread(target=_drain, daemon=True).start()
        return tunnel_info

    tunnel_info = TunnelInfo(
        error="Cloudflare Tunnel não retornou URL a tempo.",
        provider="cloudflare",
    )
    return tunnel_info


def start_tunnel(port: int, ngrok_authtoken: str = "") -> TunnelInfo:
    """Preferência: ngrok com token; senão Cloudflare (sem cadastro)."""
    global tunnel_info
    token = (ngrok_authtoken or "").strip()
    if token:
        info = _start_ngrok(port, token)
        if info.public_url:
            return info
        print(f"[tunnel] ngrok falhou ({info.error}); tentando Cloudflare...")

    return _start_cloudflared(port)


def stop_tunnel() -> None:
    global _cloudflared_proc
    if _cloudflared_proc and _cloudflared_proc.poll() is None:
        try:
            _cloudflared_proc.terminate()
        except Exception:
            pass
        _cloudflared_proc = None
    try:
        from pyngrok import ngrok

        ngrok.kill()
    except Exception:
        pass
