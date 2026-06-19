
import argparse
import html
import json
import re
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)\b[^>]*>.*?</\1>", re.I | re.S)
TURKISH_MAP = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "i": "i", "ö": "o", "ş": "s", "ü": "u",
    "Ç": "c", "Ğ": "g", "İ": "i", "I": "i", "Ö": "o", "Ş": "s", "Ü": "u",
    "²": "2",
})

NOISE_LABELS = {
    "favori arama adı",
    "favori satıcı adı",
    "günlük bildirim ayarları",
    "ilan no",
    "ilan tarihi",
    "ilanın yayınlandığı fiyat",
    "toplam yıllık mtv",
}
NOISE_VALUE_PAIRS = {
    ("yaş", "tutar"),
}
NOISE_PREFIXES = (
    "toplam yıllık mtv",
)
BOOL_TRUE = {"evet", "var", "yes", "true", "1"}
BOOL_FALSE = {"hayır", "hayir", "yok", "no", "false", "0"}
FORCE_TEXT_KEYS = {"marka", "seri", "model", "site_adi"}
FORCE_NUMBER_KEYS = {
    "yil", "km", "m2_brut", "m2_net", "banyo_sayisi", "kat_sayisi", "aidat_tl",
}
KEY_OVERRIDES = {
    "m² (brüt)": "m2_brut",
    "m2 (brüt)": "m2_brut",
    "m² (net)": "m2_net",
    "m2 (net)": "m2_net",
    "km": "km",
    "yıl": "yil",
    "yakıt tipi": "yakit_tipi",
    "vites": "vites",
    "araç durumu": "arac_durumu",
    "ağır hasar kayıtlı": "agir_hasar_kayitli",
    "oda sayısı": "oda_sayisi",
    "bina yaşı": "bina_yasi",
    "bulunduğu kat": "bulundugu_kat",
    "banyo sayısı": "banyo_sayisi",
    "krediye uygun": "krediye_uygun",
    "site içerisinde": "site_icerisinde",
    "aidat (tl)": "aidat_tl",
}

NOISE_KEYS = {
    "favori_arama_adi",
    "favori_satici_adi",
    "gunluk_bildirim_ayarlari",
    "ilan_no",
    "ilan_tarihi",
    "ilanin_yayinlandigi_fiyat",
    "yas",
}


