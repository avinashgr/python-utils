#!/usr/bin/env python3
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - depends on environment
    sync_playwright = None


def parse_numeric(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0

    try:
        return float(text.replace(",", ""))
    except ValueError:
        return 0.0


def parse_breakdown(value):
    breakdown = {}
    if not value:
        return breakdown

    for line in str(value).splitlines():
        line = line.strip()
        if not line:
            continue

        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 3:
            continue

        name = parts[1] or parts[0]
        amount = parse_numeric(parts[2])
        if amount:
            breakdown[name] = breakdown.get(name, 0.0) + amount

    return breakdown


def format_currency(value):
    return f"${value:,.2f}"


def build_svg_line_chart(values, labels):
    if not values:
        return ""

    width = 720
    height = 260
    left = 50
    right = 20
    top = 20
    bottom = 40

    max_value = max(values) or 1
    min_value = min(values) or 0
    value_span = max_value - min_value or max_value or 1

    points = []
    for index, value in enumerate(values):
        if len(values) == 1:
            x = left + (width - left - right) / 2
        else:
            x = left + (index / (len(values) - 1)) * (width - left - right)

        if value_span == 0:
            y = top + (height - top - bottom) / 2
        else:
            normalized = (value - min_value) / value_span
            y = top + (1 - normalized) * (height - top - bottom)
        points.append((x, y))

    polyline_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    grid_lines = "".join(
        f'<line x1="{left}" y1="{top + index * ((height - top - bottom) / 4):.1f}" x2="{width - right}" y2="{top + index * ((height - top - bottom) / 4):.1f}" stroke="#e5e7eb" stroke-dasharray="4 4" />'
        for index in range(5)
    )

    label_markup = "".join(
        f'<text x="{left + (index / max(1, len(labels) - 1)) * (width - left - right):.1f}" y="{height - 10}" text-anchor="middle" font-size="11" fill="#6b7280">{escape(str(label))}</text>'
        for index, label in enumerate(labels)
    )

    return f"""
    <svg width="100%" height="260" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" rx="12" />
      {grid_lines}
      <polyline fill="none" stroke="#0f766e" stroke-width="3" points="{polyline_points}" />
      {label_markup}
    </svg>
    """


def build_svg_bar_chart(values):
    if not values:
        return ""

    width = 720
    height = 260
    left = 60
    right = 40
    top = 20
    bottom = 40

    max_value = max(values.values()) or 1
    chart_width = width - left - right
    chart_height = height - top - bottom
    bar_width = chart_width / max(1, len(values)) - 30

    bars = []
    for index, (label, amount) in enumerate(values.items()):
        bar_height = (amount / max_value) * chart_height if max_value else 0
        bar_x = left + index * (bar_width + 30)
        bar_y = top + chart_height - bar_height
        bars.append(
            f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="#14b8a6" rx="6" />'
            f'<text x="{bar_x + bar_width / 2:.1f}" y="{height - 10}" text-anchor="middle" font-size="11" fill="#6b7280">{escape(str(label))}</text>'
            f'<text x="{bar_x + bar_width / 2:.1f}" y="{bar_y - 8:.1f}" text-anchor="middle" font-size="11" fill="#0f172a">{format_currency(amount)}</text>'
        )

    return f"""
    <svg width="100%" height="260" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" rx="12" />
      {''.join(bars)}
    </svg>
    """


def build_networth_summary_html(records):
    if not records:
        return ""

    parsed_records = []
    for record in records:
        date_text = str(record.get("date", "")).strip()
        time_text = str(record.get("time", "")).strip()
        parsed_dt = None

        for candidate_format in ("%m-%d-%y %I:%M:%S %p", "%m-%d-%y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %I:%M:%S %p"):
            try:
                parsed_dt = datetime.strptime(f"{date_text} {time_text}", candidate_format)
                break
            except ValueError:
                continue

        if parsed_dt is None:
            parsed_dt = datetime.min

        parsed_records.append({**record, "_dt": parsed_dt})

    ordered_records = sorted(parsed_records, key=lambda record: record["_dt"])
    first = ordered_records[0]
    latest = ordered_records[-1]
    first_networth = parse_numeric(first.get("networth"))
    latest_networth = parse_numeric(latest.get("networth"))
    growth = latest_networth - first_networth
    growth_percent = ((growth / first_networth) * 100) if first_networth else 0.0

    return f"""
    <div class=\"grid\">
      <div class=\"card\"><h3>Total Networth</h3><p>From Networth (Assets-Liabilities)</p><strong>{format_currency(latest_networth)}</strong></div>
      <div class=\"card\"><h3>Networth Growth</h3><p>Growth In Networth</p><div>From: {escape(str(first.get('date','')))} ({format_currency(first_networth)})</div><div>To: {escape(str(latest.get('date','')))} ({format_currency(latest_networth)})</div><div style=\"margin-top: 5px; font-weight: bold;\">Change: {growth_percent:.2f}%</div></div>
    </div>
    """


def build_pdf_report_html(records):
    if not records:
        return """<!doctype html><html><head><meta charset=\"utf-8\"><title>Networth Report</title></head><body><h1>No data available</h1></body></html>"""

    latest = records[-1]
    previous = records[-2] if len(records) > 1 else None
    latest_networth = parse_numeric(latest.get("networth"))
    previous_networth = parse_numeric(previous.get("networth")) if previous else latest_networth
    net_change = latest_networth - previous_networth

    latest_assets = parse_breakdown(latest.get("assets"))
    latest_liabilities = parse_breakdown(latest.get("liabilities"))
    total_assets = sum(latest_assets.values())
    total_liabilities = sum(latest_liabilities.values())
    net_assets = total_assets - total_liabilities
    asset_vs_liability_chart = {"Assets": total_assets, "Liabilities": total_liabilities}

    dates = [record.get("date", "") for record in records]
    networth_values = [parse_numeric(record.get("networth")) for record in records]

    parsed_records = []
    for record in records:
        date_text = str(record.get("date", "")).strip()
        time_text = str(record.get("time", "")).strip()
        parsed_dt = None

        for candidate_format in ("%m-%d-%y %I:%M:%S %p", "%m-%d-%y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %I:%M:%S %p"):
            try:
                parsed_dt = datetime.strptime(f"{date_text} {time_text}", candidate_format)
                break
            except ValueError:
                continue

        if parsed_dt is None:
            parsed_dt = datetime.min

        parsed_records.append({**record, "_dt": parsed_dt})

    ordered_records = sorted(parsed_records, key=lambda record: record["_dt"])

    rows = []
    for record in ordered_records:
        rows.append(
            f"<tr><td>{escape(str(record.get('date','')))}</td><td>{escape(str(record.get('time','')))}</td><td>{escape(format_currency(parse_numeric(record.get('networth'))))}</td><td>{escape(str(record.get('assets','')))}</td><td>{escape(str(record.get('liabilities','')))}</td><td>{escape(str(record.get('comments','')))}</td></tr>"
        )

    summary_cards = f"""
    <div class=\"summary-grid\">
      <div class=\"card\"><h3>Latest Snapshot</h3><p>{escape(str(latest.get('date','')))} {escape(str(latest.get('time','')))}</p><strong>{format_currency(latest_networth)}</strong></div>
      <div class=\"card\"><h3>Assets</h3><p>Total recorded assets</p><strong>{format_currency(total_assets)}</strong></div>
      <div class=\"card\"><h3>Liabilities</h3><p>Total recorded liabilities</p><strong>{format_currency(total_liabilities)}</strong></div>
      <div class=\"card\"><h3>Net Position</h3><p>Assets minus liabilities</p><strong>{format_currency(net_assets)}</strong></div>
    </div>
    """

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Networth Report</title>
  <style>
    body {{ font-family: Arial, Helvetica, sans-serif; margin: 24px; color: #0f172a; }}
    h1 {{ margin-bottom: 8px; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 16px 0 24px; }}
    .card {{ border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; background: #f8fafc; }}
    .card strong {{ font-size: 20px; display: block; margin-top: 6px; }}
    .chart-section {{ margin: 20px 0; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 10px; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 6px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; }}
    .muted {{ color: #64748b; }}
  </style>
  <style>
.grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
}}

.card {{
    flex: 1 1 calc(50% - 10px);
    box-sizing: border-box;
}}

.span-2 {{
    flex: 1 1 100%;
}}
  </style>

</head>
<body>
  <h1>Networth Snapshot Report</h1>
  <p class=\"muted\">Generated from the latest export data.</p>
  {summary_cards}
  <div class=\"chart-section\">
    <h2>Networth Trend</h2>
    {build_svg_line_chart(networth_values, dates)}
  </div>
  <div class=\"chart-section\">
    <h2>Latest Asset vs Liability Totals</h2>
    {build_svg_bar_chart(asset_vs_liability_chart)}
  </div>
  <div class=\"chart-section\">
    <h2>CSV Snapshot Table</h2>
    <table>
      <colgroup>
        <col style="width: 5%;" />
        <col style="width: 5%;" />
        <col style="width: 5%;" />
        <col style="width: 20%;" />
        <col style="width: 20%;" />
        <col style="width: 45%;" />
      </colgroup>
      <thead><tr><th>Date</th><th>Time</th><th>Networth</th><th>Assets</th><th>Liabilities</th><th>Comments</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</body>
</html>
"""


def _playwright_chart_paths(temp_dir):
    return {
        "trend": Path(temp_dir) / "networth_totals.png",
        "composition": Path(temp_dir) / "networth_composition.png",
        "assets": Path(temp_dir) / "asset_breakdown.png",
        "liabilities": Path(temp_dir) / "liability_breakdown.png",
    }


def _seed_history_into_page(page, records):
    page.evaluate(
        """
        async (recordPayload) => {
          const request = indexedDB.open('networthDB', 2);
          await new Promise((resolve, reject) => {
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
          });

          const db = request.result;
          const tx = db.transaction('history', 'readwrite');
          const store = tx.objectStore('history');

          await new Promise((resolve, reject) => {
            const clearReq = store.clear();
            clearReq.onsuccess = () => resolve();
            clearReq.onerror = () => reject(clearReq.error);
          });

          for (const row of recordPayload) {
            store.add({
              date: row.date,
              time: row.time,
              networth: row.networth,
              assets: row.assets,
              liabilities: row.liabilities,
              comments: row.comments,
            });
          }

          await new Promise((resolve, reject) => {
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
          });

          if (window.loadHistory) {
            window.loadHistory();
          }
        }
        """,
        records,
    )


def generate_pdf_report(records, pdf_path):
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if sync_playwright is None:
        raise RuntimeError(
            "Playwright is required to generate PDF reports. Install it with: pip install playwright"
        )

    html_path = Path(__file__).resolve().parent / "networth_calculator.html"
    if not html_path.exists():
        raise FileNotFoundError(f"Could not find networth calculator page at {html_path}")

    browser_records = []
    for record in records:
        browser_records.append(
            {
                "date": record.get("date", ""),
                "time": record.get("time", ""),
                "networth": record.get("networth", ""),
                "assets": record.get("assets", ""),
                "liabilities": record.get("liabilities", ""),
                "comments": record.get("comments", ""),
            }
        )

    with tempfile.TemporaryDirectory(dir=str(pdf_path.parent)) as temp_dir:
        chart_paths = _playwright_chart_paths(temp_dir)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1800})
            page = context.new_page()
            page.goto(html_path.resolve().as_uri())
            page.wait_for_load_state("networkidle")
            page.wait_for_function("window.document.readyState === 'complete'")
            _seed_history_into_page(page, browser_records)
            page.wait_for_function(
                "document.querySelector('#networthTotalsChart') && document.querySelector('#networthChart') && document.querySelector('#assetPieChart') && document.querySelector('#liabilityPieChart')"
            )
            page.wait_for_timeout(10000)

            sections = [
                ("Networth Totals", "#networthTotalsChart", chart_paths["trend"]),
                ("Networth Breakdown Chart", "#networthChart", chart_paths["composition"]),
                ("Networth Pie Chart", ".pie-chart-wrapper", chart_paths["assets"]),
            ]

            for title, selector, output_path in sections:
                page.locator(f"text={title}").first.click()
                page.wait_for_timeout(1200)
                page.locator(selector).screenshot(path=str(output_path))

            # Use the same captured chart image for all PDF panels in the current report layout.
            chart_paths["liabilities"] = chart_paths["assets"]

            ordered_browser_records = []
            for record in browser_records:
                date_text = str(record.get("date", "")).strip()
                time_text = str(record.get("time", "")).strip()
                parsed_dt = None

                for candidate_format in ("%m-%d-%y %I:%M:%S %p", "%m-%d-%y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %I:%M:%S %p"):
                    try:
                        parsed_dt = datetime.strptime(f"{date_text} {time_text}", candidate_format)
                        break
                    except ValueError:
                        continue

                if parsed_dt is None:
                    parsed_dt = datetime.min

                ordered_browser_records.append({**record, "_dt": parsed_dt})

            ordered_browser_records = sorted(ordered_browser_records, key=lambda record: record["_dt"], reverse=True)

            rows_html = "".join(
                f"<tr><td>{escape(str(r.get('date','')))}</td><td>{escape(str(r.get('time','')))}</td><td>{escape(str(r.get('networth','')))}</td><td>{escape(str(r.get('assets','')))}</td><td>{escape(str(r.get('liabilities','')))}</td><td>{escape(str(r.get('comments','')))}</td></tr>"
                for r in ordered_browser_records
            )

            html_report = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Networth Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111827; }}
    h1 {{ margin-bottom: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin: 20px 0; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; background: #f9fafb; }}
    img {{ width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px; background: white; margin-bottom: 12px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 10px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 6px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>Networth Snapshot Report</h1>
  <p>Generated from the charts rendered by the networth calculator app.</p>
  {build_networth_summary_html(browser_records)}
<div class="grid">
    <div class="card">
        <h3>Networth Trend</h3>
        <img src="{chart_paths['trend'].as_uri()}" />
    </div>

    <div class="card">
        <h3>Networth Composition</h3>
        <img src="{chart_paths['composition'].as_uri()}" />
    </div>

    <div class="card span-2">
        <h3>Asset and Liability Breakdown</h3>
        <img src="{chart_paths['assets'].as_uri()}" />
    </div>
</div>
  <h2>CSV Snapshot Table</h2>
  <table>
      <colgroup>
        <col style="width: 10%;" />
        <col style="width: 10%;" />
        <col style="width: 10%;" />
        <col style="width: 15%;" />
        <col style="width: 15%;" />
        <col style="width: 40%;" />
      </colgroup>
    <thead><tr><th>Date</th><th>Time</th><th>Networth</th><th>Assets</th><th>Liabilities</th><th>Comments</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</body>
</html>
"""

            page.set_content(html_report)
            page.pdf(path=str(pdf_path), landscape=True, format="A4", print_background=True, margin={"top": "8mm", "right": "8mm", "bottom": "8mm", "left": "8mm"})
            browser.close()
    return pdf_path
