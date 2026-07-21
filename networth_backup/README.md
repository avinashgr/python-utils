# Python Utils: Networth MongoDB to CSV

This project contains a Python utility that exports networth data from MongoDB into a JSON file and converts that JSON into a CSV file.

## What this code does

- Reads MongoDB connection details from `config.ini`
- Runs the configured MongoDB query against the configured database and collection
- Writes the exported records to `work/networth.json`
- Converts the JSON records into a timestamped CSV file like `work/Networth-07202026-0830.csv`
- Preserves multiline `assets` and `liabilities` values as quoted CSV fields

Main script: `networth_export.py`

## Prerequisites

- Python 3.9+ recommended
- `pip`
- Python package:
  - `pymongo`

The `resources.txt` file also lists `weasyprint`, but this networth CSV export script only requires `pymongo`.

### Required JSON schema

The JSON file should contain an array of networth records. Each object should include:

- `date` string: snapshot date, for example `01-01-20`
- `time` string: snapshot time, for example `5:21:19 PM`
- `networth` number: net worth value
- `assets` string: multiline asset details
- `liabilities` string: multiline liability details
- `comments` string: notes for the snapshot

MongoDB `_id`, `userId`, and `__v` fields may exist in the JSON export, but they are not written to the CSV.

Example:

```json
[
  {
    "_id": { "$oid": "6a0e7463978c3bd20634d3da" },
    "userId": { "$oid": "6a0e71e71c5859b93df89fa9" },
    "date": "01-01-20",
    "time": "5:21:19 PM",
    "networth": -181619.1,
    "assets": "Stocks | Fidelity | 88091.01\nChecking | Bank Of America | 22253.34",
    "liabilities": "Personal Loan | Wells Fargo | 24976.52\nHome Loan | Quicken Loans | 239953.18",
    "comments": "Daily snapshot",
    "__v": 0
  }
]
```

## Install dependencies

From the `networth_backup` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r resources.txt
```

If you only want to install the dependency used by this script:

```bash
pip install pymongo
```

## Configure `config.ini`

Add `config.ini` before running the script:

- `[mongodb]`: set `uri`, `database`, `collection`, and `query` for your MongoDB source.
- `[files]`: set `json_location` for the exported JSON path and `csv_location` for the base CSV path.

Because `config.ini` can contain credentials and machine-specific paths, keep your local copy out of Git if it contains secrets.

The `config.ini` should look like this:

```ini
[mongodb]
uri=mongodb://localhost:27017
database=networth
collection=networth
query={}

[files]
json_location=work/networth.json
csv_location=work/Networth.csv
```

The script appends the current date and time to `csv_location`. For example, `work/Networth.csv` becomes `work/Networth-07202026-0830.csv`.

The `query` value should be valid JSON, Mongo Extended JSON, or simple Mongo shell `ObjectId(...)` syntax. For example:

```ini
query={"userId":{"$oid":"6a0e71e71c5859b93df89fa9"}}
```

This syntax is also supported:

```ini
query={userId: ObjectId('6a0e71e71c5859b93df89fa9')}
```

## How to run

Run the full MongoDB export and CSV conversion:

```bash
python3 networth_export.py
```

Expected output:

- Console message: `INFO: Wrote ... MongoDB documents to work/networth.json`
- Console message: `INFO: Wrote ... CSV rows to work/Networth-<MMDDYYYY>-<HHMM>.csv`
- Generated JSON file: `work/networth.json`
- Generated CSV file: `work/Networth-<MMDDYYYY>-<HHMM>.csv`

To convert an existing JSON file without querying MongoDB:

```bash
python3 networth_export.py --skip-mongo
```

To use a different config file:

```bash
python3 networth_export.py --config /path/to/config.ini
```

## To run as a cron

- Copy the project to a stable folder, for example `/home/avinash/scripts/networth_backup/`
- Create and activate a virtual environment
- Install dependencies
- Run the script with full paths from cron

Example setup:

```bash
cd /home/avinash/scripts/networth_backup/
python3 -m venv venv
source venv/bin/activate
pip install -r resources.txt
```

Example cron job that runs every day at 6:00 AM:

```cron
0 6 * * * cd /home/avinash/scripts/networth_backup && /home/avinash/scripts/networth_backup/venv/bin/python networth_export.py --config config.ini
```

## Notes

- The script sorts MongoDB results by `date` and then `time` in ascending order.
- The CSV columns are `Date`, `Time`, `Networth`, `Assets`, `Liabilities`, and `Comments`.
- The `work/` folder is used for generated files.
