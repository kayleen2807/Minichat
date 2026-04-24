import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import websockets

salas = {}  # sala -> set de (websocket, usuario)

TEMPLATES_DIR = Path(__file__).parent / "templates"
CHAT_HTML = TEMPLATES_DIR / "chat.html"


class ChatHttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/chat", "/chat.html"):
            if not CHAT_HTML.exists():
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Falta templates/chat.html\n")
                return

            data = CHAT_HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"404\n")

    def log_message(self, format, *args):
        return


def start_http_server(host="127.0.0.1", port=8000):
    server = ThreadingHTTPServer((host, port), ChatHttpHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def broadcast(sala, mensaje):
    for ws, _ in list(salas.get(sala, [])):
        try:
            await ws.send(json.dumps(mensaje))
        except Exception:
            # si no se puede enviar, probablemente ya se cerró: lo sacamos de la sala
            try:
                salas.get(sala, set()).discard((ws, _))
            except Exception:
                pass

async def handler(websocket):
    usuario = None
    sala = None
    try:
        async for raw in websocket:
            try:
                d = json.loads(raw)
            except Exception:
                await websocket.send(json.dumps({"tipo": "error", "texto": "Mensaje inválido"}))
                continue

            tipo = d.get("tipo")

            if tipo == "entrar":
                nuevo_usuario = (d.get("usuario") or "").strip()
                nueva_sala = (d.get("sala") or "").strip()
                if not nuevo_usuario or not nueva_sala:
                    await websocket.send(json.dumps({"tipo": "error", "texto": "Debes indicar usuario y sala"}))
                    continue

                # si ya estaba en otra sala, salir primero
                if sala and usuario and (websocket, usuario) in salas.get(sala, set()):
                    salas[sala].discard((websocket, usuario))
                    await broadcast(sala, {"tipo": "sistema", "texto": f"{usuario} ha salido de la sala {sala}"})

                usuario = nuevo_usuario
                sala = nueva_sala
                if sala not in salas:
                    salas[sala] = set()
                salas[sala].add((websocket, usuario))
                await broadcast(sala, {"tipo": "sistema", "texto": f"{usuario} ha entrado a la sala {sala}"})

            elif tipo == "salir":
                if sala and (websocket, usuario) in salas.get(sala, set()):
                    salas[sala].discard((websocket, usuario))
                    await broadcast(sala, {"tipo": "sistema", "texto": f"{usuario} ha salido de la sala {sala}"})
                sala = None

            elif tipo == "mensaje":
                texto = (d.get("texto") or "").strip()
                if not texto:
                    continue
                if not sala or not usuario:
                    await websocket.send(json.dumps({"tipo": "error", "texto": "No estás en ninguna sala"}))
                    continue
                await broadcast(sala, {"tipo": "mensaje", "texto": f"{usuario}: {texto}"})

            else:
                await websocket.send(json.dumps({"tipo": "error", "texto": "Tipo de mensaje desconocido"}))

    except Exception:
        pass
    finally:
        if sala and usuario:
            salas.get(sala, set()).discard((websocket, usuario))
            await broadcast(sala, {"tipo": "sistema", "texto": f"{usuario} se desconecto"})

async def main():
    # Usar 127.0.0.1 evita que "localhost" resuelva a IPv6 (::1) en Windows y falle si el servidor no escucha IPv6.
    start_http_server("127.0.0.1", 8000)
    print("HTTP: http://127.0.0.1:8000/chat")
    print("WS: ws://127.0.0.1:8765")
    async with websockets.serve(handler, "127.0.0.1", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
