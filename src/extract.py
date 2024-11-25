import pathlib
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass 

import fitz


FOLDER = pathlib.Path(__file__).parent.parent
DATA_FILE = FOLDER / "data.pdf"
DATA_FOLDER = FOLDER / "data"
if __name__ == "__main__":
    DATABASE = DATA_FOLDER / f"data_{int(time.time())}.db"
else:
    databases = DATA_FOLDER.rglob("*.db")
    DATABASE = max(databases, key=lambda db: int(db.stem.split("_")[1]))
FIRST_PAGE = 3
LAST_PAGE = 100

ORIGINAL_COLLEGE = "Y0"
OTHER_COLLEGE = "Y1"
WINTER_POOL = "Y2"

GRADES = {"A*", "A", "B", "C", "D", "E"}


class Database:

    def __enter__(self) -> sqlite3.Cursor:
        self.connection = sqlite3.connect(DATABASE)
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        return cursor
    
    def __exit__(self, exception: Exception | None, *_) -> None:
        if exception is None:
            self.connection.commit()
        self.connection.close()
        self.connection = None


@dataclass
class Record:
    id: int
    year: int
    original_college: bool
    other_college: bool
    winter_pool: bool


@dataclass
class ALevel(Record):
    grades: list[str]

    @staticmethod
    def create_table() -> None:
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
        year = int(record[7])
        id_ = int(record[8])
        original_college = ORIGINAL_COLLEGE in record
        other_college = OTHER_COLLEGE in record
        winter_pool = WINTER_POOL in record
        grades = []
        for i, word in enumerate(record):
            if word.endswith(":") and record[i+1] in GRADES:
                grades.append(record[i+1])
        grades.sort()
        return ALevel(
            id_, year, original_college, other_college, winter_pool, grades)


@dataclass
class GCSE(Record):
    nines: int

    @staticmethod
    def create_table() -> None:
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
        with Database() as cursor:
            records = cursor.execute("SELECT * FROM gcse").fetchall()
        return [GCSE(*record) for record in records]

    @staticmethod
    def from_words(record: list[str]) -> "GCSE":
        year = int(record[6])
        id_ = int(record[7])
        original_college = ORIGINAL_COLLEGE in record
        other_college = OTHER_COLLEGE in record
        winter_pool = WINTER_POOL in record
        nines = int(record[-1])
        return GCSE(
            id_, year, original_college, other_college, winter_pool, nines)


@dataclass
class TMUA(Record):
    paper1: float
    paper2: float
    overall: float

    @staticmethod
    def create_table() -> None:
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
        with Database() as cursor:
            records = cursor.execute("SELECT * FROM tmua").fetchall()
        return [TMUA(*record) for record in records]

    @staticmethod
    def from_words(record: list[str]) -> "TMUA":
        year = int(record[3])
        id_ = int(record[4])
        original_college = ORIGINAL_COLLEGE in record
        other_college = OTHER_COLLEGE in record
        winter_pool = WINTER_POOL in record
        paper1, paper2, overall = map(float, record[-3:])
        return TMUA(
            id_, year, original_college, other_college, winter_pool,
            paper1, paper2, overall)


@dataclass
class Word:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    word: str
    block: int


def get_words(file: pathlib.Path, page: int) -> list[Word]:
    with fitz.Document(file) as doc:
        return [Word(*block[:6]) for block in doc[page-1].get_text("words")]
    

def main() -> None:
    yes_x_range = [None, None, None]
    for page in range(FIRST_PAGE, LAST_PAGE + 1):
        print(f"Page {page} / {LAST_PAGE}")
        words = get_words(DATA_FILE, page)
        block_words = defaultdict(list)
        for i, word in enumerate(words):
            block_words[word.block].append(word.word)
            for j, (word1, word2) in enumerate((
                ("Original", "College"),
                ("Other", "College"),
                ("in", "Winter")
            )):
                if word.word == word1 and words[i+1].word == word2:
                    yes_x_range[j] = (word.min_x, words[i+1].max_x)
            if word.word == "Y" and all(yes_x_range):
                for i in range(3):
                    if yes_x_range[i][0] <= word.min_x <= yes_x_range[i][1]:
                        block_words[word.block].append(f"Y{i}")
        data = []
        for record in block_words.values():
            if record[3] == "A":
                data.append(ALevel.from_words(record))
            elif record[3] == "GCSE":
                data.append(GCSE.from_words(record))
            elif record[0] == "Computer":
                tmua = TMUA.from_words(record)
                if (
                    not 1 <= tmua.paper1 <= 9
                    or not 1 <= tmua.paper2 <= 9 or not 1 <= tmua.overall <= 9
                ):
                    # Data issues - ignore.
                    # E.g. missing Paper 2 score for ID 302936
                    continue
                data.append(tmua)
        type(data[0]).insert_records(data)


if __name__ == "__main__":
    DATA_FOLDER.mkdir(exist_ok=True)
    for data_class in (ALevel, GCSE, TMUA):
        data_class.create_table()
    main()