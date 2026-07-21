import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import networth_export as exporter
import networth_report


class FakeLocator:
    def __init__(self, page):
        self.page = page
        self.first = self

    def click(self):
        return None

    def screenshot(self, path):
        Path(path).write_bytes(b"image")


class FakePage:
    def __init__(self):
        self.wait_timeout_calls = []

    def evaluate(self, *args, **kwargs):
        return None

    def goto(self, url):
        self.url = url

    def wait_for_load_state(self, *args, **kwargs):
        return None

    def wait_for_function(self, *args, **kwargs):
        return None

    def wait_for_timeout(self, timeout):
        self.wait_timeout_calls.append(timeout)

    def locator(self, selector):
        return FakeLocator(self)

    def set_content(self, content):
        self.content = content

    def pdf(self, path, **kwargs):
        Path(path).write_bytes(b"pdf")


class FakeBrowser:
    def __init__(self, page):
        self.page = page

    def new_context(self, **kwargs):
        return FakeBrowserContext(self.page)

    def close(self):
        return None


class FakeBrowserContext:
    def __init__(self, page):
        self.page = page

    def new_page(self):
        return self.page


class FakeChromium:
    def __init__(self, page):
        self.page = page

    def launch(self, **kwargs):
        return FakeBrowser(self.page)


class FakePlaywright:
    def __init__(self, page):
        self.chromium = FakeChromium(page)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class NetworthExportPdfTests(unittest.TestCase):
    def test_generate_pdf_report_creates_file(self):
        records = [
            {
                "date": "01-01-26",
                "time": "10:00:00 AM",
                "networth": 100000.0,
                "assets": "Checking | Main | 50000\nSavings | Emergency | 50000",
                "liabilities": "Credit Card | Visa | 1000",
                "comments": "Initial snapshot",
            },
            {
                "date": "01-02-26",
                "time": "11:00:00 AM",
                "networth": 110000.0,
                "assets": "Checking | Main | 60000\nSavings | Emergency | 50000",
                "liabilities": "Credit Card | Visa | 1000",
                "comments": "Added value",
            },
        ]

        page = FakePage()
        fake_playwright = FakePlaywright(page)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.pdf"
            with patch("networth_report.sync_playwright", return_value=fake_playwright):
                exporter.generate_pdf_report(records, output_path)

            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)

    def test_generate_pdf_report_waits_10_seconds_for_page_load(self):
        records = [
            {
                "date": "01-01-26",
                "time": "10:00:00 AM",
                "networth": 100000.0,
                "assets": "Checking | Main | 50000",
                "liabilities": "Credit Card | Visa | 1000",
                "comments": "Initial snapshot",
            }
        ]
        page = FakePage()
        fake_playwright = FakePlaywright(page)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.pdf"
            with patch("networth_report.sync_playwright", return_value=fake_playwright):
                networth_report.generate_pdf_report(records, output_path)

            self.assertEqual(page.wait_timeout_calls[0], 10000)

    def test_generate_pdf_report_includes_total_networth_and_growth_sections(self):
        records = [
            {
                "date": "01-01-26",
                "time": "10:00:00 AM",
                "networth": 100000.0,
                "assets": "Checking | Main | 50000",
                "liabilities": "Credit Card | Visa | 1000",
                "comments": "Initial snapshot",
            },
            {
                "date": "01-02-26",
                "time": "11:00:00 AM",
                "networth": 110000.0,
                "assets": "Checking | Main | 60000",
                "liabilities": "Credit Card | Visa | 1000",
                "comments": "Added value",
            },
        ]
        page = FakePage()
        fake_playwright = FakePlaywright(page)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.pdf"
            with patch("networth_report.sync_playwright", return_value=fake_playwright):
                networth_report.generate_pdf_report(records, output_path)

            self.assertIn("Total Networth", page.content)
            self.assertIn("Networth Growth", page.content)
            self.assertIn("From:", page.content)
            self.assertIn("To:", page.content)


if __name__ == "__main__":
    unittest.main()
