#!/usr/bin/env python3
"""
Safe sahibinden category tree fetcher.

Rules:
- No internal AJAX endpoints.
- No login cookies, proxies, CAPTCHA bypass, browser spoofing, or anti-bot bypass.
- No listing/user/price/media scraping.
- Uses only robots.txt-discovered sitemap XML and /site-haritasi/ when accessible.
- Exits cleanly with structured JSON when blocked or challenged.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import defusedxml.ElementTree as ET
from defusedxml.common import DefusedXmlException
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

BASE_URL = "https://www.sahibinden.com"
DEFAULT_OUTPUT_TREE = "backend/listings/data/sahibinden_category_tree.json"
DEFAULT_OUTPUT_URLS = "backend/listings/data/sahibinden_category_urls.json"

BLOCKED_STATUS_CODES = {401, 403, 429}
CHALLENGE_PATTERNS = (
    "captcha",
    "recaptcha",
    "g-recaptcha",
    "hcaptcha",
    "cf-challenge",
    "cloudflare",
    "challenge-form",
    "access denied",
    "verify you are human",
    "bot detection",
    "robot check",
)


def detect_blocked_response(status_code: int, body: str = "") -> Tuple[bool, str]:
    if status_code in BLOCKED_STATUS_CODES:
        return True, f"blocked_http_{status_code}"

    lowered = (body or "").lower()
    for pattern in CHALLENGE_PATTERNS:
        if pattern in lowered:
            return True, f"challenge_detected:{pattern}"

    return False, ""


def slugify(value: str) -> str:
    value = (value or "").strip()
    replacements = {
        "ı": "i",
        "İ": "i",
        "ş": "s",
        "Ş": "s",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.replace("-", " ").split())


def normalize_sahibinden_url(url: str, base_url: str = BASE_URL) -> Optional[str]:
    if not url:
        return None

    absolute = urllib.parse.urljoin(base_url + "/", url.strip())
    parsed = urllib.parse.urlparse(absolute)

    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc.lower() not in {"www.sahibinden.com", "sahibinden.com"}:
        return None

    path = parsed.path.rstrip("/")
    if not path:
        return None

    disallowed_prefixes = (
        "/ilan",
        "/listing",
        "/arama",
        "/kelime-ile-arama",
        "/accounts",
        "/secure",
        "/api",
        "/ajax",
    )
    if any(path.startswith(prefix) for prefix in disallowed_prefixes):
        return None

    disallowed_extensions = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".css",
        ".js",
        ".ico",
        ".xml",
        ".txt",
        ".pdf",
    )
    if path.lower().endswith(disallowed_extensions):
        return None

    return urllib.parse.urlunparse(("https", "www.sahibinden.com", path, "", "", ""))


def category_path_parts(url: str) -> List[str]:
    parsed = urllib.parse.urlparse(url)
    return [part for part in parsed.path.strip("/").split("/") if part]


def node_template(name: str, slug: str, url: str, source: str) -> Dict[str, object]:
    return {
        "name": name,
        "slug": slug,
        "url": url,
        "listing_count": None,
        "source": source,
        "children": [],
    }


def build_tree_from_urls(
    urls: Sequence[str],
    source: str,
    label_by_url: Optional[Dict[str, str]] = None,
) -> List[Dict[str, object]]:
    label_by_url = label_by_url or {}
    roots: List[Dict[str, object]] = []
    node_by_url: Dict[str, Dict[str, object]] = {}

    for raw_url in sorted(set(urls)):
        url = normalize_sahibinden_url(raw_url)
        if not url:
            continue

        parts = category_path_parts(url)
        if not parts:
            continue

        parent_children = roots
        running_parts: List[str] = []

        for part in parts:
            running_parts.append(part)
            current_url = "https://www.sahibinden.com/" + "/".join(running_parts)
            slug = slugify(part)
            label = label_by_url.get(current_url) or title_from_slug(part)

            if current_url not in node_by_url:
                node = node_template(label, slug, current_url, source)
                node_by_url[current_url] = node
                parent_children.append(node)
            else:
                node = node_by_url[current_url]
                if label_by_url.get(current_url):
                    node["name"] = label_by_url[current_url]

            parent_children = node["children"]  # type: ignore[assignment]

    return roots


def extract_urls_from_sitemap_xml(xml_text: str, base_url: str = BASE_URL) -> List[str]:
    xml_text = xml_text or ""
    urls: List[str] = []

    try:
        root = ET.fromstring(xml_text)
    except (ET.ParseError, DefusedXmlException):
        for match in re.findall(r"<loc>(.*?)</loc>", xml_text, flags=re.IGNORECASE | re.DOTALL):
            normalized = normalize_sahibinden_url(match.strip(), base_url=base_url)
            if normalized:
                urls.append(normalized)
        return sorted(set(urls))

    for element in root.iter():
        tag = element.tag.split("}", 1)[-1].lower()
        if tag != "loc":
            continue
        normalized = normalize_sahibinden_url((element.text or "").strip(), base_url=base_url)
        if normalized:
            urls.append(normalized)

    return sorted(set(urls))


def extract_sitemap_urls_from_robots(robots_text: str) -> List[str]:
    sitemap_urls: List[str] = []
    for raw_line in (robots_text or "").splitlines():
        line = raw_line.strip()
        if not line.lower().startswith("sitemap:"):
            continue
        sitemap_url = line.split(":", 1)[1].strip()
        if sitemap_url:
            sitemap_urls.append(sitemap_url)
    return sorted(set(sitemap_urls))


def robots_disallows_path(robots_text: str, path: str, user_agent: str = "*") -> bool:
    active = False
    disallows: List[str] = []

    for raw_line in (robots_text or "").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if line.lower().startswith("user-agent:"):
            value = line.split(":", 1)[1].strip().lower()
            active = value == "*" or value == user_agent.lower()
            continue

        if active and line.lower().startswith("disallow:"):
            value = line.split(":", 1)[1].strip()
            if value:
                disallows.append(value)

    return any(path.startswith(rule.rstrip("*")) for rule in disallows if rule)


class SiteHaritasiParser(HTMLParser):
    def __init__(self, base_url: str = BASE_URL) -> None:
        super().__init__()
        self.base_url = base_url
        self._active_href: Optional[str] = None
        self._active_text: List[str] = []
        self.urls: List[str] = []
        self.labels: Dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = {name.lower(): value for name, value in attrs}
        href = attrs_dict.get("href")
        normalized = normalize_sahibinden_url(href or "", base_url=self.base_url)
        if normalized:
            self._active_href = normalized
            self._active_text = []

    def handle_data(self, data: str) -> None:
        if self._active_href:
            self._active_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._active_href:
            return

        label = " ".join("".join(self._active_text).split())
        self.urls.append(self._active_href)
        if label:
            self.labels[self._active_href] = label

        self._active_href = None
        self._active_text = []


def parse_site_haritasi_html(html_text: str, base_url: str = BASE_URL) -> Tuple[List[str], Dict[str, str]]:
    parser = SiteHaritasiParser(base_url=base_url)
    parser.feed(html_text or "")
    return sorted(set(parser.urls)), parser.labels


def fetch_public_url(url: str, timeout: int = 20) -> Tuple[int, str, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"Invalid scheme: {scheme}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "classifieds-local-category-tree-fetcher/1.0",
            "Accept": "text/html,application/xml,text/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            body = raw_body.decode(charset, errors="replace")
            return int(response.status), body, response.geturl()
    except urllib.error.HTTPError as exc:
        raw_body = exc.read() if hasattr(exc, "read") else b""
        body = raw_body.decode("utf-8", errors="replace")
        return int(exc.code), body, url
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network_error:{exc}") from exc


def write_json(path: str, payload: object) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_outputs(
    output_tree: str,
    output_urls: str,
    status: str,
    reason: str,
    urls: Sequence[str],
    categories: Sequence[Dict[str, object]],
    source: str,
) -> Dict[str, object]:
    unique_urls = sorted(set(urls))
    category_list = list(categories)
    url_payload = {
        "status": status,
        "reason": reason,
        "source": source,
        "url_count": len(unique_urls),
        "urls": unique_urls,
    }
    tree_payload: Dict[str, object] = {
        "status": status,
        "reason": reason,
        "source": source,
        "category_count": len(category_list),
        "categories": category_list,
    }

    write_json(output_urls, url_payload)
    write_json(output_tree, tree_payload)
    return tree_payload


def run_from_local_fixtures(
    sitemap_xml_paths: Sequence[str],
    site_haritasi_html_path: Optional[str],
    output_tree: str,
    output_urls: str,
) -> Dict[str, object]:
    urls: List[str] = []
    labels: Dict[str, str] = {}
    source = "sitemap"

    for path in sitemap_xml_paths:
        urls.extend(extract_urls_from_sitemap_xml(Path(path).read_text(encoding="utf-8")))

    if site_haritasi_html_path:
        html_urls, html_labels = parse_site_haritasi_html(Path(site_haritasi_html_path).read_text(encoding="utf-8"))
        urls.extend(html_urls)
        labels.update(html_labels)
        if not sitemap_xml_paths:
            source = "site-haritasi"

    categories = build_tree_from_urls(urls, source=source, label_by_url=labels)
    return write_outputs(output_tree, output_urls, "ok", "", sorted(set(urls)), categories, source)


def run_live(args: argparse.Namespace) -> Dict[str, object]:
    robots_url = urllib.parse.urljoin(args.base_url + "/", "robots.txt")
    site_haritasi_url = urllib.parse.urljoin(args.base_url + "/", "site-haritasi/")

    try:
        robots_status, robots_body, _ = fetch_public_url(robots_url, timeout=args.timeout)
    except RuntimeError as exc:
        return write_outputs(args.output_tree, args.output_urls, "network_error", str(exc), [], [], "none")

    blocked, reason = detect_blocked_response(robots_status, robots_body)
    if blocked:
        return write_outputs(args.output_tree, args.output_urls, "blocked_or_unavailable", reason, [], [], "robots")

    sitemap_urls = extract_sitemap_urls_from_robots(robots_body)
    urls: List[str] = []

    for sitemap_url in sitemap_urls:
        time.sleep(max(args.delay, 0))
        status, body, _ = fetch_public_url(sitemap_url, timeout=args.timeout)
        blocked, reason = detect_blocked_response(status, body)
        if blocked:
            return write_outputs(args.output_tree, args.output_urls, "blocked_or_unavailable", reason, [], [], "sitemap")
        if 200 <= status < 300:
            urls.extend(extract_urls_from_sitemap_xml(body, base_url=args.base_url))

    if urls:
        categories = build_tree_from_urls(urls, source="sitemap")
        return write_outputs(args.output_tree, args.output_urls, "ok", "", sorted(set(urls)), categories, "sitemap")

    if robots_disallows_path(robots_body, "/site-haritasi/"):
        return write_outputs(args.output_tree, args.output_urls, "robots_disallow", "/site-haritasi/ disallowed", [], [], "robots")

    status, body, _ = fetch_public_url(site_haritasi_url, timeout=args.timeout)
    blocked, reason = detect_blocked_response(status, body)
    if blocked:
        return write_outputs(args.output_tree, args.output_urls, "blocked_or_unavailable", reason, [], [], "site-haritasi")
    if not (200 <= status < 300):
        return write_outputs(args.output_tree, args.output_urls, "blocked_or_unavailable", f"http_{status}", [], [], "site-haritasi")

    html_urls, labels = parse_site_haritasi_html(body, base_url=args.base_url)
    categories = build_tree_from_urls(html_urls, source="site-haritasi", label_by_url=labels)
    return write_outputs(args.output_tree, args.output_urls, "ok", "", html_urls, categories, "site-haritasi")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely fetch or parse sahibinden category tree data.")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--output-tree", default=DEFAULT_OUTPUT_TREE)
    parser.add_argument("--output-urls", default=DEFAULT_OUTPUT_URLS)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--local-sitemap-xml", action="append", default=[])
    parser.add_argument("--local-site-haritasi-html")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.local_sitemap_xml or args.local_site_haritasi_html:
        result = run_from_local_fixtures(
            sitemap_xml_paths=args.local_sitemap_xml,
            site_haritasi_html_path=args.local_site_haritasi_html,
            output_tree=args.output_tree,
            output_urls=args.output_urls,
        )
    else:
        result = run_live(args)

    print(json.dumps({
        "status": result.get("status"),
        "reason": result.get("reason"),
        "source": result.get("source"),
        "category_count": result.get("category_count"),
    }, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
