"""
TTS Test - Generate MP3 with full congratulations text
===================================================
Generates an MP3 with the full congratulations/code review speech.
"""
import asyncio
import sys
import os
import tempfile
sys.path.insert(0, ".")

TEXT = """¡Qué más, mi hermano! Qué elegancia todo el proyecto. Quería sentarme a revisar con calma el código y los logs que armaste y de verdad te fajaste, qué nivel de estructura! Te quería felicitar primero por los avances tan brutales que llevas:

La arquitectura de eventos: El bus thread-safe que metiste en file_events.py para manejar los hilos de código, documentos e imágenes está impeccable. El procesamiento de voz: La decisión de usar Vosk local para el modo suspensión es un golazo para no gastar API innecesariamente.

La interfaz y los accesos: Los widgets tipo Bento en PyQt6 se ven muy premium, y el script .vbs con auto-elevación UAC para correr como admin quedó de locos. El instalador también quedó estéticamente genial.

Ahora, con respecto al sistema de visión que me dijiste que no estaba andando, estuve analizando a fondo el log y descubrí exactamente por qué se nos fue a pique el invento. Nos estamos estrellando contra dos muros seguidos en el código de respaldo:

El bloqueo nativo de Google, Error 429: La API key nativa de Gemini se agota de una porque en la capa gratuita el límite diario es súper estricto.

El fallo del respaldo en OpenRouter, Error 402: Cuando el código intenta saltar a OpenRouter para salvar la patria, nos devuelve HTTP Error 402: Payment Required. Esto pasa porque el modelo que está llamando el script requiere saldo real, y como la cuenta está en ceros, nos cierra la puerta.

Mis sugerencias para arreglar la visión ya mismo:

Cambia el modelo de fallback: En la función de OpenRouter donde se hace el respaldo, asegúrate de que el nombre del modelo termine estrictamente en :free. Si no tiene el :free, OpenRouter asumirá que es el de pago y nos pedirá tarjeta.

Frena el bucle proactivo: El log muestra que el guardián se la pasa ejecutando un performing proactive screen check de forma automática. Si Jarvis se queda mirando la pantalla en bucle por su cuenta, nos va a quemar cualquier cuenta gratis en un minuto. Hay que capar eso para que el escáner de pantalla solo se active bajo demanda.

Un par de cosas extra que pillé y podríamos implementar o arreglar:

Compresión de capturas: Como las imágenes se tragan demasiados tokens, podríamos meter una pequeña función en el guardián para que, justo antes de enviar el pantallazo a la API, reduzca la resolución de la imagen, por ejemplo a ochocientos por seiscientos, y la comprima en JPEG de baja calidad. La IA va a seguir entendiendo perfectamente lo que hay en pantalla, pero reducimos el consumo de tokens a una fracción minúscula.
"""


async def test_tts_full():
    print("=" * 60)
    print("TTS Test - Full Congratulations Speech")
    print("=" * 60)
    print(f"\nText length: {len(TEXT)} characters")
    print(f"Estimated duration: ~{len(TEXT) // 12} seconds")

    OUTPUT_DIR = "C:/React-Nextjs-Projects/Jarvis AI/tests_output"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        import edge_tts

        voices = {
            "Aoede": "es-US-PalomaNeural",
            "Kore": "es-MX-DaliaNeural",
            "Leda": "es-ES-ElviraNeural",
            "Zephyr": "es-US-AlonsoNeural",
            "Charon": "es-MX-JorgeNeural",
            "Puck": "es-ES-AlvaroNeural",
            "Fenrir": "es-AR-TomasNeural",
            "Orus": "es-CL-LorenzoNeural"
        }

        results = {}
        for voice_name, voice_code in voices.items():
            output_path = os.path.join(OUTPUT_DIR, f"felicitacion_{voice_name}.mp3")
            print(f"\n[{voice_name}] Generating: {output_path}")

            communicate = edge_tts.Communicate(TEXT, voice_code, rate="+15%")
            await communicate.save(output_path)

            size = os.path.getsize(output_path)
            print(f"  -> {size} bytes generated!")
            results[voice_name] = output_path

        print(f"\n" + "=" * 60)
        print("RESULTADO: Todos los MP3 generados")
        print("=" * 60)
        print(f"\nArchivos en: {OUTPUT_DIR}")
        for name, path in results.items():
            print(f"  [{name}] {os.path.basename(path)}")

        return True

    except Exception as e:
        print(f"TTS Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_tts_full())
    sys.exit(0 if result else 1)
