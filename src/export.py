"""Utility functions for data exportation."""
import csv
import json
from tkinter import filedialog
from tkinter import messagebox

import openpyxl
from openpyxl.styles import Font


def export_csv(headings: tuple[str], data: list[tuple], title: str) -> None:
    """Exports data to CSV format."""
    file = filedialog.asksaveasfilename(
        title=title, defaultextension=".csv", filetypes=(("CSV", ".csv"),))
    if not file:
        return
    try:
        with open(file, "w", encoding="utf8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(headings)
            writer.writerows(data)
    except Exception as e:
        messagebox.showerror(
            "CSV Export Error",
                f"An error occurred while exporting the CSV: {e}")


def export_xlsx(
    headings: tuple[str], data: list[tuple], title: str, sheet_name: str
) -> None:
    """Exports data to XLSX format."""
    file = filedialog.asksaveasfilename(
        title=title, defaultextension=".xlsx", filetypes=(("XLSX", ".xlsx"),))
    if not file:
        return
    try:
        workbook = openpyxl.Workbook()
        workbook.active.title = sheet_name
        for i, heading in enumerate(headings, 1):
            cell = workbook.active.cell(row=1, column=i)
            cell.value = heading
            cell.font = Font(bold=True)
        for record in data:
            workbook.active.append(record)
        workbook.save(file)
    except Exception as e:
        messagebox.showerror(
            "XLSX Export Error",
                f"An error occurred while exporting the XLSX: {e}")


def export_json(data: list[dict], title: str) -> None:
    """Exports data to CSV format."""
    file = filedialog.asksaveasfilename(
        title=title, defaultextension=".json", filetypes=(("JSON", ".json"),))
    if not file:
        return
    try:
        with open(file, "w", encoding="utf8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        messagebox.showerror(
            "JSON Export Error",
                f"An error occurred while exporting the JSON: {e}")