def normalize_for_matching(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.translate(TURKISH_MAP).lower()
    value = re.sub(r"\s+", " ", value).strip()
    return value


def strip_html(fragment):
    fragment = SCRIPT_STYLE_RE.sub(" ", fragment or "")
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    text = TAG_RE.sub(" ", fragment)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def clean_label(value):
    value = strip_html(value)
    value = re.sub(r"[:：]+$", "", value).strip()
    if not value or len(value) > 90:
        return ""
    if not re.search(r"[A-Za-zÀ-ž0-9]", value):
        return ""
    return value

def clean_value(value):
    value = strip_html(value)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > 260:
        value = value[:260].rstrip() + "..."
    return value

def slugify(label):
    lowered = normalize_for_matching(label)
    override = KEY_OVERRIDES.get(label.strip().lower()) or KEY_OVERRIDES.get(lowered)
    if override:
        return override
    text = lowered.translate(TURKISH_MAP)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "attribute"

def is_noise(label, value):
    label_norm = normalize_for_matching(label)
    value_norm = normalize_for_matching(value)
    label_key = slugify(label)

    if label_norm in {normalize_for_matching(item) for item in NOISE_LABELS}:
        return True
    if label_key in NOISE_KEYS:
        return True
    if (label_norm, value_norm) in {(normalize_for_matching(a), normalize_for_matching(b)) for a, b in NOISE_VALUE_PAIRS}:
        return True
    if any(label_norm.startswith(normalize_for_matching(prefix)) for prefix in NOISE_PREFIXES):
        return True
    if re.fullmatch(r"\d+\s*-\s*\d+", label_norm):
        return True
    if "favori" in label_norm or "bildirim" in label_norm:
        return True
    if "tl x" in value_norm and ("yas" in label_key or "mtv" in label_key):
        return True
    if len(value) > 180 and ("hata olustu" in value_norm or "formu kontrol" in value_norm):
        return True
    return False

def extract_title(page_html):
    for pattern in [r"<h1\b[^>]*>(.*?)</h1>", r"<title\b[^>]*>(.*?)</title>"]:
        match = re.search(pattern, page_html, re.I | re.S)
        if match:
            return strip_html(match.group(1))
    return ""

def extract_canonical_url(page_html):
    patterns = [
        r"<link\b[^>]*rel=[\"']canonical[\"'][^>]*href=[\"']([^\"']+)[\"']",
        r"<meta\b[^>]*property=[\"']og:url[\"'][^>]*content=[\"']([^\"']+)[\"']",
    ]
    for pattern in patterns:
        match = re.search(pattern, page_html, re.I)
        if match:
            return html.unescape(match.group(1))
    return ""

def extract_pairs(page_html):
    pairs = []
    patterns = [
        r"<li\b[^>]*>\s*<(?:strong|label|span)\b[^>]*>(.*?)</(?:strong|label|span)>\s*(.*?)</li>",
        r"<tr\b[^>]*>.*?<(?:th|td)\b[^>]*>(.*?)</(?:th|td)>.*?<(?:td|th)\b[^>]*>(.*?)</(?:td|th)>.*?</tr>",
        r"<dt\b[^>]*>(.*?)</dt>\s*<dd\b[^>]*>(.*?)</dd>",
    ]
    for pattern in patterns:
        for raw_label, raw_value in re.findall(pattern, page_html, re.I | re.S):
            label = clean_label(raw_label)
            value = clean_value(raw_value)
            if not label or not value or label == value:
                continue
            if is_noise(label, value):
                continue
            pairs.append((label, value))
    deduped = []
    seen = set()
    for label, value in pairs:
        key = (label.casefold(), value.casefold())
        if key not in seen:
            seen.add(key)
            deduped.append((label, value))
    return deduped

def guess_category_display_name(category_key):
    return category_key.replace("_", " ").strip().title()

def infer_input_type(key, values):
    norm_values = [normalize_for_matching(str(v)) for v in values if str(v).strip()]
    unique = sorted(set(norm_values))

    if key in FORCE_TEXT_KEYS:
        return "text"
    if key in FORCE_NUMBER_KEYS:
        return "number"
    if unique and all(v in BOOL_TRUE or v in BOOL_FALSE for v in unique):
        return "boolean"

    numeric_like = 0
    for value in norm_values:
        if re.fullmatch(r"[0-9 .,-]+", value):
            cleaned = value.replace(".", "").replace(",", ".").strip()
            if cleaned and re.fullmatch(r"-?\d+(\.\d+)?", cleaned):
                numeric_like += 1

    if norm_values and numeric_like == len(norm_values):
        return "number"
    if 1 < len(unique) <= 16 and all(len(v) <= 50 for v in unique):
        return "choice"
    return "text"

def summarize_source(path):
    page_html = path.read_text(encoding="utf-8", errors="ignore")
    pairs = extract_pairs(page_html)
    grouped = defaultdict(lambda: {"count": 0, "sample_values": []})
    for label, value in pairs:
        grouped[label]["count"] += 1
        if value not in grouped[label]["sample_values"] and len(grouped[label]["sample_values"]) < 20:
            grouped[label]["sample_values"].append(value)
    attributes = []
    for label in sorted(grouped.keys(), key=lambda item: item.casefold()):
        key = slugify(label)
        values = grouped[label]["sample_values"]
        attributes.append({
            "key": key,
            "label": label,
            "input_type": infer_input_type(key, values),
            "required": False,
            "count": grouped[label]["count"],
            "sample_values": values,
        })
    return {
        "file": str(path),
        "category_key": path.stem,
        "display_name": guess_category_display_name(path.stem),
        "title": extract_title(page_html),
        "canonical_url": extract_canonical_url(page_html),
        "attribute_count": len(attributes),
        "attributes": attributes,
    }

def merge_global_labels(sources):
    merged = defaultdict(lambda: {"source_count": 0, "sample_values": [], "labels": set()})
    for source in sources:
        seen_keys = set()
        for attr in source["attributes"]:
            key = attr["key"]
            if key not in seen_keys:
                merged[key]["source_count"] += 1
                seen_keys.add(key)
            merged[key]["labels"].add(attr["label"])
            for value in attr["sample_values"]:
                if value not in merged[key]["sample_values"] and len(merged[key]["sample_values"]) < 20:
                    merged[key]["sample_values"].append(value)
    output = []
    for key, data in sorted(merged.items(), key=lambda item: item[0]):
        label = sorted(data["labels"], key=len)[0]
        output.append({
            "key": key,
            "label": label,
            "source_count": data["source_count"],
            "sample_values": data["sample_values"],
        })
    return output

def build_schema(sources):
    return {
        "version": 1,
        "description": "Local category attribute schema generated from user-saved reference HTML. Do not commit raw reference HTML.",
        "categories": [
            {
                "key": source["category_key"],
                "name": source["display_name"],
                "source_title": source["title"],
                "source_url": source["canonical_url"],
                "attributes": [
                    {
                        "key": attr["key"],
                        "label": attr["label"],
                        "input_type": attr["input_type"],
                        "required": attr["required"],
                        "sample_values": attr["sample_values"],
                    }
                    for attr in source["attributes"]
                ],
            }
            for source in sources
        ],
        "global_attributes": merge_global_labels(sources),
    }

def iter_local_files(input_dir):
    input_dir = Path(input_dir)
    if not input_dir.exists():
        return []

    ignored_stems = {"f", "saved_resource", "index", "resource"}
    files = []

    # Only read the files saved directly in backend/reference_html/sahibinden.
    # Browser "Webpage, Complete" asset folders contain helper HTML files that are not categories.
    for pattern in ("*.html", "*.htm", "*.txt"):
        for path in input_dir.glob(pattern):
            stem = re.sub(r"\(\d+\)$", "", path.stem).strip().lower()
            if stem in ignored_stems:
                continue
            files.append(path)

    return sorted(files)

def fetch_url(url, delay_seconds=1.5):
    time.sleep(delay_seconds)
    req = urllib.request.Request(url, headers={"User-Agent": "classifieds-local-category-schema/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()

def fetch_category_sitemaps(output_path: str):
    # Optional remote discovery helper. Some environments receive 403 from sahibinden.
    # In that case, write a structured result instead of raising a traceback.
    import json as _json
    import re as _re
    from pathlib import Path as _Path

    result = {
        "status": "not_started",
        "reason": "",
        "sitemap_count": 0,
        "url_count": 0,
        "sitemaps": [],
        "urls": [],
        "sitemap_errors": [],
    }

    def write_result():
        output = _Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(_json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    try:
        robots = fetch_url("https://www.sahibinden.com/robots.txt", delay_seconds=0)
        if isinstance(robots, bytes):
            robots = robots.decode("utf-8", errors="replace")
    except Exception as exc:
        result["status"] = "blocked_or_unavailable"
        result["reason"] = f"{type(exc).__name__}: {exc}"
        return write_result()

    sitemap_urls = []
    for raw_line in robots.splitlines():
        line = raw_line.strip()
        if not line.lower().startswith("sitemap:"):
            continue
        sitemap_url = line.split(":", 1)[1].strip()
        lowered = sitemap_url.lower()
        if "categor" in lowered or "kategori" in lowered:
            sitemap_urls.append(sitemap_url)

    result["sitemaps"] = sorted(set(sitemap_urls))
    result["sitemap_count"] = len(result["sitemaps"])

    category_urls = []
    for sitemap_url in result["sitemaps"]:
        try:
            sitemap_body = fetch_url(sitemap_url, delay_seconds=1)
            if isinstance(sitemap_body, bytes):
                sitemap_body = sitemap_body.decode("utf-8", errors="replace")
        except Exception as exc:
            result["sitemap_errors"].append({
                "url": sitemap_url,
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue

        for match in _re.findall(r"<loc>(.*?)</loc>", sitemap_body, flags=_re.IGNORECASE | _re.DOTALL):
            loc = match.strip()
            if not loc:
                continue
            if "/ilan/" in loc or "/listing/" in loc:
                continue
            if "sahibinden.com" in loc:
                category_urls.append(loc)

    result["urls"] = sorted(set(category_urls))
    result["url_count"] = len(result["urls"])

    if result["urls"]:
        result["status"] = "ok"
    elif result["sitemaps"]:
        result["status"] = "no_category_urls_found"
    else:
        result["status"] = "no_category_sitemaps_found"

    return write_result()

def main():
    parser = argparse.ArgumentParser(description="Build a local category attribute schema from saved HTML and optionally allowed category sitemaps.")
    parser.add_argument("--input", default="backend/reference_html/sahibinden")
    parser.add_argument("--candidates-output", default="backend/listings/data/sahibinden_attribute_candidates.json")
    parser.add_argument("--schema-output", default="backend/listings/data/category_attribute_schema.json")
    parser.add_argument("--fetch-category-sitemaps", action="store_true")
    parser.add_argument("--category-sitemap-output", default="backend/listings/data/sahibinden_category_urls.json")
    args = parser.parse_args()

    if args.fetch_category_sitemaps:
        result = fetch_category_sitemaps(args.category_sitemap_output)
        print("Fetched category sitemap data:", args.category_sitemap_output)
        print("status", result.get("status"))
        print("reason", result.get("reason"))
        print("sitemap_count", result.get("sitemap_count"))
        print("url_count", result.get("url_count"))
        return
    files = iter_local_files(args.input)
    sources = [source for source in (summarize_source(path) for path in files) if source["attribute_count"] > 0]
    candidates = {
        "source_count": len(sources),
        "sources": sources,
        "all_attribute_labels": merge_global_labels(sources),
    }
    schema = build_schema(sources)

    Path(args.candidates_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.schema_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.candidates_output).write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.schema_output).write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Processed", len(files), "local file(s).")
    print("Candidates written to:", args.candidates_output)
    print("Schema written to:", args.schema_output)
    for source in sources:
        print(source["category_key"], source["attribute_count"])

if __name__ == "__main__":
    main()
