""""Handles the storage of the data in the SQLite database."""
import pathlib
import sqlite3
import time
from dataclasses import dataclass


FOLDER = pathlib.Path(__file__).parent.parent
DATA_FILE = FOLDER / "data.pdf"
DATA_FOLDER = FOLDER / "data"
DATA_FOLDER.mkdir(exist_ok=True)

# Special strings to denote outcomes.
ORIGINAL_COLLEGE = "Y0"
OTHER_COLLEGE = "Y1"
WINTER_POOL = "Y2"

# Possible A-Level grades (except U).
GRADES = {"A*", "A", "B", "C", "D", "E"}

DATABASE = None


def new_database() -> None:
    """A new database will be created for operation."""
    global DATABASE
    DATABASE = DATA_FOLDER / f"data_{int(time.time())}.db"


def most_recent_database() -> None:
    """The most recent database by timestamp will be accessed."""
    global DATABASE
    databases = DATA_FOLDER.rglob("*.db")
    DATABASE = max(databases, key=lambda db: int(db.stem.split("_")[1]))


class Database:
    """Convenient SQLite database wrapper."""

    def __enter__(self) -> sqlite3.Cursor:
        """Start of database operation."""
        self.connection = sqlite3.connect(DATABASE)
        cursor = self.connection.cursor()
        return cursor
    
    def __exit__(self, exception: Exception | None, *_) -> None:
        """End of database operation - commit if error-free."""
        if exception is None:
            self.connection.commit()
        self.connection.close()
        self.connection = None


@dataclass
class Record:
    """Common fields for all specific data records."""
    id: int # Applicant ID
    year: int # Year being applied for
    original_college: bool # Whether the original college gave an offer.
    other_college: bool # Whether another college gave an offer.
    winter_pool: bool # Whether the applicant was pooled.

    @property
    def export_record(self) -> tuple:
        return (
            self.year, self.id, self.original_college, self.other_college,
            self.winter_pool
        )
    
    @property
    def json_object(self) -> dict:
        return {
            "year": self.year,
            "apply_id": self.id,
            "original_college": bool(self.original_college),
            "other_college": bool(self.other_college),
            "winter_pool": bool(self.winter_pool)
        }


@dataclass
class ALevel(Record):
    """Outcome based on A-Level predicted grades."""
    grades: list[str] # List of predicted grades (A*-E)

    @staticmethod
    def create_table() -> None:
        """Creates the A-Level data table."""
        with Database() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS alevel(
                    id INTEGER PRIMARY KEY,
                    year INTEGER,
                    original_college BOOLEAN,
                    other_college BOOLEAN,
                    winter_pool BOOLEAN,
                    grades STRING
                )
                """
            )
    
    @staticmethod
    def insert_records(data: list["ALevel"]) -> None:
        """Inserts A-Level data records."""
        with Database() as cursor:
            for a_level in data:
                grades_string = " ".join(a_level.grades)
                cursor.execute(
                    """
                    INSERT INTO alevel
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (a_level.id, a_level.year,
                          a_level.original_college, a_level.other_college,
                          a_level.winter_pool, grades_string)
                )

    @staticmethod
    def get_data() -> list["ALevel"]:
        """Retrieves all A-Level data records."""
        with Database() as cursor:
            records = cursor.execute("SELECT * FROM alevel").fetchall()
        a_levels = []
        for record in records:
            (id_, year, original_college,
             other_college, winter_pool, grades) = record
            grades = grades.split()
            a_level = ALevel(
                id_, year, original_college,
                other_college, winter_pool, grades)
            a_levels.append(a_level)
        return a_levels

    @staticmethod
    def from_words(record: list[str]) -> "ALevel":
        """Processes a raw record from the PDF to create an A-Level object."""
        year = int(record[7])
        id_ = int(record[8])
        original_college = ORIGINAL_COLLEGE in record
        other_college = OTHER_COLLEGE in record
        winter_pool = WINTER_POOL in record
        grades = []
        # Predicted grades succeed ': '.
        # Cannot just search for grades instances e.g. "Chemistry B"
        # is not a grade, but the title of an A-Level.
        for i, word in enumerate(record):
            if word.endswith(":") and record[i+1] in GRADES:
                grades.append(record[i+1])
        grades.sort()
        return ALevel(
            id_, year, original_college, other_college, winter_pool, grades)
    
    @property
    def export_record(self) -> tuple:
        return super().export_record + (" ".join(self.grades),)
    
    @property
    def json_object(self) -> dict:
        return super().json_object | {"grades": self.grades}


