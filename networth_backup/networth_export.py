#!/usr/bin/env python3
import argparse
import configparser
import csv
import io
import json
import logging
import re
from datetime import datetime
from pathlib import Path


CSV_COLUMNS = [
    ("Date", "date"),
    ("Time", "time"),
    ("Networth", "networth"),
    ("Assets", "assets"),
    ("Liabilities", "liabilities"),
    ("Comments", "comments"),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export networth records from MongoDB and convert them to CSV."
    )
    parser.add_argument(
        "--config",
        default="config.ini",
        help="Path to config.ini. Defaults to config.ini in the current directory.",
    )
    parser.add_argument(
        "--skip-mongo",
        action="store_true",
        help="Skip MongoDB export and only convert the configured JSON file to CSV.",
    )
    return parser.parse_args()


def load_config(config_path):
    config = configparser.ConfigParser()
    read_files = config.read(config_path)
    if not read_files:
        raise FileNotFoundError(f"Config file not found: {config_path}")

    for section in ("mongodb", "files"):
        if not config.has_section(section):
            raise ValueError(f"Missing config section: [{section}]")

    required_options = {
        "mongodb": ("uri", "database", "collection", "query"),
        "files": ("json_location", "csv_location"),
    }
    for section, options in required_options.items():
        for option in options:
            if not config.has_option(section, option):
                raise ValueError(f"Missing config option: [{section}] {option}")

    return config


def parse_query(query_text):
    query_text = query_text.strip()
    if not query_text:
        return {}

    try:
        from bson import json_util
    except ImportError as error:
        try:
            return json.loads(query_text)
        except json.JSONDecodeError as json_error:
            raise ImportError(
                "pymongo is required for Mongo Extended JSON or ObjectId query syntax. "
                "Install dependencies with: pip install -r resources.txt"
            ) from json_error

    try:
        return json_util.loads(query_text)
    except Exception:
        shell_query_text = convert_mongo_shell_query(query_text)
        try:
            return json_util.loads(shell_query_text)
        except Exception as error:
            raise ValueError(
                "Invalid MongoDB query in config.ini. Use JSON, Mongo Extended JSON, "
                "or simple Mongo shell ObjectId syntax like "
                "{userId: ObjectId('69992fc5b86afd5c80b009ae')}."
            ) from error


def convert_mongo_shell_query(query_text):
    query_text = re.sub(
        r"ObjectId\(['\"]([0-9a-fA-F]{24})['\"]\)",
        r'{"$oid":"\1"}',
        query_text,
    )
    query_text = re.sub(
        r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)",
        r'\1"\2"\3',
        query_text,
    )
    return query_text


def write_json(config):
    from bson import json_util
    from pymongo import MongoClient

    mongo_config = config["mongodb"]
    files_config = config["files"]
    query = parse_query(mongo_config["query"])
    json_path = Path(files_config["json_location"])
    json_path.parent.mkdir(parents=True, exist_ok=True)

    with MongoClient(mongo_config["uri"]) as client:
        collection = client[mongo_config["database"]][mongo_config["collection"]]
        documents = list(collection.find(query).sort([("date", 1), ("time", 1)]))

    json_path.write_text(json_util.dumps(documents, indent=2), encoding="utf-8")
    logging.info("Wrote %s MongoDB documents to %s", len(documents), json_path)


def load_json(json_path):
    text = json_path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        from bson import json_util

        return json_util.loads(text)


def add_timestamp_to_csv_path(csv_path):
    timestamp = datetime.now().strftime("%m%d%Y-%H%M")
    return csv_path.with_name(f"{csv_path.stem}-{timestamp}{csv_path.suffix}")


def write_csv(config):
    files_config = config["files"]
    json_path = Path(files_config["json_location"])
    csv_path = add_timestamp_to_csv_path(Path(files_config["csv_location"]))
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    records = load_json(json_path)
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow([column_name for column_name, _ in CSV_COLUMNS])
    for record in records:
        writer.writerow([record.get(field_name, "") for _, field_name in CSV_COLUMNS])

    csv_text = csv_buffer.getvalue()
    if csv_text.endswith("\r\n"):
        csv_text = csv_text[:-2]
    csv_path.write_text(csv_text, encoding="utf-8")

    logging.info("Wrote %s CSV rows to %s", len(records), csv_path)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    config = load_config(args.config)

    if not args.skip_mongo:
        write_json(config)
    write_csv(config)


if __name__ == "__main__":
    main()
