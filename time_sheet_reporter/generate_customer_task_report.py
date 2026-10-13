#!/usr/bin/env python3
"""
Create a PDF report from a CSV of dated customer tasks.

Expected CSV columns:
  - Task: "Customer: task description"
  - Time Taken (min): duration in minutes
  - Date: task date

Usage:
  python generate_customer_task_report.py input.csv [output.pdf]

The summary table contains one column per date, each customer's daily hours,
a date-range total, and a total row for each date. Detailed sections then list
each date, customer, hours spent, and the tasks performed.
"""
import argparse
from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

def parse_data(csv_path):
    df = pd.read_csv(csv_path)
    required = {"Task", "Time Taken (min)", "Date"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required column(s): {', '.join(sorted(missing))}")

    df = df.dropna(subset=["Task", "Date"]).copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Time Taken (min)"] = pd.to_numeric(df["Time Taken (min)"], errors="coerce")
    df = df.dropna(subset=["Date", "Time Taken (min)"])
    df["Date"] = df["Date"].dt.date

    def split_task(value):
        # Split only on the first colon so additional colons remain in task text.
        value = str(value).strip()
        if ":" in value:
            customer, task = value.split(":", 1)
            customer, task = customer.strip(), task.strip()
        else:
            customer, task = "Unspecified customer", value
        return customer or "Unspecified customer", task

    parsed = df["Task"].apply(split_task)
    df["Customer"] = parsed.apply(lambda item: item[0])
    df["Task description"] = parsed.apply(lambda item: item[1])
    return df

def hours(minutes):
    return float(minutes) / 60.0

def build_pdf(df, output_pdf):
    dates = sorted(df["Date"].unique())
    customers = sorted(df["Customer"].unique(), key=str.casefold)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="SmallCell", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=7, leading=8.5, spaceAfter=0
    ))
    styles.add(ParagraphStyle(
        name="SmallCellCenter", parent=styles["SmallCell"], alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name="SummaryHeader", parent=styles["SmallCellCenter"],
        fontName="Helvetica-Bold", textColor=colors.white
    ))
    styles.add(ParagraphStyle(
        name="SectionDate", parent=styles["Heading2"], spaceBefore=8, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="TaskText", parent=styles["BodyText"], fontSize=8.5, leading=11,
        leftIndent=12, spaceAfter=3
    ))

    doc = SimpleDocTemplate(
        str(output_pdf), pagesize=landscape(A4),
        rightMargin=0.35*inch, leftMargin=0.35*inch,
        topMargin=0.4*inch, bottomMargin=0.4*inch
    )
    story = []
    story.append(Paragraph("Customer Time and Task Report", styles["Title"]))
    if dates:
        story.append(Paragraph(
            f"Date range: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}",
            styles["Normal"]
        ))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Summary (hours)", styles["Heading2"]))

    date_labels = [d.strftime("%Y-%m-%d") for d in dates]
    headers = ["Customer"] + date_labels + ["Date-range total"]
    table_data = [[Paragraph(str(h), styles["SummaryHeader"]) for h in headers]]

    daily_totals = {d: 0.0 for d in dates}
    customer_totals = {}
    for customer in customers:
        row = [Paragraph(customer.replace("&", "&amp;"), styles["SmallCell"])]
        total_minutes = 0.0
        for date in dates:
            minutes = df.loc[
                (df["Customer"] == customer) & (df["Date"] == date),
                "Time Taken (min)"
            ].sum()
            total_minutes += minutes
            daily_totals[date] += minutes
            row.append(Paragraph(f"{hours(minutes):.2f}" if minutes else "—",
                                 styles["SmallCellCenter"]))
        customer_totals[customer] = total_minutes
        row.append(Paragraph(f"{hours(total_minutes):.2f}", styles["SmallCellCenter"]))
        table_data.append(row)

    total_row = [Paragraph("<b>Total per day</b>", styles["SmallCell"])]
    for date in dates:
        total_row.append(Paragraph(f"<b>{hours(daily_totals[date]):.2f}</b>",
                                  styles["SmallCellCenter"]))
    total_row.append(Paragraph(f"<b>{hours(sum(daily_totals.values())):.2f}</b>",
                              styles["SmallCellCenter"]))
    table_data.append(total_row)

    available_width = landscape(A4)[0] - 0.7*inch
    customer_width = min(2.1*inch, available_width * 0.25)
    other_width = (available_width - customer_width) / (len(headers) - 1)
    col_widths = [customer_width] + [other_width] * (len(headers) - 1)
    summary_table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#244062")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -2), colors.HexColor("#F4F6F8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F4F6F8")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DCE6F1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9AA7B2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_table)
    story.append(PageBreak())
    story.append(Paragraph("Daily Task Details", styles["Title"]))
    story.append(Spacer(1, 6))

    for date_index, date in enumerate(dates):
        story.append(Paragraph(date.strftime("%A, %Y-%m-%d"), styles["SectionDate"]))
        day_df = df[df["Date"] == date]
        if day_df.empty:
            story.append(Paragraph("No tasks recorded.", styles["Normal"]))
            continue
        # Keep source order within each day.
        for customer in customers:
            customer_rows = day_df[day_df["Customer"] == customer]
            if customer_rows.empty:
                continue
            total_hours = hours(customer_rows["Time Taken (min)"].sum())
            block = [
                Paragraph(
                    f"<b>{customer.replace('&', '&amp;')} — {total_hours:.2f} hrs</b>",
                    styles["Normal"]
                )
            ]
            for task in customer_rows["Task description"]:
                safe_task = (str(task).replace("&", "&amp;")
                             .replace("<", "&lt;").replace(">", "&gt;"))
                block.append(Paragraph(f"• {safe_task}", styles["TaskText"]))
            block.append(Spacer(1, 5))
            story.extend(block)
        if date_index < len(dates) - 1:
            story.append(Spacer(1, 8))

    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(landscape(A4)[0] - 0.35*inch, 0.2*inch,
                               f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)

def main():
    parser = argparse.ArgumentParser(description="Create a customer task time PDF report.")
    parser.add_argument("input_csv", help="Path to the input CSV file")
    parser.add_argument("output_pdf", nargs="?", default="customer_task_report.pdf",
                        help="Output PDF path (default: customer_task_report.pdf)")
    args = parser.parse_args()
    df = parse_data(args.input_csv)
    build_pdf(df, args.output_pdf)
    print(f"Created PDF report: {args.output_pdf}")

if __name__ == "__main__":
    main()
