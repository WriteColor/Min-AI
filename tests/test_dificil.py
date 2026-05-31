import asyncio
import websockets
import json
import sys

PREGS = [
    "Explícame la paradoja de Russell en teoría de conjuntos",
    "Cuéntame sobre la guerra de las culturas en la antigua Roma",
    "Resuelve: integra e^(x²) dx desde 0 hasta infinito",
    "Explica el argumento del cerebro en una cubeta de Hilary Putnam",
    "Qué pasó en el Concilio de Trento y cómo afectó a la iglesia?"
]

async def test():
    for i, preg in enumerate(PREGS):
        print(f"\n{'='*60}")
        print(f"PREGUNTA {i+1}: {preg}")
        print('='*60)
        try:
            ws = await websockets.connect('ws://127.0.0.1:8765')
            await ws.recv()  # state
            cmd = json.dumps({'type': 'command', 'value': preg})
            await ws.send(cmd)

            responses = []
            for j in range(100):
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=15)
                    parsed = json.loads(resp)
                    t = parsed.get('type')
                    v = str(parsed.get('value', ''))[:200]
                    if t in ('log', 'text', 'state'):
                        print(f"  [{t}] {v}")
                    responses.append((t, v))
                except asyncio.TimeoutError:
                    break

            print(f"  --> Total msgs: {len(responses)}")
            await ws.close()
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(1)

asyncio.run(test())
