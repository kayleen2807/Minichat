import asyncio
import json
import websockets

salas = {}  # sala -> set de (websocket, usuario)

async def broadcast(sala, mensaje):
    for ws, _ in list(salas.get(sala, [])):
        try:
            await ws.send(json.dumps(mensaje))
        except:
            pass

async def handler(websocket):
    usuario = None
    sala = None
    try:
        async for raw in websocket:
            d = json.loads(raw)

            if d["tipo"] == "entrar":
                usuario = d["usuario"]
                sala = d["sala"]
                if sala not in salas:
                    salas[sala] = set()
                salas[sala].add((websocket, usuario))
                await broadcast(sala, {"tipo": "sistema", "texto": f"{usuario} ha entrado a la sala {sala}"})

            elif d["tipo"] == "salir":
                if sala and (websocket, usuario) in salas.get(sala, set()):
                    salas[sala].discard((websocket, usuario))
                    await broadcast(sala, {"tipo": "sistema", "texto": f"{usuario} ha salido de la sala {sala}"})
                sala = None

            elif d["tipo"] == "mensaje":
                await broadcast(sala, {"tipo": "mensaje", "texto": f"{usuario}: {d['texto']}"})

    except:
        pass
    finally:
        if sala and usuario:
            salas.get(sala, set()).discard((websocket, usuario))
            await broadcast(sala, {"tipo": "sistema", "texto": f"{usuario} se desconecto"})

async def main():
    print("Servidor iniciado en ws://0.0.0.0:8765")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()

asyncio.run(main())