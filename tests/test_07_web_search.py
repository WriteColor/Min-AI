"""
Test 07: Búsqueda web sin navegador
==========================
Prueba búsqueda en internet y retorno de información resumida.
"""

import asyncio
import sys
sys.path.insert(0, ".")

from actions.automation.web_search import search_web, search_news, search_facts


async def test_search_precise(query: str, expected_type: str):
    """Test de búsqueda con información precisa."""
    print(f"\n[+] Query: '{query}' ({expected_type})")

    try:
        result = await search_web(query)

        if result.get('success'):
            data = result.get('data', {})
            results = data.get('results', [])

            print(f"    → {len(results)} resultados encontrados")

            if results:
                # Mostrar primer resultado completo
                top = results[0]
                print(f"    → Título: {top.get('title', 'N/A')}")
                print(f"    → URL: {top.get('url', 'N/A')[:60]}...")

                snippet = top.get('snippet', '')
                if snippet:
                    print(f"    → Snippet: {snippet[:150]}...")

                # Verificar si hay datos estructurados
                if 'date' in top:
                    print(f"    → Fecha: {top.get('date', 'N/A')}")
                if 'rating' in top:
                    print(f"    → Rating: {top.get('rating', 'N/A')}")

            return True
        else:
            print(f"    ✗ {result.get('message', 'Error desconocido')}")
            return False

    except Exception as e:
        print(f"    ✗ Exception: {e}")
        return False


async def test_search_with_dates():
    """Test de búsqueda de fechas específicas."""
    print("\n" + "=" * 60)
    print("TEST 07b: Búsquedas con información de FECHA específica")
    print("=" * 60)

    date_queries = [
        ("Fecha del descubrimiento de América", "historical_date"),
        ("Cuando fue la Revolución Francesa", "historical_date"),
        ("Día de la Independencia de México", "historical_date"),
        ("Cuándo terminó la Segunda Guerra Mundial", "historical_date"),
        ("Fecha del primer viaje a la Luna", "historical_date"),
    ]

    results = []
    for query, expected_type in date_queries:
        print(f"\n[?] '{query}'")
        try:
            # Usar search_facts para información factual
            result = await search_facts(query)

            if result.get('success'):
                data = result.get('data', {})
                answer = data.get('answer', '')
                sources = data.get('sources', [])

                print(f"    ✓ Respuesta: {answer}")
                if sources:
                    print(f"    → Fuentes: {len(sources)}")
                    for src in sources[:2]:
                        print(f"       - {src.get('title', 'N/A')}: {src.get('url', 'N/A')[:50]}...")

                results.append(True)
            else:
                print(f"    ✗ {result.get('message', 'Error')}")
                results.append(False)

        except Exception as e:
            print(f"    ✗ Exception: {e}")
            results.append(False)

        await asyncio.sleep(1)

    print("\n" + "=" * 60)
    print(f"RESULTADO: {sum(results)}/{len(results)} búsquedas de fecha exitosas")
    print("=" * 60)

    return all(results)


async def test_news_search():
    """Test de búsqueda de noticias."""
    print("\n" + "=" * 60)
    print("TEST 07c: Búsqueda de noticias")
    print("=" * 60)

    topics = [
        "Inteligencia artificial 2026",
        "Tecnología espacial",
        "Energías renovables",
    ]

    results = []
    for topic in topics:
        print(f"\n[+] Noticias sobre: '{topic}'")
        try:
            result = await search_news(topic)

            if result.get('success'):
                articles = result.get('articles', [])
                print(f"    → {len(articles)} artículos")

                for art in articles[:3]:
                    print(f"       📰 {art.get('title', 'N/A')}")
                    print(f"          {art.get('source', 'N/A')} - {art.get('date', 'N/A')}")
                    print(f"          {art.get('description', 'N/A')[:100]}...")

                results.append(True)
            else:
                print(f"    ✗ {result.get('message', '')}")
                results.append(False)

        except Exception as e:
            print(f"    ✗ Exception: {e}")
            results.append(False)

        await asyncio.sleep(1)

    return all(results)


async def test_math_search():
    """Test de búsqueda matemática."""
    print("\n" + "=" * 60)
    print("TEST 07d: Búsqueda de información matemática")
    print("=" * 60)

    math_queries = [
        ("Teorema de Pitágoras fórmula", "math"),
        ("Derivada de e^x", "math"),
        ("Integrales definidas", "math"),
        ("Número PI primeros 20 decimales", "math"),
    ]

    results = []
    for query, _ in math_queries:
        print(f"\n[?] '{query}'")
        try:
            result = await search_facts(query)

            if result.get('success'):
                data = result.get('data', {})
                answer = data.get('answer', '')
                print(f"    ✓ {answer[:200]}...")
                results.append(True)
            else:
                print(f"    ✗ {result.get('message', '')}")
                results.append(False)

        except Exception as e:
            print(f"    ✗ Exception: {e}")
            results.append(False)

        await asyncio.sleep(1)

    return all(results)


async def main():
    print("=" * 60)
    print("TEST 07: Búsqueda web sin navegador")
    print("=" * 60)

    # Test de búsquedas generales
    general_queries = [
        ("Python programming language", "general"),
        ("Best restaurants in Madrid", "local"),
        ("How to cook paella", "howto"),
    ]

    results = []
    for query, qtype in general_queries:
        results.append(await test_search_precise(query, qtype))
        await asyncio.sleep(1)

    # Tests específicos
    results.append(await test_search_with_dates())
    results.append(await test_news_search())
    results.append(await test_math_search())

    print("\n" + "=" * 60)
    print(f"RESULTADO GENERAL: {sum(results)}/{len(results)} categorías aprobadas")
    print("=" * 60)

    return all(results)


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
