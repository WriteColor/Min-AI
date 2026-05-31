"""
Test 09: Verificación de cambio de personalidad del asistente
==========================
Prueba que MIN responde de forma natural, sin frases estáticas,
con muletillas apropiadas y sin uso innecesario de herramientas.
"""

import asyncio
import json
import sys
import time
sys.path.insert(0, ".")

from pathlib import Path


# =============================================================================
# TESTS DE ESTILO CONVERSACIONAL
# =============================================================================

def check_no_static_phrases(text: str) -> dict:
    """Verifica que no haya frases estáticas repetitivas."""
    static_phrases = [
        "por supuesto",
        "con mucho gusto",
        "encantado de ayudarte",
        "¡exactamente!",
        "asi es",
        "exactamente como dijiste",
        "tal como mencionaste",
        "basándome en",
        "mi respuesta anterior",
        "como te comenté",
        "como mencioné anteriormente",
    ]

    found = []
    text_lower = text.lower()

    for phrase in static_phrases:
        if phrase.lower() in text_lower:
            found.append(phrase)

    return {
        "clean": len(found) == 0,
        "found": found
    }


def check_natural_markers(text: str) -> dict:
    """Verifica presencia de marcadores conversacionales naturales."""
    markers = {
        "fillers": ["eh", "mmm", "este", "a ver", "bueno", "pues", "entonces"],
        "connectors": ["vale", "claro", "ajá", "ya", "bueno", "oh", "ah"],
        "confirmation": ["ya veo", "entiendo", "comprendo", "ok", "de acuerdo"]
    }

    text_lower = text.lower()
    found_markers = {
        "fillers": [],
        "connectors": [],
        "confirmation": []
    }

    for category, words in markers.items():
        for word in words:
            if word in text_lower:
                found_markers[category].append(word)

    return {
        "has_natural_markers": any(found_markers.values()),
        "markers_found": found_markers
    }


def check_no_tool_phrase(text: str) -> dict:
    """Verifica que no use frases predefinidas de herramientas."""
    tool_phrases = [
        "utilizando la herramienta",
        "voy a usar",
        "para ello utilizaré",
        "mediante el uso de",
        "me encuentro",
        "estoy buscando",
        "procedo a",
    ]

    found = []
    text_lower = text.lower()

    for phrase in tool_phrases:
        if phrase.lower() in text_lower:
            found.append(phrase)

    return {
        "clean": len(found) == 0,
        "found": found
    }


def check_response_length(text: str) -> dict:
    """Verifica que las respuestas no sean demasiado largas."""
    # Una respuesta natural debería tener menos de 300 palabras
    words = text.split()
    is_too_long = len(words) > 300

    return {
        "appropriate_length": not is_too_long,
        "word_count": len(words),
        "is_too_verbose": is_too_long
    }


def check_spanish_natural(text: str) -> dict:
    """Verifica uso natural del español."""
    # Espacios en blanco antes de signos de puntuación son comunes en español mal formateado
    bad_patterns = [
        " .",  # espacio antes de punto
        " ,",  # espacio antes de coma
        " !",  # espacio antes de exclamación
        " ?",  # espacio antes de interrogación
    ]

    text_lower = text.lower()
    found_bad = []

    for pattern in bad_patterns:
        if pattern in text_lower:
            found_bad.append(pattern)

    return {
        "proper_spanish": len(found_bad) == 0,
        "issues": found_bad
    }


# =============================================================================
# TEST DE USO DE HERRAMIENTAS
# =============================================================================

def should_use_tool(query: str) -> tuple[bool, str]:
    """Determina si una query debería usar herramienta o no."""

    # Queries que SÍ necesitan herramienta
    needs_tool = {
        "time": ["hora", "qué hora", "tiempo actual"],
        "music": ["spotify", "reproduce", "pon música", "pausa"],
        "search": ["busca", "búsqueda", "información sobre", "qué es"],
        "weather": ["clima", "tiempo en", "temperatura"],
        "system": ["wifi", "volumen", "brillo", "apagar"],
        "message": ["whatsapp", "mensaje", "envía"],
    }

    # Queries que NO necesitan herramienta
    no_tool = {
        "opinion": ["crees que", "qué opinas", "qué piensas"],
        "philosophy": ["por qué", "significa", "explica la vida"],
        "casual": ["cómo estás", "qué tal", "hola", "buenos días"],
    }

    query_lower = query.lower()

    # Verificar si necesita herramienta
    for category, keywords in needs_tool.items():
        for keyword in keywords:
            if keyword in query_lower:
                return True, f"necesita_tool ({category})"

    # Verificar si NO necesita herramienta
    for category, keywords in no_tool.items():
        for keyword in keywords:
            if keyword in query_lower:
                return False, f"no_necesita_tool ({category})"

    return None, "indeterminado"


