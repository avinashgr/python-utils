from __future__ import annotations

from pathlib import Path
import json
import configparser
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List

from pymongo import MongoClient
from weasyprint import HTML

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.ini"


# =========================================================
# MongoDB Configuration
# =========================================================

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

# MongoDB Configuration
MONGO_URI = config["mongodb"]["uri"]
DATABASE_NAME = config["mongodb"]["database"]
COLLECTION_NAME = config["mongodb"]["collection"]

# File Paths
JSON_EXPORT_FILE = config["files"]["json_export"]
PDF_OUTPUT_FILE = config["files"]["pdf_output"]

# Author
AUTHOR_NAME = config["author"]["name"]


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
        try:
            return datetime.fromtimestamp(
                self.created_dt / 1000
            ).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(self.created_dt)

    @property
    def short_date(self) -> str:
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
# MongoDB Export
# =========================================================

def export_mongodb_collection_to_json(
    mongo_uri: str,
    database_name: str,
    collection_name: str,
    output_json_path: str,
) -> None:

    client = MongoClient(mongo_uri)

    db = client[database_name]
    collection = db[collection_name]

    documents = list(collection.find())

    # Convert ObjectId + unsupported BSON types
    serializable_docs = []

    for doc in documents:
        cleaned_doc = {}

        for key, value in doc.items():

            # Convert ObjectId
            if key == "_id":
                cleaned_doc[key] = str(value)
                continue

            cleaned_doc[key] = value

        serializable_docs.append(cleaned_doc)

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(
            serializable_docs,
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    print(
        f"Exported {len(serializable_docs)} documents "
        f"to {output_json_path}"
    )


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
        raise ValueError("No blogs found")

    newest_blog = blogs[0]
    oldest_blog = blogs[-1]

    start_date = oldest_blog.short_date
    end_date = newest_blog.short_date

    cover_html = render_cover_page(
        author_name=author_name,
        start_date=start_date,
        end_date=end_date,
    )

    blogs_html = "\n".join(
        render_blog(blog)
        for blog in blogs
    )

    full_html = HTML_TEMPLATE.format(
        content=cover_html + blogs_html
    )

    HTML(string=full_html).write_pdf(output_pdf)

    print(f"PDF created: {output_pdf}")


# =========================================================
# Full Pipeline
# =========================================================

def export_and_generate_pdf() -> None:

    # Step 1
    export_mongodb_collection_to_json(
        mongo_uri=MONGO_URI,
        database_name=DATABASE_NAME,
        collection_name=COLLECTION_NAME,
        output_json_path=JSON_EXPORT_FILE,
    )

    # Step 2
    create_pdf(
        input_json=JSON_EXPORT_FILE,
        output_pdf=PDF_OUTPUT_FILE,
        author_name=AUTHOR_NAME,
    )


# =========================================================
# Entry Point
# =========================================================

if __name__ == "__main__":

    export_and_generate_pdf()
