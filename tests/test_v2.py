import asyncio
import websockets
import json
import time

PREGUNTAS = [
    "Explicame la paradoja de Russell en teoria de conjuntos",
    "Que paso en el Concilio de Trento?",
    "Cuéntame algo interesante sobre filosofia",
    "Como estas hoy?"
]

async def test():
    for i, preg in enumerate(PREGUNTAS):
        print(f"\n{'='*60}")
        print(f"PREGUNTA {i+1}: {preg}")
        print('='*60)
        t0 = time.time()
        try:
            ws = await websockets.connect('ws://127.0.0.1:8765', ping_interval=None)
            await ws.recv()  # state
            cmd = json.dumps({'type': 'command', 'value': preg})
            await ws.send(cmd)

            texts = []
            state = None
            for j in range(500):  # más mensajes, más tiempo
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=30)
                    elapsed = time.time() - t0
                    parsed = json.loads(resp)
                    t = parsed.get('type')
                    v = str(parsed.get('value', ''))
                    if t == 'log' and v.startswith('MIN:'):
                        text = v.replace('MIN:', '').strip()
                        if text and len(text) > 2:
                            texts.append(text)
                            print(f"  [{elapsed:.1f}s] TEXT: {text[:100]}")
                    elif t == 'state':
                        if state != v:
                            state = v
                            print(f"  [{elapsed:.1f}s] STATE: {v}")
                except asyncio.TimeoutError:
                    print(f"  Timeout en mensaje {j}")
                    break

            print(f"  --> Tiempo total: {time.time()-t0:.1f}s")
            print(f"  --> Respuestas recibidas: {len(texts)}")
            if texts:
                full = ' '.join(texts)
                print(f"  --> TEXTO COMPLETO: {full[:300]}...")
            await ws.close()
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(2)

asyncio.run(test())
