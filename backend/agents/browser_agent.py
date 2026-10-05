import re
from typing import Any, Dict, List, Optional
import urllib.parse
import webbrowser

from bs4 import BeautifulSoup
import requests

from backend.services.llm_service import llm_service


class BrowserAgent:
    """
    Intelligent Web Navigation and Research Agent for JARVIS.
    Controls browser opening, search engine dispatch, clean article scraping,
    link extraction, and AI page summarization.
    """

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    SEARCH_ENGINES = {
        "google": "https://www.google.com/search?q={}",
        "duckduckgo": "https://duckduckgo.com/?q={}",
        "bing": "https://www.bing.com/search?q={}",
        "youtube": "https://www.youtube.com/results?search_query={}",
        "github": "https://github.com/search?q={}",
        "wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search={}",
        "reddit": "https://www.reddit.com/search/?q={}"
    }

    def __init__(self):
        self.name = "BrowserAgent"

    def _normalize_url(self, url: str) -> str:
        url = url.strip()
        if not re.match(r"^https?://", url, re.IGNORECASE):
            return f"https://{url}"
        return url

    def open_url(self, url: str) -> Dict[str, Any]:
        """
        Open a URL in the user's default web browser.
        """
        if not url:
            return {"success": False, "message": "No URL provided.", "data": None, "error": "EmptyURL"}

        norm_url = self._normalize_url(url)
        try:
            opened = webbrowser.open(norm_url)
            return {
                "success": True,
                "message": f"Opened {norm_url} in browser.",
                "data": {"url": norm_url, "browser_opened": opened},
                "error": None
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to open browser: {e}", "data": None, "error": str(e)}

    def search_and_open(self, query: str, engine: str = "google") -> Dict[str, Any]:
        """
        Perform a web search on the requested search engine and launch in browser.
        """
        engine_key = engine.lower().strip()
        template = self.SEARCH_ENGINES.get(engine_key, self.SEARCH_ENGINES["google"])
        encoded_query = urllib.parse.quote_plus(query.strip())
        target_url = template.format(encoded_query)

        try:
            webbrowser.open(target_url)
            return {
                "success": True,
                "message": f"Searching for '{query}' on {engine_key.title()}.",
                "data": {"query": query, "engine": engine_key, "url": target_url},
                "error": None
            }
        except Exception as e:
            return {"success": False, "message": f"Search open failed: {e}", "data": None, "error": str(e)}

    def scrape_and_summarize(self, url: str, max_chars: int = 2500) -> Dict[str, Any]:
        """
        Scrape clean text from a webpage, extract structure, and summarize via LLM.
        """
        norm_url = self._normalize_url(url)
        try:
            response = requests.get(norm_url, headers=self.DEFAULT_HEADERS, timeout=12)
            if response.status_code >= 400:
                return {
                    "success": False,
                    "message": f"HTTP {response.status_code} while fetching {norm_url}",
                    "data": {"status_code": response.status_code},
                    "error": f"HTTPError {response.status_code}"
                }

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unwanted elements
            for tag in soup(["script", "style", "noscript", "nav", "footer", "aside", "header"]):
                tag.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled Page"

            # Extract headings and paragraphs
            paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
            clean_paragraphs = [p for p in paragraphs if len(p) > 30]

            body_text = "\n\n".join(clean_paragraphs)
            truncated_text = body_text[:max_chars]

            # LLM Summarization if available
            summary = ""
            if llm_service.is_available() and len(truncated_text) > 100:
                summary_prompt = (
                    f"Summarize the key information from this webpage in 2-3 concise bullet points:\n\n"
                    f"Title: {title}\n"
                    f"Content:\n{truncated_text}"
                )
                summary = llm_service.generate_chat_response(summary_prompt)
            else:
                summary = truncated_text[:300] + ("..." if len(truncated_text) > 300 else "")

            return {
                "success": True,
                "message": f"Extracted content from '{title}'.",
                "data": {
                    "url": norm_url,
                    "title": title,
                    "summary": summary,
                    "char_count": len(body_text),
                    "paragraph_count": len(clean_paragraphs),
                    "snippet": truncated_text[:500]
                },
                "error": None
            }
        except Exception as e:
            return {"success": False, "message": f"Scraping failed: {e}", "data": None, "error": str(e)}

    def extract_links(self, url: str, max_links: int = 15) -> Dict[str, Any]:
        """
        Extract meaningful navigation and resource links from a webpage.
        """
        norm_url = self._normalize_url(url)
        try:
            response = requests.get(norm_url, headers=self.DEFAULT_HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            links = []
            seen = set()

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                text = a.get_text(strip=True)

                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue

                full_url = urllib.parse.urljoin(norm_url, href)
                if full_url in seen or not text:
                    continue

                seen.add(full_url)
                links.append({"text": text[:60], "url": full_url})
                if len(links) >= max_links:
                    break

            return {
                "success": True,
                "message": f"Found {len(links)} links on {norm_url}",
                "data": {"url": norm_url, "links": links},
                "error": None
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to extract links: {e}", "data": None, "error": str(e)}

    def open_media(self, query: str, platform: str = "youtube") -> Dict[str, Any]:
        """
        Search and stream media on YouTube or Spotify.
        """
        platform_key = platform.lower().strip()
        if platform_key == "spotify":
            url = f"https://open.spotify.com/search/{urllib.parse.quote_plus(query)}"
        else:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"

        try:
            webbrowser.open(url)
            return {
                "success": True,
                "message": f"Playing '{query}' on {platform_key.title()}.",
                "data": {"query": query, "platform": platform_key, "url": url},
                "error": None
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to open media: {e}", "data": None, "error": str(e)}


browser_agent = BrowserAgent()
