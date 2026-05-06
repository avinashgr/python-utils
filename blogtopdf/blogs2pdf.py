from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from weasyprint import HTML, CSS


# -----------------------------
# Data Model
# -----------------------------

@dataclass
class Blog:
    blog_name: str
    blog_content: str
    created_dt: int

    @property
    def formatted_date(self) -> str:
        return datetime.fromtimestamp(self.created_dt / 1000).strftime(
            "%Y-%m-%d %H:%M:%S"
        )


# -----------------------------
# Parsing Mongo-safe dates
# -----------------------------

def parse_created_dt(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0

    if isinstance(value, dict):
        if "$numberLong" in value:
            return int(value["$numberLong"])
        if "$date" in value:
            return int(value["$date"])

    return 0


# -----------------------------
# Load + sort
# -----------------------------

def load_blogs(path: str) -> List[Blog]:
    with open(path, "r", encoding="utf-8") as f:
        raw: List[Dict[str, Any]] = json.load(f)

    blogs = [
        Blog(
            blog_name=item.get("blog_name", "Untitled"),
            blog_content=item.get("blog_content", ""),
            created_dt=parse_created_dt(item.get("created_dt")),
        )
        for item in raw
    ]

    return sorted(blogs, key=lambda b: b.created_dt, reverse=True)


# -----------------------------
# HTML Template
# -----------------------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: Arial, sans-serif;
        margin: 40px;
        line-height: 1.5;
    }}

    .blog {{
        page-break-after: always;
    }}

    .header {{
        border-bottom: 1px solid #ddd;
        margin-bottom: 20px;
        padding-bottom: 10px;
    }}

    .date {{
        color: #666;
        font-size: 12px;
    }}

    .title {{
        font-size: 22px;
        font-weight: bold;
        margin-top: 5px;
    }}

    img {{
        max-width: 100%;
        height: auto;
        margin-top: 10px;
    }}

    a {{
        color: #1a0dab;
        text-decoration: underline;
    }}

    p {{
        margin: 10px 0;
    }}
</style>
</head>
<body>

{content}

</body>
</html>
"""


def render_blog(blog: Blog) -> str:
    return f"""
    <div class="blog">
        <div class="header">
            <div class="date">{blog.formatted_date}</div>
            <div class="title">{blog.blog_name}</div>
        </div>
        <div class="content">
            {blog.blog_content}
        </div>
    </div>
    """


# -----------------------------
# PDF Generation
# -----------------------------

def create_pdf(input_json: str, output_pdf: str) -> None:
    blogs = load_blogs(input_json)

    html_content = "\n".join(render_blog(b) for b in blogs)
    full_html = HTML_TEMPLATE.format(content=html_content)

    HTML(string=full_html).write_pdf(
        output_pdf,
        stylesheets=[CSS(string="@page { size: Letter; margin: 20mm }")]
    )

    print(f"PDF created: {output_pdf}")


# -----------------------------
# Entry point
# -----------------------------

if __name__ == "__main__":
    create_pdf("work/blogs.json", "work/blogs_output.pdf")