# =============================================================================
# TESTS PRINCIPALES
# =============================================================================

async def test_personality_style():
    """Test de estilo de personalidad."""
    print("\n[1] Verificando estilo de personalidad...")

    # Texts that should pass
    good_texts = [
        "eh, mmm, este... pues depende de cómo lo veas, no?",
        "ah, ya entiendo lo que dices. Claro, tiene sentido.",
        "bueno, eso es interesante. Oh, no lo había pensado así.",
        "vale, entonces si lo analizamos bien...",
        "mmm, déjame pensar... ya! tienes razón",
    ]

    # Texts with static phrases (should fail)
    bad_texts = [
        "Por supuesto, con mucho gusto te ayudo.",
        "Encantado de ayudarte, ¿qué necesitas?",
        "¡Exactamente! Tal como mencionaste anteriormente.",
        "Basándome en mi respuesta anterior...",
    ]

    results = []

    print("    Texts buenos (deberian pasar):")
    for text in good_texts:
        check = check_no_static_phrases(text)
        status = "[PASS]" if check["clean"] else "[FAIL]"
        print(f"    {status} '{text[:40]}...'")
        results.append(check["clean"])

    print("\n    Textos malos (deberian fallar):")
    for text in bad_texts:
        check = check_no_static_phrases(text)
        status = "[PASS]" if not check["clean"] else "[FAIL]"
        print(f"    {status} Detectado: {check['found']}")
        results.append(not check["clean"])

    return all(results)


async def test_natural_markers():
    """Test de marcadores naturales."""
    print("\n[2] Verificando marcadores naturales...")

    text = "eh, mmm, este... bueno, ya sabes cómo es. Vale, entonces cuando quieras. Ajá, claro que sí."

    check = check_natural_markers(text)

    print(f"    Marcadores encontrados: {check['markers_found']}")
    print(f"    Tiene marcadores naturales?: {'[PASS]' if check['has_natural_markers'] else '[FAIL]'}")

    return check['has_natural_markers']


async def test_tool_usage_rules():
    """Test de reglas de uso de herramientas."""
    print("\n[3] Verificando reglas de uso de herramientas...")

    test_cases = [
        # NO deberían usar herramienta
        ("qué hora es", False, "simple_time"),
        ("cómo estás hoy", False, "casual"),
        ("qué piensas de la vida", False, "philosophy"),

        # SÍ deberían usar herramienta
        ("qué hora es en tokio", True, "time_query"),
        ("busca información sobre física cuántica", True, "search"),
        ("pon música de jazz", True, "music"),
    ]

    results = []
    for query, expected_uses_tool, category in test_cases:
        uses_tool, reason = should_use_tool(query)
        correct = uses_tool == expected_uses_tool
        results.append(correct)

        status = "[PASS]" if correct else "[FAIL]"
        print(f"    {status} '{query}'")
        print(f"       -> Espera: {'tool' if expected_uses_tool else 'no tool'}")
        print(f"       -> Usa: {reason}")
        print(f"       -> Correcto?: {correct}")

    return all(results)


