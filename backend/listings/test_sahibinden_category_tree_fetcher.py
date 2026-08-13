import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sahibinden_category_tree_fetcher.py"
SPEC = importlib.util.spec_from_file_location("sahibinden_category_tree_fetcher", SCRIPT_PATH)
fetcher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(fetcher)


class SahibindenCategoryTreeFetcherTests(unittest.TestCase):
    def test_fetch_public_url_rejects_non_http_schemes(self):
        with self.assertRaises(ValueError) as context:
            fetcher.fetch_public_url("file:///etc/passwd")
        self.assertIn("Invalid scheme: file", str(context.exception))

        with self.assertRaises(ValueError) as context:
            fetcher.fetch_public_url("ftp://example.com/file")
        self.assertIn("Invalid scheme: ftp", str(context.exception))

    def test_sitemap_xml_parsing(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://www.sahibinden.com/vasita</loc></url>
          <url><loc>https://www.sahibinden.com/vasita/otomobil</loc></url>
          <url><loc>https://www.sahibinden.com/ilan/vasita-otomobil-demo</loc></url>
        </urlset>
        """

        urls = fetcher.extract_urls_from_sitemap_xml(xml)

        self.assertEqual(
            urls,
            [
                "https://www.sahibinden.com/vasita",
                "https://www.sahibinden.com/vasita/otomobil",
            ],
        )

    def test_site_haritasi_html_parsing(self):
        html = """
        <html><body>
          <a href="/vasita">Vasıta</a>
          <a href="https://www.sahibinden.com/emlak/konut">Konut</a>
          <a href="/ilan/secret">Listing should be ignored</a>
        </body></html>
        """

        urls, labels = fetcher.parse_site_haritasi_html(html)

        self.assertIn("https://www.sahibinden.com/vasita", urls)
        self.assertIn("https://www.sahibinden.com/emlak/konut", urls)
        self.assertNotIn("https://www.sahibinden.com/ilan/secret", urls)
        self.assertEqual(labels["https://www.sahibinden.com/vasita"], "Vasıta")

    def test_normalization_into_internal_json_shape(self):
        tree = fetcher.build_tree_from_urls(
            [
                "https://www.sahibinden.com/vasita",
                "https://www.sahibinden.com/vasita/otomobil",
            ],
            source="sitemap",
            label_by_url={"https://www.sahibinden.com/vasita": "Vasıta"},
        )

        self.assertEqual(len(tree), 1)
        root = tree[0]
        self.assertEqual(root["name"], "Vasıta")
        self.assertEqual(root["slug"], "vasita")
        self.assertEqual(root["url"], "https://www.sahibinden.com/vasita")
        self.assertIsNone(root["listing_count"])
        self.assertEqual(root["source"], "sitemap")
        self.assertEqual(root["children"][0]["slug"], "otomobil")

    def test_blocked_response_handling_for_status_codes(self):
        for status_code in (401, 403, 429):
            blocked, reason = fetcher.detect_blocked_response(status_code, "blocked")
            self.assertTrue(blocked)
            self.assertIn(str(status_code), reason)

    def test_captcha_recaptcha_challenge_detection(self):
        examples = [
            "<html>captcha required</html>",
            "<div class='g-recaptcha'></div>",
            "<form id='challenge-form'></form>",
        ]

        for body in examples:
            blocked, reason = fetcher.detect_blocked_response(200, body)
            self.assertTrue(blocked)
            self.assertIn("challenge_detected", reason)

    def test_existing_schema_files_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "backend" / "listings" / "data"
            data_dir.mkdir(parents=True)

            schema_path = data_dir / "category_attribute_schema.json"
            candidates_path = data_dir / "sahibinden_attribute_candidates.json"
            schema_path.write_text('{"schema": "keep"}', encoding="utf-8")
            candidates_path.write_text('{"candidates": "keep"}', encoding="utf-8")

            fixture_path = root / "fixture.xml"
            fixture_path.write_text(
                """<urlset>
                  <url><loc>https://www.sahibinden.com/vasita</loc></url>
                  <url><loc>https://www.sahibinden.com/vasita/otomobil</loc></url>
                </urlset>""",
                encoding="utf-8",
            )

            tree_path = data_dir / "sahibinden_category_tree.json"
            urls_path = data_dir / "sahibinden_category_urls.json"

            fetcher.run_from_local_fixtures(
                sitemap_xml_paths=[str(fixture_path)],
                site_haritasi_html_path=None,
                output_tree=str(tree_path),
                output_urls=str(urls_path),
            )

            self.assertEqual(schema_path.read_text(encoding="utf-8"), '{"schema": "keep"}')
            self.assertEqual(candidates_path.read_text(encoding="utf-8"), '{"candidates": "keep"}')
            self.assertTrue(tree_path.exists())
            self.assertTrue(urls_path.exists())

            payload = json.loads(tree_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["categories"][0]["slug"], "vasita")


if __name__ == "__main__":
    unittest.main()
