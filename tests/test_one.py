import asyncio
import websockets
import json

PREG = "Explícame la paradoja de Russell en teoría de conjuntos"

async def test():
    ws = await websockets.connect('ws://127.0.0.1:8765')
    await ws.recv()  # state
    print(f"PREGUNTA: {PREG}")
    print("-" * 60)

    cmd = json.dumps({'type': 'command', 'value': PREG})
    await ws.send(cmd)

    texts = []
    for i in range(200):
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=20)
            parsed = json.loads(resp)
            t = parsed.get('type')
            v = str(parsed.get('value', ''))
            if t == 'log' and v.startswith('MIN:'):
                text = v.replace('MIN:', '').strip()
                if text:
                    texts.append(text)
                    print(f"  {text}")
            elif t == 'state':
                print(f"  [STATE] {v}")
        except asyncio.TimeoutError:
            break

    print("-" * 60)
    print(f"TOTAL TEXT: {' '.join(texts)}")
    await ws.close()

asyncio.run(test())
