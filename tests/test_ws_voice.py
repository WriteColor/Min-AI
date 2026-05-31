import asyncio
import websockets
import json
import sys

async def test_voice():
    try:
        ws = await websockets.connect('ws://127.0.0.1:8765')
        print('Connected!')

        greeting = await asyncio.wait_for(ws.recv(), timeout=5)
        print('State:', greeting)

        question = 'Que hora es?'
        cmd = json.dumps({'type': 'command', 'value': question})
        await ws.send(cmd)
        print('Sent question')

        responses = []
        for i in range(100):
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=20)
                responses.append(resp)
                parsed = json.loads(resp)
                msg_type = parsed.get('type')
                preview = str(parsed.get('value', ''))[:150]
                print(f'Response {i+1}: type={msg_type}, preview={preview}')
            except asyncio.TimeoutError:
                print(f'Timeout after {i+1} responses')
                break

        await ws.close()
        print(f'Total responses received: {len(responses)}')
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)

asyncio.run(test_voice())
