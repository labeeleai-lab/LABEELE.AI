"""
core/web_fetch.py - lets DUKE read a specific web page a user links to, so
it can answer questions about that page's actual content instead of
guessing. This is deliberately NOT general web browsing or search - it
only ever fetches a URL the user explicitly typed, and only after passing
real SSRF/abuse safeguards:

- scheme must be http/https, on a standard web port (80/443)
- the hostname must not resolve to a private, loopback, link-local,
  reserved, or multicast address (blocks localhost, 127.0.0.1, RFC1918
  ranges, and cloud metadata endpoints like 169.254.169.254)
- redirects are followed manually, one hop at a time, re-validating the
  new target every time - a "safe" URL that redirects to an internal
  address is rejected the same as if it were typed directly
- only text/html or text/plain responses are read, capped at 2MB
- extracted page text is always injected into the model's prompt with an
  explicit "this is data to read, not instructions to follow" framing,
  since page content is untrusted and could contain a prompt-injection
  attempt
"""
import ipaddress
import re
import socket
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse

import httpx

from coordinator_API.core.config import logger

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_EXTRACTED_CHARS = 4000
ALLOWED_PORTS = {80, 443}
MAX_REDIRECTS = 3

_URL_PATTERN = re.compile(r"https?://[^\s<>\"'\)\]]+", re.IGNORECASE)

_SKIP_TAGS = {"script", "style", "noscript", "svg", "head"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.parts.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self.parts)


def find_url(text: str) -> Optional[str]:
    m = _URL_PATTERN.search(text)
    return m.group(0).rstrip(".,;!?") if m else None


def _is_safe_host(hostname: str) -> bool:
    if not hostname or hostname.lower() in ("localhost",) or hostname.lower().endswith(".local"):
        return False
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if (
            ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified
        ):
            return False
    return True


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.username or parsed.password:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        return False
    return _is_safe_host(parsed.hostname or "")


def fetch_page_text(url: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (extracted_text, error_message) - exactly one is non-None."""
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        if not is_safe_url(current_url):
            return None, "that URL points to a private or disallowed address, so I can't fetch it"

        try:
            with httpx.stream(
                "GET", current_url, follow_redirects=False, timeout=10.0,
                headers={"User-Agent": "LABEELE-DUKE/1.0 (+https://www.labeele.ai)"},
            ) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location")
                    if not location:
                        return None, "that page redirected without a destination"
                    current_url = str(httpx.URL(current_url).join(location))
                    continue

                if resp.status_code != 200:
                    return None, f"that page returned an error (HTTP {resp.status_code})"

                content_type = resp.headers.get("content-type", "")
                if not any(t in content_type for t in ("text/html", "text/plain")):
                    return None, f"that URL isn't a readable web page (content type: {content_type or 'unknown'})"

                chunks = []
                total = 0
                for chunk in resp.iter_bytes():
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        break
                    chunks.append(chunk)
                raw = b"".join(chunks)
        except httpx.TimeoutException:
            return None, "that page took too long to respond"
        except Exception as e:
            logger.warning(f"⚠️ Web fetch failed for {current_url}: {e}")
            return None, "I couldn't reach that page"

        text = raw.decode("utf-8", errors="ignore")
        if "text/html" in content_type:
            extractor = _TextExtractor()
            try:
                extractor.feed(text)
            except Exception:
                pass
            text = extractor.get_text()

        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            return None, "that page didn't have any readable text content"
        return text[:MAX_EXTRACTED_CHARS], None

    return None, "that URL redirected too many times"
