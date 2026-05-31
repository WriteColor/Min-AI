import asyncio
import websockets
import json

PREGUNTAS = [
    "Que hora es?",
    "Cuentame un chiste",
    "Como estas?"
]

async def test():
    for i, preg in enumerate(PREGUNTAS):
        print(f"\n{'='*60}")
        print(f"PREGUNTA {i+1}: {preg}")
        print('='*60)
        try:
            ws = await websockets.connect('ws://127.0.0.1:8765')
            await ws.recv()  # state
            cmd = json.dumps({'type': 'command', 'value': preg})
            await ws.send(cmd)

            texts = []
            for j in range(100):
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=15)
                    parsed = json.loads(resp)
                    t = parsed.get('type')
                    v = str(parsed.get('value', ''))
                    if t == 'log' and v.startswith('MIN:'):
                        text = v.replace('MIN:', '').strip()
                        if text and len(text) > 2:
                            texts.append(text)
                            print(f"  TEXT: {text}")
                    elif t == 'state':
                        print(f"  STATE: {v}")
                except asyncio.TimeoutError:
                    break

            print(f"  --> TOTAL: {' '.join(texts)}")
            await ws.close()
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(1)

asyncio.run(test())
