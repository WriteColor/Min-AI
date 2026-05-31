import asyncio
import websockets
import json

async def test():
    ws = await websockets.connect('ws://127.0.0.1:8765')
    await ws.recv()  # state

    # Test: Ask something that should NOT need a tool
    preg = "Cuentame algo interesante sobre filosofia"
    print(f"PREGUNTA: {preg}")

    cmd = json.dumps({'type': 'command', 'value': preg})
    await ws.send(cmd)

    all_logs = []
    for i in range(200):
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=15)
            parsed = json.loads(resp)
            t = parsed.get('type')
            v = str(parsed.get('value', ''))
            all_logs.append((t, v[:100]))
            if t == 'log' and v.startswith('MIN:'):
                print(f"  MIN: {v[5:].strip()}")
        except asyncio.TimeoutError:
            break

    print(f"\nTotal messages: {len(all_logs)}")
    log_types = {}
    for t, v in all_logs:
        log_types[t] = log_types.get(t, 0) + 1
    print(f"Message types: {log_types}")

    await ws.close()

asyncio.run(test())