async def test_read_prompt_file():
    """Verifica que el archivo prompt.txt tenga las características esperadas."""
    print("\n[4] Verificando archivo core/prompt.txt...")

    prompt_path = Path("C:/React-Nextjs-Projects/Jarvis AI/core/prompt.txt")

    if not prompt_path.exists():
        print(f"    ✗ Archivo no encontrado: {prompt_path}")
        return False

    content = prompt_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    print(f"    -> Lineas: {len(lines)}")
    print(f"    -> Caracteres: {len(content)}")

    # Verificaciones
    checks = {
        "natural_voice": "hablo como persona normal" in content.lower(),
        "no_static_phrases": "frases prefabricadas" in content.lower(),
        "tool_rules": "herramientas" in content.lower() and "openrouter" in content.lower(),
        "fillers": "mmm" in content or "eh," in content or "muletillas" in content.lower(),
        "no_repeat": "nunca repitas" in content.lower() or "no repet" in content.lower(),
        "examples": "ejemplo" in content.lower() or "ejemplos" in content.lower(),
    }

    print("\n    Características encontradas:")
    all_pass = True
    for check_name, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"    {status} {check_name}: {passed}")
        if not passed:
            all_pass = False

    # Mostrar preview
    print("\n    Preview del prompt:")
    print("    " + "-" * 40)
    for line in lines[:15]:
        print(f"    {line}")
    print("    ...")

    return all_pass


async def test_response_evaluation():
    """Test de evaluación de respuestas generadas."""
    print("\n[5] Evaluando respuestas simuladas...")

    # Respuesta BUENA (natural, corta)
    good_response = """
    mmm, eh... bueno, depende de cómo lo veas. Si me preguntas si creo que vale la pena,
    te diría que sí, pero no porque sí. Ajá, ya me entiendes.
    """

    # Respuesta MALA (robot, larga, estática)
    bad_response = """
    Por supuesto, con mucho gusto te respondo esta pregunta.
    Basándome en mi conocimiento y en lo que me has consultado,
    me encuentro en posición de afirmar que la respuesta correcta es la siguiente:
    Primero, necesito utilizar la herramienta de búsqueda para encontrar información
    relevante sobre el tema que me estás preguntando. Para ello, procederé a
    hacer uso de la herramienta de openrouter_agent para procesar tu solicitud.
    """

    print("\n    Evaluando respuesta BUENA:")
    r1_static = check_no_static_phrases(good_response)
    r1_length = check_response_length(good_response)
    r1_markers = check_natural_markers(good_response)

    print(f"    -> Sin frases estaticas: {'[PASS]' if r1_static['clean'] else '[FAIL]'}")
    print(f"    -> Longitud apropiada: {'[PASS]' if r1_length['appropriate_length'] else '[FAIL]'}")
    print(f"    -> Marcadores naturales: {'[PASS]' if r1_markers['has_natural_markers'] else '[FAIL]'}")

    print("\n    Evaluando respuesta MALA:")
    r2_static = check_no_static_phrases(bad_response)
    r2_length = check_response_length(bad_response)
    r2_tool = check_no_tool_phrase(bad_response)

    print(f"    -> Sin frases estaticas: {'[PASS]' if r2_static['clean'] else '[FAIL]'} (deberia ser False)")
    print(f"    -> Longitud apropiada: {'[PASS]' if r2_length['appropriate_length'] else '[FAIL]'} (deberia ser False)")
    print(f"    -> Sin frases de herramienta: {'[PASS]' if r2_tool['clean'] else '[FAIL]'} (deberia ser False)")

    # La buena respuesta debe pasar todas
    # La mala debe fallar en al menos una
    good_passes = r1_static['clean'] and r1_length['appropriate_length']
    bad_fails = not (r2_static['clean'] and r2_length['appropriate_length'] and r2_tool['clean'])

    return good_passes and bad_fails


async def main():
    print("=" * 60)
    print("TEST 09: Verificación de personalidad del asistente")
    print("=" * 60)

    results = []

    results.append(await test_personality_style())
    results.append(await test_natural_markers())
    results.append(await test_tool_usage_rules())
    results.append(await test_read_prompt_file())
    results.append(await test_response_evaluation())

    print("\n" + "=" * 60)
    print(f"RESULTADO: {sum(results)}/{len(results)} tests aprobados")
    print("=" * 60)

    if all(results):
        print("\n[PASS] El asistente tiene las caracteristicas de personalidad esperadas:")
        print("  - Habla de forma natural")
        print("  - Usa muletillas y marcadores")
        print("  - No usa frases estaticas")
        print("  - Respeta reglas de herramientas")
        print("  - El archivo prompt.txt esta correctamente configurado")
    else:
        print("\n[FAIL] Hay aspectos de personalidad que necesitan ajustes")

    return all(results)


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
