import json
import urllib.parse
from bs4 import BeautifulSoup
import requests
import wikipedia

# Set Wikipedia User-Agent to prevent 403 blocks
try:
    wikipedia.set_user_agent("JarvisAI/1.0 (https://github.com/ranjeetkumarsupaul5-svg/Jarvis)")
except Exception:
    pass

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}


def search_web(query: str, max_results: int = 5):
    """
    Search the web and encyclopedia for real-time information.
    """
    if not query or not query.strip():
        return {
            "success": False,
            "message": "No search query provided.",
            "data": [],
            "error": "EmptyQuery"
        }

    query = query.strip()
    results = []

    # 1. Search Wikipedia Encyclopedia
    try:
        wiki_titles = wikipedia.search(query, results=min(3, max_results))
        for title in wiki_titles:
            try:
                summary = wikipedia.summary(title, sentences=3, auto_suggest=False)
                page = wikipedia.page(title, auto_suggest=False)
                results.append({
                    "title": title,
                    "snippet": summary,
                    "url": page.url,
                    "source": "Wikipedia"
                })
            except Exception:
                continue
    except Exception as e:
        print(f"Wikipedia search warning: {e}")

    # 2. Search DuckDuckGo Instant Answer API
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=8)
        if res.status_code == 200:
            data = res.json()
            abstract = data.get("AbstractText")
            if abstract:
                results.append({
                    "title": data.get("Heading") or query,
                    "snippet": abstract,
                    "url": data.get("AbstractURL") or "https://duckduckgo.com",
                    "source": "DuckDuckGo"
                })

            for topic in data.get("RelatedTopics", []):
                if len(results) >= max_results:
                    break
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({
                        "title": topic.get("Text", "")[:60],
                        "snippet": topic.get("Text"),
                        "url": topic.get("FirstURL", ""),
                        "source": "DuckDuckGo"
                    })
    except Exception as e:
        print(f"DuckDuckGo search warning: {e}")

    # Format result message
    if results:
        summary_text = f"Found {len(results)} search results for '{query}'."
        return {
            "success": True,
            "status": "success",
            "message": summary_text,
            "query": query,
            "data": {
                "query": query,
                "results": results[:max_results]
            },
            "error": None
        }

    return {
        "success": False,
        "status": "error",
        "message": f"No direct search results found for '{query}'.",
        "query": query,
        "data": {"query": query, "results": []},
        "error": "NoResults"
    }


def fetch_web_page(url: str, max_chars: int = 5000):
    """
    Fetch and extract main article text from a web URL.
    """
    if not url or not url.strip():
        return {
            "success": False,
            "message": "No URL provided.",
            "data": None,
            "error": "EmptyURL"
        }

    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if res.status_code != 200:
            return {
                "success": False,
                "message": f"Failed to load web page (HTTP {res.status_code})",
                "data": None,
                "error": f"HTTPError_{res.status_code}"
            }

        soup = BeautifulSoup(res.text, "html.parser")

        # Strip scripts, styles, and unwanted elements
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else url

        # Extract text blocks
        paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 30]
        text_content = "\n\n".join(paragraphs)

        if not text_content:
            text_content = soup.get_text(separator=" ", strip=True)

        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + "\n...[truncated]"

        return {
            "success": True,
            "message": f"Successfully extracted text from '{title}'",
            "data": {
                "url": url,
                "title": title,
                "content": text_content,
                "length": len(text_content)
            },
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to fetch web page: {str(e)}",
            "data": None,
            "error": str(e)
        }