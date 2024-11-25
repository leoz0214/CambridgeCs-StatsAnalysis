import ctypes
import enum
import statistics
import tkinter as tk
from collections import Counter
from tkinter import ttk
from tkinter.font import Font
from typing import Callable

from extract import *


A_LEVEL_YEARS = (2022, 2023, 2024)
GCSE_YEARS = (2022, 2023)
TMUA_YEARS = (2022, 2023, 2024)

A_LEVEL_TABLE_HEADINGS = ("Grade Combination", "Frequency", "Percentage (%)")
GCSE_TABLE_HEADINGS = ("Number of 9s", "Frequency", "Percentage (%)")
TMUA_TABLE_HEADINGS = ("Score", "Frequency", "Percentage (%)")


class Outcome(enum.Enum):
    original_college_offer = "Original College Offer"
    other_college_offer = "Other College Offer"
    winter_pool = "Winter Pool"
    nothing = "Nothing"
    any = "Any"


def matches_outcome(record: Record, outcome: Outcome) -> bool:
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

    def __init__(
        self, master: tk.Frame, callback: Callable, years: list[int]
    ) -> None:
        super().__init__(master)
        self._year = tk.IntVar(value=-1)
        self.all_years = years
        self.label = tk.Label(self, text="Year")
        self.label.grid(row=0, column=0)
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

    def __init__(self, master: tk.Frame, callback: Callable) -> None:
        super().__init__(master)
        self._outcome = tk.StringVar(
            value=Outcome.original_college_offer.value)
        self.label = tk.Label(self, text="Outcome")
        self.label.grid(row=0, column=0)
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


class ALevelAnalysis(tk.Frame):

    def __init__(self, master: CsStatsAnalysis) -> None:
        super().__init__(master)
        self.data = ALevel.get_data()
        self.year_setting = YearSetting(
            self, self.update_table, A_LEVEL_YEARS)
        self.outcome_setting = OutcomeSetting(self, self.update_table)
        self.table = Table(self, A_LEVEL_TABLE_HEADINGS, [])
        self.year_setting.pack(padx=10, pady=10)
        self.outcome_setting.pack(padx=10, pady=10)
        self.update_table()
    
    def update_table(self) -> None:
        self.table.destroy()
        years = self.year_setting.years
        outcome = self.outcome_setting.outcome
        matching_records = [
            record for record in self.data
            if record.year in years and matches_outcome(record, outcome)]
        counter = Counter(
            " ".join(record.grades) for record in matching_records)
        table_records = []
        for grade_combination, count in counter.most_common():
            percentage = f"{count / len(matching_records) * 100:.1f}"
            record = (grade_combination, count, percentage)
            table_records.append(record)
        table_records.append(("All", len(matching_records), "100.0"))
        self.table = Table(self, A_LEVEL_TABLE_HEADINGS, table_records)
        self.table.pack(padx=10, pady=10)


class GCSEAnalysis(tk.Frame):

    def __init__(self, master: CsStatsAnalysis) -> None:
        super().__init__(master)
        self.data = GCSE.get_data()
        self.year_setting = YearSetting(
            self, self.update_output, GCSE_YEARS)
        self.outcome_setting = OutcomeSetting(self, self.update_output)
        self.stats = tk.Label(self, justify=tk.LEFT)
        self.table = Table(self, GCSE_TABLE_HEADINGS, [])
        self.year_setting.pack(padx=10, pady=10)
        self.outcome_setting.pack(padx=10, pady=10)
        self.stats.pack(padx=10, pady=10)
        self.update_output()
    
    def update_output(self) -> None:
        years = self.year_setting.years
        outcome = self.outcome_setting.outcome
        matching_records = [
            record for record in self.data
            if record.year in years and matches_outcome(record, outcome)]
        nines = [record.nines for record in matching_records]
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
        table_records = []
        for nines_, count in counter.most_common():
            percentage = f"{count / len(nines) * 100:.1f}"
            record = (nines_, count, percentage)
            table_records.append(record)
        table_records.append(("All", len(nines), "100.0"))
        self.table.destroy()
        self.table = Table(self, GCSE_TABLE_HEADINGS, table_records)
        self.stats.config(text=stats_text)
        self.table.pack(padx=10, pady=10)


class TMUAAnalysis(tk.Frame):

    def __init__(self, master: CsStatsAnalysis) -> None:
        super().__init__(master)
        self.data = TMUA.get_data()
        self.year_setting = YearSetting(
            self, self.update_output, TMUA_YEARS)
        self.outcome_setting = OutcomeSetting(self, self.update_output)
        self.notebook = ttk.Notebook(self)
        self.year_setting.pack(padx=10, pady=10)
        self.outcome_setting.pack(padx=10, pady=10)
        self.update_output()

    def update_output(self) -> None:
        years = self.year_setting.years
        outcome = self.outcome_setting.outcome
        matching_records = [
            record for record in self.data
            if record.year in years and matches_outcome(record, outcome)]
        self.notebook.destroy()
        self.notebook = ttk.Notebook(self)
        paper1 = TMUADataFrame(
            self.notebook, "Paper 1",
            [record.paper1 for record in matching_records]
        )
        paper2 = TMUADataFrame(
            self.notebook, "Paper 2",
            [record.paper2 for record in matching_records]
        )
        overall = TMUADataFrame(
            self.notebook, "Overall",
            [record.overall for record in matching_records]
        )
        self.notebook.add(paper1, text="Paper 1")
        self.notebook.add(paper2, text="Paper 2")
        self.notebook.add(overall, text="Overall")
        self.notebook.pack(padx=10, pady=10)


class TMUADataFrame(tk.Frame):

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
        table_records = []
        for score, count in counter.most_common():
            percentage = f"{count / len(results) * 100:.1f}"
            record = (score, count, percentage)
            table_records.append(record)
        table_records.append(("All", len(results), "100.0"))
        self.stats_label = tk.Label(self, text=stats_text, justify=tk.LEFT)
        self.table = Table(self, TMUA_TABLE_HEADINGS, table_records)
        self.stats_label.pack(padx=10, pady=10)
        self.table.pack(padx=10, pady=10)


def main() -> None:
    ctypes.windll.shcore.SetProcessDpiAwareness(True)
    CsStatsAnalysis().mainloop()


if __name__ == "__main__":
    main()