@dataclass
class GCSE(Record):
    """Outcome based on number of 9s achieved at GCSE."""
    nines: int

    @staticmethod
    def create_table() -> None:
        """Creates the GCSE data table."""
        with Database() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS gcse(
                    id INTEGER PRIMARY KEY,
                    year INTEGER,
                    original_college BOOLEAN,
                    other_college BOOLEAN,
                    winter_pool BOOLEAN,
                    nines INTEGER
                )
                """
            )

    @staticmethod
    def insert_records(data: list["GCSE"]) -> None:
        """Inserts GCSE data records."""
        with Database() as cursor:
            for gcse in data:
                cursor.execute(
                    """
                    INSERT INTO gcse
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (gcse.id, gcse.year,
                          gcse.original_college, gcse.other_college,
                          gcse.winter_pool, gcse.nines)
                )
    
    @staticmethod
    def get_data() -> list["GCSE"]:
        """Retrieves GCSE data records."""
        with Database() as cursor:
            records = cursor.execute("SELECT * FROM gcse").fetchall()
        return [GCSE(*record) for record in records]

    @staticmethod
    def from_words(record: list[str]) -> "GCSE":
        """Processes a raw record from the PDF to create an GCSE object."""
        year = int(record[6])
        id_ = int(record[7])
        original_college = ORIGINAL_COLLEGE in record
        other_college = OTHER_COLLEGE in record
        winter_pool = WINTER_POOL in record
        nines = int(record[-1])
        return GCSE(
            id_, year, original_college, other_college, winter_pool, nines)

    @property
    def export_record(self) -> tuple:
        return super().export_record + (self.nines,)
    
    @property
    def json_object(self) -> dict:
        return super().json_object | {"nines": self.nines}


@dataclass
class TMUA(Record):
    """Outcome based on TMUA performance."""
    paper1: float # Paper 1 score [1.0, 9.0]
    paper2: float # Paper 2 score [1.0, 9.0]
    overall: float # Overall score [1.0, 9.0]

    @staticmethod
    def create_table() -> None:
        """Creates the TMUA data table."""
        with Database() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tmua(
                    id INTEGER PRIMARY KEY,
                    year INTEGER,
                    original_college BOOLEAN,
                    other_college BOOLEAN,
                    winter_pool BOOLEAN,
                    paper1 REAL,
                    paper2 REAL,
                    overall REAL
                )
                """
            )

    @staticmethod
    def insert_records(data: list["TMUA"]) -> None:
        """Inserts TMUA data records."""
        with Database() as cursor:
            for tmua in data:
                cursor.execute(
                    """
                    INSERT INTO tmua
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (tmua.id, tmua.year,
                          tmua.original_college, tmua.other_college,
                          tmua.winter_pool, tmua.paper1, tmua.paper2,
                          tmua.overall)
                )

    @staticmethod
    def get_data() -> list["TMUA"]:
        """Retrieves TMUA data records."""
        with Database() as cursor:
            records = cursor.execute("SELECT * FROM tmua").fetchall()
        return [TMUA(*record) for record in records]

    @staticmethod
    def from_words(record: list[str]) -> "TMUA":
        """Processes a raw record from the PDF to create a TMUA object."""
        year = int(record[3])
        id_ = int(record[4])
        original_college = ORIGINAL_COLLEGE in record
        other_college = OTHER_COLLEGE in record
        winter_pool = WINTER_POOL in record
        paper1, paper2, overall = map(float, record[-3:])
        return TMUA(
            id_, year, original_college, other_college, winter_pool,
            paper1, paper2, overall)
    
    @property
    def export_record(self) -> tuple:
        return super().export_record + (self.paper1, self.paper2, self.overall)
    
    @property
    def json_object(self) -> dict:
        return super().json_object | {
            "paper1": self.paper1,
            "paper2": self.paper2,
            "overall": self.overall
        }