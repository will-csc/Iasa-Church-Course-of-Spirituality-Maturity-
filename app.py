"""Servidor local do Curso de Maturidade Espiritual."""

from __future__ import annotations

import atexit
import configparser
import secrets
import socket
import sys
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from room_state import room
from tunnel import get_public_url, start_tunnel, stop_tunnel, tunnel_info
from users import UserStore

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR.mkdir(exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
DEFAULT_PDF_FILE = DATA_DIR / "784656217-CURSO-DE-MATURIDADE-NO-ESPIRITO-1.pdf"
DEFAULT_PDF_URL = "/material/curso.pdf"

ALLOWED_EXTENSIONS = {"pdf"}

DEFAULT_MEMBERS = [
    "William",
    "Stela",
    "Peter",
    "Saraiva",
    "Bruna",
    "Felipe",
    "Carol",
    "Paulo",
]


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    config_path = BASE_DIR / "config.ini"
    example_path = BASE_DIR / "config.ini.example"
    if not config_path.exists() and example_path.exists():
        config_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
    cfg.read(config_path, encoding="utf-8")
    return cfg


config = load_config()
user_store = UserStore(USERS_FILE)

# Garante as contas iniciais (senha = Nome + 123)
for _name in DEFAULT_MEMBERS:
    user_store.upsert(_name, f"{_name}123")

# PDF padrão de todas as aulas
if DEFAULT_PDF_FILE.exists():
    room.configure_default_pdf(DEFAULT_PDF_FILE.name, DEFAULT_PDF_URL)

app = Flask(__name__)
app.secret_key = config.get("app", "SECRET_KEY", fallback=secrets.token_hex(16))
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024  # 80 MB

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


def get_lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


def share_url(port: int | None = None) -> str:
    """Link externo (ngrok) se existir; senão localhost."""
    public = get_public_url()
    if public:
        return public
    p = port or config.getint("app", "PORT", fallback=8080)
    return f"http://127.0.0.1:{p}"


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("role"):
            return redirect(url_for("login"))
        if session.get("role") == "member" and room.snapshot()["room_locked"]:
            session.clear()
            flash("A sala está bloqueada pelo Apóstolo.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def master_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "master":
            return jsonify({"ok": False, "error": "Apenas o Apóstolo pode fazer isso."}), 403
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_share_link():
    return {
        "public_url": get_public_url(),
        "share_link": share_url(),
        "tunnel_error": tunnel_info.error,
    }


@app.route("/")
def index():
    if session.get("role"):
        return redirect(url_for("sala"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("role"):
            return redirect(url_for("sala"))
        return render_template("login.html")

    mode = request.form.get("mode", "member")
    master_user = config.get("auth", "MASTER_USER", fallback="master")
    master_password = config.get("auth", "MASTER_PASSWORD", fallback="")

    if mode == "master":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if (
            username.casefold() == master_user.casefold()
            and password.casefold() == master_password.casefold()
        ):
            session.clear()
            session["role"] = "master"
            session["name"] = master_user
            return redirect(url_for("sala"))
        flash("Usuário ou senha do Apóstolo incorretos.", "error")
        return render_template("login.html", show_master=True)

    name = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if room.snapshot()["room_locked"]:
        flash("A sala está bloqueada pelo Apóstolo. Tente mais tarde.", "error")
        return render_template("login.html")

    if not name or not password:
        flash("Informe nome e senha.", "error")
        return render_template("login.html")

    if user_store.authenticate(name, password):
        matched = user_store.resolve_display_name(name) or name
        session.clear()
        session["role"] = "member"
        session["name"] = matched
        return redirect(url_for("sala"))

    flash("Nome ou senha incorretos.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/sala")
@login_required
def sala():
    state = room.snapshot()
    return render_template(
        "sala.html",
        role=session.get("role"),
        display_name=session.get("name", ""),
        jitsi_room=config.get("jitsi", "ROOM_NAME", fallback="iasa-espiritual-reuniao"),
        room_state=state,
        users=user_store.list_users() if session.get("role") == "master" else [],
        lan_url=f"http://{get_lan_ip()}:{config.get('app', 'PORT', fallback='8080')}",
        local_url=f"http://127.0.0.1:{config.get('app', 'PORT', fallback='8080')}",
    )


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/material/curso.pdf")
@login_required
def default_material():
    if not DEFAULT_PDF_FILE.exists():
        return "PDF padrão não encontrado.", 404
    return send_from_directory(
        DEFAULT_PDF_FILE.parent,
        DEFAULT_PDF_FILE.name,
        mimetype="application/pdf",
    )


@app.route("/api/room/state")
@login_required
def api_room_state():
    return jsonify(room.snapshot())


@app.route("/api/public-url")
def api_public_url():
    return jsonify(
        {
            "ok": True,
            "public_url": get_public_url(),
            "share_link": share_url(),
            "error": tunnel_info.error,
        }
    )


@app.route("/api/room/page", methods=["POST"])
@login_required
@master_required
def api_set_page():
    data = request.get_json(silent=True) or {}
    page = data.get("page", 1)
    try:
        page = int(page)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Página inválida."}), 400
    state = room.set_page(page)
    socketio.emit("room_update", state)
    return jsonify({"ok": True, **state})


@app.route("/api/room/lock", methods=["POST"])
@login_required
@master_required
def api_set_lock():
    data = request.get_json(silent=True) or {}
    locked = bool(data.get("locked", False))
    state = room.set_locked(locked)
    socketio.emit("room_update", state)
    return jsonify({"ok": True, **state})


@app.route("/api/room/upload", methods=["POST"])
@login_required
@master_required
def api_upload():
    if "pdf" not in request.files:
        return jsonify({"ok": False, "error": "Nenhum arquivo enviado."}), 400
    file = request.files["pdf"]
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "Arquivo vazio."}), 400
    if not allowed_file(file.filename):
        return jsonify({"ok": False, "error": "Envie apenas PDF."}), 400

    filename = secure_filename(file.filename)
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    for old in UPLOAD_DIR.glob("*.pdf"):
        try:
            old.unlink()
        except OSError:
            pass

    dest = UPLOAD_DIR / filename
    file.save(dest)
    state = room.set_pdf(filename, f"/uploads/{filename}")
    socketio.emit("room_update", state)
    return jsonify({"ok": True, **state})


@app.route("/api/room/clear", methods=["POST"])
@login_required
@master_required
def api_clear_pdf():
    for old in UPLOAD_DIR.glob("*.pdf"):
        try:
            old.unlink()
        except OSError:
            pass
    state = room.restore_default_pdf()
    socketio.emit("room_update", state)
    return jsonify({"ok": True, **state})


@app.route("/api/room/highlight", methods=["POST"])
@login_required
@master_required
def api_add_highlight():
    data = request.get_json(silent=True) or {}
    page = data.get("page", 1)
    stroke = data.get("stroke") or []
    try:
        page = int(page)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Página inválida."}), 400
    if not isinstance(stroke, list) or len(stroke) < 2:
        return jsonify({"ok": False, "error": "Traço inválido."}), 400
    state = room.add_stroke(page, stroke)
    saved = (state.get("highlights") or {}).get(str(page) or "", [])
    last = saved[-1] if saved else stroke
    socketio.emit("highlight_stroke", {"page": page, "stroke": last})
    return jsonify({"ok": True, **state})


@app.route("/api/room/highlight/clear", methods=["POST"])
@login_required
@master_required
def api_clear_highlights():
    data = request.get_json(silent=True) or {}
    page = data.get("page")
    if page is not None:
        try:
            page = int(page)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Página inválida."}), 400
    state = room.clear_highlights(page)
    socketio.emit("highlight_clear", {"page": page})
    return jsonify({"ok": True, **state})


@app.route("/api/users", methods=["GET"])
@login_required
@master_required
def api_list_users():
    return jsonify({"ok": True, "users": user_store.list_users()})


@app.route("/api/users", methods=["POST"])
@login_required
@master_required
def api_create_user():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "")
    password = data.get("password", "")
    ok, message = user_store.create(name, password)
    if not ok:
        return jsonify({"ok": False, "error": message}), 400
    return jsonify({"ok": True, "message": message, "users": user_store.list_users()})


@app.route("/api/users/delete", methods=["POST"])
@login_required
@master_required
def api_delete_user():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "")
    ok, message = user_store.delete(name)
    if not ok:
        return jsonify({"ok": False, "error": message}), 400
    return jsonify({"ok": True, "message": message, "users": user_store.list_users()})


