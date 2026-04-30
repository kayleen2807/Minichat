from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "clave-secreta-chat"
socketio = SocketIO(app, cors_allowed_origins="*")

# sala -> lista de usuarios conectados
usuarios_en_sala = {}

@app.route("/")
@app.route("/chat")
def index():
    return render_template("chat.html")


@socketio.on("entrar")
def on_entrar(data):
    usuario = (data.get("usuario") or "").strip()
    sala    = (data.get("sala")    or "").strip()
    if not usuario or not sala:
        emit("error", {"texto": "Falta usuario o sala"})
        return

    # Guardar en sesión del socket
    request.sid  # solo para asegurarnos de tener acceso
    join_room(sala)

    if sala not in usuarios_en_sala:
        usuarios_en_sala[sala] = {}
    usuarios_en_sala[sala][request.sid] = usuario

    emit("sistema", {"texto": f"{usuario} ha entrado a la sala '{sala}'"}, to=sala)
    emit("miembro_lista", {"usuarios": list(usuarios_en_sala[sala].values())}, to=sala)


@socketio.on("salir")
def on_salir(data):
    sala = (data.get("sala") or "").strip()
    if not sala:
        return
    usuario = usuarios_en_sala.get(sala, {}).pop(request.sid, "alguien")
    leave_room(sala)
    emit("sistema", {"texto": f"{usuario} ha salido de la sala '{sala}'"}, to=sala)
    emit("miembro_lista", {"usuarios": list(usuarios_en_sala.get(sala, {}).values())}, to=sala)


@socketio.on("mensaje")
def on_mensaje(data):
    sala    = (data.get("sala")    or "").strip()
    texto   = (data.get("texto")   or "").strip()
    usuario = (data.get("usuario") or "").strip()
    if not sala or not texto or not usuario:
        return
    emit("mensaje", {"usuario": usuario, "texto": texto}, to=sala)


@socketio.on("disconnect")
def on_disconnect():
    # Buscar al usuario en todas las salas y sacarlo
    for sala, miembros in list(usuarios_en_sala.items()):
        if request.sid in miembros:
            usuario = miembros.pop(request.sid)
            emit("sistema", {"texto": f"{usuario} se desconectó"}, to=sala)
            emit("miembro_lista", {"usuarios": list(miembros.values())}, to=sala)


if __name__ == "__main__":
    import socket

    def guess_lan_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    ip = guess_lan_ip()
    print(f"\n{'='*45}")
    print(f"  Abre en tu navegador:")
    print(f"  http://{ip}:5000/chat")
    print(f"  (Comparte esa URL con tu compañera)")
    print(f"{'='*45}\n")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)