from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from weasyprint import HTML


# =========================================================
# Data Model
# =========================================================

@dataclass
class Blog:
    blog_name: str
    blog_content: str
    created_dt: int

    @property
    def formatted_date(self) -> str:
        """
        Converts epoch milliseconds to readable datetime.
        """
        try:
            return datetime.fromtimestamp(
                self.created_dt / 1000
            ).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(self.created_dt)

    @property
    def short_date(self) -> str:
        """
        Returns YYYY-MM-DD
        """
        try:
            return datetime.fromtimestamp(
                self.created_dt / 1000
            ).strftime("%Y-%m-%d")
        except Exception:
            return str(self.created_dt)


# =========================================================
# Mongo-safe date parsing
# =========================================================

def parse_created_dt(value: Any) -> int:
    """
    Handles:
    - int
    - float
    - string
    - Mongo Extended JSON
    """

    if value is None:
        return 0

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


# =========================================================
# Load Blogs
# =========================================================

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

    # newest first
    return sorted(
        blogs,
        key=lambda b: b.created_dt,
        reverse=True,
    )


# =========================================================
# HTML Template
# =========================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>

    @page {{
        size: Letter;
        margin: 20mm;

        @bottom-center {{
            content: "Page " counter(page) " of " counter(pages);
            font-size: 10px;
            color: #666;
        }}
    }}

    body {{
        font-family: Arial, sans-serif;
        line-height: 1.6;
        margin: 0;
        padding: 0;
    }}

    .cover-page {{
        height: 90vh;

        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;

        page-break-after: always;
    }}

    .cover-content h1 {{
        font-size: 36px;
        margin-bottom: 20px;
    }}

    .cover-content h2 {{
        font-size: 24px;
        color: #666;
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
        font-size: 24px;
        font-weight: bold;
        margin-top: 8px;
    }}

    .content {{
        font-size: 14px;
    }}

    .content img {{
        max-width: 100%;
        height: auto;
        margin-top: 12px;
        margin-bottom: 12px;
    }}

    .content a {{
        color: #1a0dab;
        text-decoration: underline;
    }}

    .content p {{
        margin: 10px 0;
    }}

</style>
</head>

<body>

{content}

</body>
</html>
"""


# =========================================================
# Cover Page
# =========================================================

def render_cover_page(
    author_name: str,
    start_date: str,
    end_date: str,
) -> str:

    return f"""
    <div class="cover-page">
        <div class="cover-content">
            <h1>Blogs from {start_date} to {end_date}</h1>
            <h2>By {author_name}</h2>
        </div>
    </div>
    """


# =========================================================
# Blog Renderer
# =========================================================

def render_blog(blog: Blog) -> str:
    return f"""
    <div class="blog">

        <div class="header">
            <div class="date">
                {blog.formatted_date}
            </div>

            <div class="title">
                {blog.blog_name}
            </div>
        </div>

        <div class="content">
            {blog.blog_content}
        </div>

    </div>
    """


# =========================================================
# PDF Generation
# =========================================================

def create_pdf(
    input_json: str,
    output_pdf: str,
    author_name: str,
) -> None:

    blogs = load_blogs(input_json)

    if not blogs:
        raise ValueError("No blogs found in JSON")

    newest_blog = blogs[0]
    oldest_blog = blogs[-1]

    start_date = oldest_blog.short_date
    end_date = newest_blog.short_date

    # Cover page
    cover_html = render_cover_page(
        author_name=author_name,
        start_date=start_date,
        end_date=end_date,
    )

    # Blog pages
    blogs_html = "\n".join(
        render_blog(blog)
        for blog in blogs
    )

    # Final HTML
    full_html = HTML_TEMPLATE.format(
        content=cover_html + blogs_html
    )

    # Generate PDF
    HTML(string=full_html).write_pdf(output_pdf)

    print(f"PDF created: {output_pdf}")


# =========================================================
# Entry Point
# =========================================================

if __name__ == "__main__":

    create_pdf(
        input_json="work/blogs.json",
        output_pdf="work/blogs_output.pdf",
        author_name="Avinash"
    )