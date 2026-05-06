# Python Utils: Blog JSON to PDF

This project contains a Python utility that converts blog data from a JSON file into a PDF document.

## What this code does

- Reads blog entries from `work/blogs.json`
- Parses `created_dt` values (including Mongo-style objects like `{"$numberLong": "..."}`)
- Sorts blogs by newest date first
- Renders each blog entry into HTML
- Generates a final PDF file (`work/blogs_output.pdf`) using WeasyPrint

Main script: `blogs2pdf.py`

## Prerequisites

- Python 3.9+ (recommended)
- `pip`
- Python package:
  - `weasyprint`

### System libraries for WeasyPrint

WeasyPrint may require native libraries depending on your OS (for example Cairo/Pango/GDK-PixBuf related packages on Linux).  
If install/runtime errors mention missing shared libraries, install the required OS packages for WeasyPrint for your platform.

Install required system libraries on Ubuntu/Debian:

```bash
sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libcairo2
```

### Required JSON schema (`work/blogs.json`)

Create `work/blogs.json` with a JSON array of blog objects. Each object should include:

- `blog_name` (string): title of the blog post
- `blog_content` (string): HTML content for the blog post body
- `created_dt` (required): creation timestamp in epoch milliseconds

Supported `created_dt` formats:

- Number: `1617228689559`
- Numeric string: `"1617228689559"`
- Mongo-style object: `{"$numberLong": "1617228689559"}`
- Mongo-style object: `{"$date": "1617228689559"}`

Example:

```json
[
  {
    "blog_name": "My First Blog",
    "blog_content": "<p>Hello world</p>",
    "created_dt": { "$numberLong": "1617228689559" }
  }
]
```

## Install dependencies

From the `blogtopdf` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install weasyprint
```

## How to run

```bash
python3 blogs2pdf.py
```

Expected output:

- Console message: `PDF created: work/blogs_output.pdf`
- Generated file: `work/blogs_output.pdf`

## Notes

- To use a different input/output file, edit the last line in `blogs2pdf.py`:
  - `create_pdf("work/blogs.json", "work/blogs_output.pdf")`