@socketio.on("connect")
def on_connect():
    if not session.get("role"):
        return False
    emit("room_update", room.snapshot())


@socketio.on("request_state")
def on_request_state():
    if not session.get("role"):
        return
    emit("room_update", room.snapshot())


def print_startup_banner(port: int) -> None:
    local = f"http://127.0.0.1:{port}"
    public = get_public_url()
    line = "=" * 56
    print()
    print(line)
    print("  Curso de Maturidade Espiritual")
    print(line)
    print(f"  Neste computador:  {local}")
    if public:
        print(f"  Link externo:      {public}")
        print(f"  Provedor:          {tunnel_info.provider or '-'}")
        print()
        print("  Compartilhe o link externo com os fiéis.")
    else:
        print(f"  Link externo:      (indisponível)")
        if tunnel_info.error:
            print(f"  Motivo: {tunnel_info.error}")
    print()
    print("  Não desligue este PC enquanto o curso estiver ativo.")
    print("  Login Apóstolo: MASTER_USER / MASTER_PASSWORD no config.ini")
    print(line)
    print()


def main() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    host = config.get("app", "HOST", fallback="0.0.0.0")
    port = config.getint("app", "PORT", fallback=8080)
    authtoken = ""
    if config.has_section("ngrok"):
        authtoken = config.get("ngrok", "AUTHTOKEN", fallback="")

    info = start_tunnel(port, authtoken)
    if info.public_url:
        print(f"[tunnel:{info.provider}] {info.public_url}")
    elif info.error:
        print(f"[tunnel] {info.error}")

    atexit.register(stop_tunnel)

    print_startup_banner(port)
    # provider no banner usa o estado global já atualizado por start_tunnel
    socketio.run(
        app,
        host=host,
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
