"""Analysis of the Cambridge CS application stats, including a basic GUI."""
import ctypes
import enum
import statistics
import tkinter as tk
from collections import Counter
from tkinter import ttk
from tkinter.font import Font
from typing import Callable

import export
from data import *


# The years that each metric has data for.
A_LEVEL_YEARS = (2022, 2023, 2024)
GCSE_YEARS = (2022, 2023)
TMUA_YEARS = (2022, 2023, 2024)

A_LEVEL_TABLE_HEADINGS = ("Grade Combination", "Frequency", "Percentage (%)")
A_LEVEL_RAW_TABLE_HEADINGS = (
    "Year", "Apply ID", "Original College Offer", "Other College Offer",
    "Winter Pool", "Grades" 
)

GCSE_TABLE_HEADINGS = ("Number of 9s", "Frequency", "Percentage (%)")
GCSE_RAW_TABLE_HEADINGS = (
    "Year", "Apply ID", "Original College Offer", "Other College Offer",
    "Winter Pool", "Nines" 
)

TMUA_TABLE_HEADINGS = ("Score", "Frequency", "Percentage (%)")
TMUA_RAW_TABLE_HEADINGS = (
    "Year", "Apply ID", "Original College Offer", "Other College Offer",
    "Winter Pool", "Paper 1", "Paper 2", "Overall"
)

MAX_SHEET_NAME_LENGTH = 31


class Outcome(enum.Enum):
    """
    Possible outcomes for a given application,
    with all applications satisfying 'any' plus at least one other.
    """
    original_college_offer = "Original College Offer"
    other_college_offer = "Other College Offer"
    winter_pool = "Winter Pool"
    nothing = "Nothing" # No offer, not pooled.
    any = "Any"


def matches_outcome(record: Record, outcome: Outcome) -> bool:
    """Determines if a record matches a given outcome."""
    return {
        Outcome.original_college_offer: record.original_college,
        Outcome.other_college_offer: record.other_college,
        Outcome.winter_pool: record.winter_pool,
        Outcome.nothing: (
            not record.original_college and not record.other_college
            and not record.winter_pool),
        Outcome.any: True
    }[outcome]


class Table(ttk.Treeview):
    """Convenient treeview wrapper with properly sized headings to fit data."""

    def __init__(
        self, master: tk.Frame, headings: tuple[str], records: list[tuple]
    ) -> None:
        super().__init__(
            master, columns=list(range(len(headings))),
            selectmode="browse", show="headings")
        font_obj = Font()
        for i, heading in enumerate(headings):
            self.heading(i, text=heading, anchor=tk.CENTER)
            width = 0
            for string in [headings[i]] + [record[i] for record in records]:
                width = max(width, font_obj.measure(string))
            self.column(i, width=width, anchor=tk.CENTER)

        for record in records:
            self.insert("", tk.END, values=record)


