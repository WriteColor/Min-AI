"""
DuckDuckGo Search Provider
=========================
Proveedor de búsqueda usando DuckDuckGo HTML.

Método: Scraping del HTML de DuckDuckGo
Ventajas: Gratuito, no requiere API key
Limitaciones: Rate limited, puede cambiar estructura HTML
"""

import urllib.parse
import urllib.request
import re
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from .search_provider import (
    BaseSearchProvider,
    SearchProviderType,
    SearchResult,
    SearchResponse,
    SearchProviderFactory
)


class DuckDuckGoProvider(BaseSearchProvider):
    """
    Proveedor de búsqueda usando DuckDuckGo.
    
    Usa el endpoint HTML de DuckDuckGo que devuelve resultados
    en formato más parseable que el endpoint principal.
    """
    
    provider_type = SearchProviderType.DUCKDUCKGO
    requires_api_key = False
    rate_limit_requests_per_minute = 20  # Conservative limit
    
    DUCKDUCKGO_HTML_URL = "https://duckduckgo.com/html/"
    DUCKDUCKGO_JSON_URL = "https://duckduckgo.com/"
    
    def __init__(self, use_json: bool = True):
        """
        Inicializar proveedor DuckDuckGo.
        
        Args:
            use_json: Usar endpoint JSON en lugar de HTML (más estable)
        """
        super().__init__()
        self.use_json = use_json
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    def _execute(self, query: str, **kwargs) -> List[SearchResult]:
        """
        Ejecutar búsqueda en DuckDuckGo.
        
        Args:
            query: Término de búsqueda
            
        Returns:
            Lista de SearchResult
        """
        if self.use_json:
            return self._search_json(query, **kwargs)
        else:
            return self._search_html(query, **kwargs)
    
    def _search_json(self, query: str, **kwargs) -> List[SearchResult]:
        """
        Búsqueda usando endpoint JSON de DuckDuckGo.
        
        Este método usa la API interna de DuckDuckGo que devuelve
        resultados en formato JSON más fácil de parsear.
        """
        results = []
        
        try:
            # First request to get cookies
            url = f"{self.DUCKDUCKGO_JSON_URL}?q={urllib.parse.quote(query)}&ia=web"
            request = urllib.request.Request(url, headers=self._headers)
            
            with urllib.request.urlopen(request, timeout=10) as response:
                html_content = response.read().decode('utf-8')
            
            # Extract results from HTML using regex patterns
            # DuckDuckGo embeds results in a script tag as JSON
            results = self._parse_duckduckgo_results(html_content, query)
            
        except Exception as e:
            # Fallback to HTML parsing
            results = self._search_html(query, **kwargs)
        
        return results
    
    def _search_html(self, query: str, **kwargs) -> List[SearchResult]:
        """
        Búsqueda usando endpoint HTML de DuckDuckGo.
        
        Args:
            query: Término de búsqueda
            
        Returns:
            Lista de SearchResult parseados del HTML
        """
        results = []
        
        try:
            url = f"{self.DUCKDUCKGO_HTML_URL}?q={urllib.parse.quote(query)}"
            request = urllib.request.Request(url, headers=self._headers)
            
            with urllib.request.urlopen(request, timeout=10) as response:
                html_content = response.read().decode('utf-8')
            
            # Parse HTML results
            results = self._parse_html_results(html_content, query)
            
        except Exception as e:
            raise RuntimeError(f"DuckDuckGo search failed: {e}")
        
        return results
    
    def _parse_duckduckgo_results(self, html_content: str, query: str) -> List[SearchResult]:
        """Parse resultados del HTML de DuckDuckGo."""
        results = []
        
        # Pattern for result items
        # DuckDuckGo results are in <a> tags with class="result__a"
        result_pattern = r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
        snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]+)</a>'
        
        # Find all result links
        for match in re.finditer(result_pattern, html_content):
            url = match.group(1)
            title = self._clean_html(match.group(2))
            
            # Find corresponding snippet
            snippet_start = match.end()
            snippet_match = re.search(
                r'<a class="result__snippet"[^>]*>([^<]+)</a>',
                html_content[snippet_start:snippet_start+500]
            )
            snippet = ""
            if snippet_match:
                snippet = self._clean_html(snippet_match.group(1))
            
            results.append(SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                source="DuckDuckGo",
                metadata={"query": query}
            ))
            
            if len(results) >= 20:  # Limit results
                break
        
        # If regex didn't work, try JSON parsing
        if not results:
            results = self._parse_json_data(html_content, query)
        
        return results
    
    def _parse_json_data(self, html_content: str, query: str) -> List[SearchResult]:
        """Intentar parsear datos JSON embebidos en el HTML."""
        results = []
        
        # Look for JSON data embedded in the page
        json_pattern = r'data-result="([^"]+)"'
        for match in re.finditer(json_pattern, html_content):
            try:
                # Data is URL encoded
                import html
                data = html.unescape(match.group(1))
                # Try to parse as JSON
                result_data = json.loads(data)
                
                if isinstance(result_data, dict):
                    results.append(SearchResult(
                        title=self._clean_html(result_data.get('t', '')),
                        url=result_data.get('u', ''),
                        snippet=self._clean_html(result_data.get('d', '')),
                        source="DuckDuckGo",
                        metadata={"query": query}
                    ))
            except (json.JSONDecodeError, KeyError):
                continue
        
        return results
    
    def _parse_html_results(self, html_content: str, query: str) -> List[SearchResult]:
        """Parse resultados de formato HTML."""
        results = []
        
        # Clean the HTML content first
        # Remove script and style tags
        html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL)
        
        # Find result links
        # Pattern: <h2 class="result__title"> followed by <a class="result__a">
        title_pattern = r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
        
        for match in re.finditer(title_pattern, html_clean):
            url = match.group(1)
            title = self._clean_html(match.group(2))
            
            # Look for snippet near the result
            snippet_pattern = rf'<a class="result__snippet"[^>]*>([^<]+)</a>'
            snippet_start = match.end()
            snippet_match = re.search(
                snippet_pattern,
                html_clean[snippet_start:snippet_start+1000]
            )
            
            snippet = ""
            if snippet_match:
                snippet = self._clean_html(snippet_match.group(1))
            
            # Skip if URL is not valid
            if not url.startswith(('http://', 'https://')):
                continue
            
            results.append(SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                source="DuckDuckGo",
                metadata={"query": query}
            ))
            
            if len(results) >= 20:
                break
        
        return results
    
    def _extract_snippet(self, html_segment: str) -> str:
        """Extraer snippet de un segmento HTML."""
        # Remove all HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_segment)
        # Decode HTML entities
        text = self._clean_html(text)
        return text


# Register provider with factory
SearchProviderFactory.register(
    SearchProviderType.DUCKDUCKGO,
    DuckDuckGoProvider
)