class CsStatsAnalysis(tk.Tk):
    """GUI for Cambridge CS stats analysis."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Cambridge CS Stats Analysis")
        self.notebook = ttk.Notebook(self)
        self.a_level = ALevelAnalysis(self.notebook)
        self.gcse = GCSEAnalysis(self.notebook)
        self.tmua = TMUAAnalysis(self.notebook)
        self.notebook.add(self.a_level, text="A-Level")
        self.notebook.add(self.gcse, text="GCSE")
        self.notebook.add(self.tmua, text="TMUA")
        self.notebook.pack()


class YearSetting(tk.Frame):
    """Allows a year to be selected, or all years (for data filtering)."""

    def __init__(
        self, master: tk.Frame, callback: Callable, years: list[int]
    ) -> None:
        super().__init__(master)
        self._year = tk.IntVar(value=-1)
        self.all_years = years
        self.label = tk.Label(self, text="Year")
        self.label.grid(row=0, column=0, columnspan=len(self.all_years) + 1)
        for i, year in enumerate(self.all_years):
            tk.Radiobutton(
                self, text=year, variable=self._year, value=year,
                command=callback).grid(row=1, column=i, padx=5, pady=5)
        tk.Radiobutton(
            self, text="All", variable=self._year, value=-1,
            command=callback
        ).grid(row=1, column=len(self.all_years), padx=5, pady=5)
    
    @property
    def years(self) -> tuple[int]:
        if self._year.get() != -1:
            return (self._year.get(),)
        return self.all_years


class OutcomeSetting(tk.Frame):
    """Allows a particular outcome to be selected (for data filtering)."""

    def __init__(self, master: tk.Frame, callback: Callable) -> None:
        super().__init__(master)
        self._outcome = tk.StringVar(
            value=Outcome.original_college_offer.value)
        self.label = tk.Label(self, text="Outcome")
        self.label.grid(row=0, column=0, columnspan=5)
        for i, outcome in enumerate((
            Outcome.original_college_offer, Outcome.other_college_offer,
            Outcome.winter_pool, Outcome.nothing, Outcome.any
        )):
            tk.Radiobutton(
                self, text=outcome.value, variable=self._outcome,
                value=outcome.value, command=callback
            ).grid(row=1, column=i, padx=5, pady=5)
    
    @property
    def outcome(self) -> Outcome:
        return Outcome(self._outcome.get())


class ExportFrame(tk.Frame):
    """Export options and functionality for data within the program."""

    def __init__(
        self, master: tk.Frame, raw_headings: tuple[str],
        summary_headings: tuple[str], metric: str
    ) -> None:
        super().__init__(master)
        self.raw_headings = raw_headings
        self.summary_headings = summary_headings
        self.metric = metric

        self.label = tk.Label(self, text="Export")
        self.label.grid(row=0, column=0, columnspan=6)
        for i, (text, command) in enumerate((
            ("Raw CSV", self.export_raw_csv),
            ("Raw XLSX", self.export_raw_xlsx),
            ("Raw JSON", self.export_raw_json),
            ("Summary CSV", self.export_summary_csv),
            ("Summary XLSX", self.export_summary_xlsx),
            ("Summary JSON", self.export_summary_json)
        )):
            button = ttk.Button(self, text=text, command=command)
            button.grid(row=1 + i // 3, column=i % 3, padx=5, pady=5)

    @property
    def raw_export_records(self) -> list[tuple]:
        return [
            record.export_record for record in self.master.filtered_records]
    
    @property
    def raw_json_data(self) -> list[dict]:
        return [record.json_object for record in self.master.filtered_records]

    def export_raw_csv(self) -> None:
        """Exports the raw data to CSV format."""
        export.export_csv(
            self.raw_headings, self.raw_export_records,
            f"Export Raw {self.metric} CSV")
    
    def export_raw_xlsx(self) -> None:
        """Exports the raw data to XLSX format."""
        export.export_xlsx(
            self.raw_headings, self.raw_export_records,
            f"Export Raw {self.metric} XLSX",
            f"Raw {self.metric}"[:MAX_SHEET_NAME_LENGTH])

    def export_raw_json(self) -> None:
        """Exports the raw data to JSON format."""
        export.export_json(
            self.raw_json_data, f"Export Raw {self.metric} JSON")
    
    def export_summary_csv(self) -> None:
        """Exports the summary table to CSV format."""
        export.export_csv(
            self.summary_headings, self.master.summary_table_records[:-1],
            f"Export Summary {self.metric} CSV")
    
    def export_summary_xlsx(self) -> None:
        """Exports the summary data to XLSX format."""
        export.export_xlsx(
            self.summary_headings, self.master.summary_table_records[:-1],
            f"Export Summary {self.metric} XLSX",
            f"Summary {self.metric}"[:MAX_SHEET_NAME_LENGTH])

    def export_summary_json(self) -> None:
        """Exports the summary data to JSON format.""" 
        export.export_json(
            self.master.summary_table_json_data, 
            f"Export Summary {self.metric} JSON")


class ALevelAnalysis(tk.Frame):
    """Analysis of outcomes by A-Level predicted grades."""

    def __init__(self, master: CsStatsAnalysis) -> None:
        super().__init__(master)
        self.data = ALevel.get_data()
        self.filtered_records = []
        self.summary_table_records = []
        self.year_setting = YearSetting(
            self, self.update_table, A_LEVEL_YEARS)
        self.outcome_setting = OutcomeSetting(self, self.update_table)
        self.table = Table(self, A_LEVEL_TABLE_HEADINGS, [])
        self.export_frame = ExportFrame(
            self, A_LEVEL_RAW_TABLE_HEADINGS, A_LEVEL_TABLE_HEADINGS,
            "Predicted A-Level Grades")

        self.year_setting.grid(row=0, padx=10, pady=10)
        self.outcome_setting.grid(row=1, padx=10, pady=10)
        self.export_frame.grid(row=3, padx=10, pady=10)
        self.update_table()
    
    def update_table(self) -> None:
        """Updates the A-Level predicted grades frequency table."""
        self.table.destroy()
        years = self.year_setting.years
        outcome = self.outcome_setting.outcome
        self.filtered_records = [
            record for record in self.data
            if record.year in years and matches_outcome(record, outcome)]
        counter = Counter(
            " ".join(record.grades) for record in self.filtered_records)
        self.summary_table_records = []
        for grade_combination, count in counter.most_common():
            percentage = float(
                f"{count / len(self.filtered_records) * 100:.1f}")
            record = (grade_combination, count, percentage)
            self.summary_table_records.append(record)
        self.summary_table_records.append(
            ("All", len(self.filtered_records), 100.0))
        self.table = Table(
            self, A_LEVEL_TABLE_HEADINGS, self.summary_table_records)
        self.table.grid(row=2, padx=10, pady=10)
    
    @property
    def summary_table_json_data(self) -> list[dict]:
        return [{
            "grade_combination": grades.split(),
            "count": count,
            "percentage": count / len(self.filtered_records) * 100
        } for grades, count, _ in self.summary_table_records[:-1]]


class GCSEAnalysis(tk.Frame):
    """Analysis of outcomes by 9s at GCSE."""

    def __init__(self, master: CsStatsAnalysis) -> None:
        super().__init__(master)
        self.data = GCSE.get_data()
        self.filtered_records = []
        self.summary_table_records = []
        self.year_setting = YearSetting(
            self, self.update_output, GCSE_YEARS)
        self.outcome_setting = OutcomeSetting(self, self.update_output)
        self.stats = tk.Label(self, justify=tk.LEFT)
        self.table = Table(self, GCSE_TABLE_HEADINGS, [])
        self.export_frame = ExportFrame(
            self, GCSE_RAW_TABLE_HEADINGS, GCSE_TABLE_HEADINGS,
            "Achieved GCSE 9s")
        self.year_setting.grid(row=0, padx=10, pady=10)
        self.outcome_setting.grid(row=1, padx=10, pady=10)
        self.stats.grid(row=2, padx=10, pady=10)
        self.export_frame.grid(row=4, padx=10, pady=10)
        self.update_output()
    
    def update_output(self) -> None:
        """Updates the 9s at GCSE summary stats and frequency table."""
        years = self.year_setting.years
        outcome = self.outcome_setting.outcome
        self.filtered_records = [
            record for record in self.data
            if record.year in years and matches_outcome(record, outcome)]
        nines = [record.nines for record in self.filtered_records]
        lower_quartile, median, upper_quartile = statistics.quantiles(nines)
        stats_text = "\n".join((
            f"Mean 9s: {statistics.mean(nines):.2f}",
            f"Median 9s: {median:.2f}",
            f"Lower Quartile 9s: {lower_quartile:.2f}",
            f"Upper Quartile 9s: {upper_quartile:.2f}",
            f"Minimum 9s: {min(nines):.2f}",
            f"Maximum 9s: {max(nines):.2f}"
        ))
        counter = Counter(nines)
        self.summary_table_records = []
        for nines_, count in counter.most_common():
            percentage = float(f"{count / len(nines) * 100:.1f}")
            record = (nines_, count, percentage)
            self.summary_table_records.append(record)
        self.summary_table_records.append(
            ("All", len(nines), 100.0))
        self.table.destroy()
        self.table = Table(
            self, GCSE_TABLE_HEADINGS, self.summary_table_records)
        self.stats.config(text=stats_text)
        self.table.grid(row=3, padx=10, pady=10)

    @property
    def summary_table_json_data(self) -> list[dict]:
        return [{
            "nines": nines,
            "count": count,
            "percentage": count / len(self.filtered_records) * 100
        } for nines, count, _ in self.summary_table_records[:-1]]


class TMUAAnalysis(tk.Frame):
    """Analysis of outcomes by TMUA performance."""

    def __init__(self, master: CsStatsAnalysis) -> None:
        super().__init__(master)
        self.data = TMUA.get_data()
        self.filtered_records = []
        self.year_setting = YearSetting(
            self, self.update_output, TMUA_YEARS)
        self.outcome_setting = OutcomeSetting(self, self.update_output)
        self.notebook = ttk.Notebook(self)
        self.export_frame = ExportFrame(
            self, TMUA_RAW_TABLE_HEADINGS, TMUA_TABLE_HEADINGS, "TMUA Scores")
        self.export_note = tk.Label(
            self, text="Note: Summary exports are "
                "for the currently selected table above.")
        self.year_setting.grid(row=0, padx=10, pady=10)
        self.outcome_setting.grid(row=1, padx=10, pady=10)
        self.export_frame.grid(row=3, padx=10, pady=10)
        self.export_note.grid(row=4)
        self.update_output()

    def update_output(self) -> None:
        """
        Updates the TMUA summary stats and frequency tables
        for paper 1, paper 2, and the overall score.
        """
        years = self.year_setting.years
        outcome = self.outcome_setting.outcome
        self.filtered_records = [
            record for record in self.data
            if record.year in years and matches_outcome(record, outcome)]
        self.notebook.destroy()
        # Sub-notebook to display data for each score (P1, P2, overall).
        self.notebook = ttk.Notebook(self)
        for field, text in ((
            ("paper1", "Paper 1"), ("paper2", "Paper 2"),
            ("overall", "Overall")
        )):
            data = [getattr(record, field) for record in self.filtered_records]
            data_frame = TMUADataFrame(self.notebook, text, data)
            self.notebook.add(data_frame, text=text)
        self.notebook.grid(row=2, padx=10, pady=10)
    
    @property
    def summary_table_records(self) -> list[tuple]:
        index = self.notebook.index(self.notebook.select())
        frame = tuple(self.notebook.children.values())[index]
        return frame.table_records

    @property
    def summary_table_json_data(self) -> list[dict]:
        return [{
            "score": score,
            "count": count,
            "percentage": count / len(self.filtered_records) * 100
        } for score, count, _ in self.summary_table_records[:-1]]


class TMUADataFrame(tk.Frame):
    """
    Displays summary stats and score frequency table for a given TMUA metric.
    (paper 1 / paper 2 / overall).
    """

    def __init__(
        self, master: ttk.Notebook, metric: str, results: list[float]
    ) -> None:
        super().__init__(master)
        lower_quartile, median, upper_quartile = statistics.quantiles(results)
        stats_text = "\n".join((
            f"Mean {metric}: {statistics.mean(results):.2f}",
            f"Median {metric}: {median:.2f}",
            f"Lower Quartile {metric}: {lower_quartile:.2f}",
            f"Upper Quartile {metric}: {upper_quartile:.2f}",
            f"Minimum {metric}: {min(results):.2f}",
            f"Maximum {metric}: {max(results):.2f}"
        ))
        counter = Counter(results)
        self.table_records = []
        for score, count in counter.most_common():
            percentage = float(f"{count / len(results) * 100:.1f}")
            record = (score, count, percentage)
            self.table_records.append(record)
        self.table_records.append(("All", len(results), 100.0))
        self.stats_label = tk.Label(self, text=stats_text, justify=tk.LEFT)
        self.table = Table(self, TMUA_TABLE_HEADINGS, self.table_records)
        self.stats_label.pack(padx=10, pady=10)
        self.table.pack(padx=10, pady=10)


def main() -> None:
    """Main procedure of the program."""
    ctypes.windll.shcore.SetProcessDpiAwareness(True)
    CsStatsAnalysis().mainloop()


if __name__ == "__main__":
    # Use the data stored in the most recent database.
    most_recent_database()
    main()