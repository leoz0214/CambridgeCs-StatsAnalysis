"""Script for extracting data from the PDF and saving it."""
from collections import defaultdict
from dataclasses import dataclass 

import fitz

from data import *


# Range of PDF page numbers containing the desired data.
FIRST_PAGE = 3
LAST_PAGE = 100


@dataclass
class Word:
    """Convenient data class - more readable than the 'word' tuple."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    word: str
    block: int # Block number
    

def main() -> None:
    """Main data extracton function."""
    # Unfortunately, the 'Y' which denotes Yes to a particular
    # outcome cannot be readily matched to its outcome
    # (original college / other college / pool).
    # Instead, the outcome a 'Y' denotes will be retrieved by
    # its x-ordinate in the PDF (which column the 'Y' belongs to).
    yes_x_range = [None, None, None]
    with fitz.Document(DATA_FILE) as doc:
        for page in range(FIRST_PAGE, LAST_PAGE + 1):
            print(f"Page {page} / {LAST_PAGE}")
            words = [
                Word(*block[:6]) for block in doc[page-1].get_text("words")]
            # Retrieves records.
            block_words = defaultdict(list)
            for i, word in enumerate(words):
                block_words[word.block].append(word.word)
                for j, (word1, word2) in enumerate((
                    ("Original", "College"),
                    ("Other", "College"),
                    ("in", "Winter")
                )):
                    if word.word == word1 and words[i+1].word == word2:
                        # Key words found, denoting a heading.
                        # Update the rough x-ordinate range for 'Y'
                        # to indicate it is for the current clumn.
                        yes_x_range[j] = (word.min_x, words[i+1].max_x)
                if word.word == "Y" and all(yes_x_range):
                    # Determine the outcome the 'Y' represents based on
                    # its left x-ordinate.
                    for j, (min_x, max_x) in enumerate(yes_x_range):
                        if min_x <= word.min_x <= max_x:
                            block_words[word.block].append(f"Y{j}")
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
                        or not 1 <= tmua.paper2 <= 9
                        or not 1 <= tmua.overall <= 9
                    ):
                        # Data issues - ignore.
                        # E.g. missing Paper 2 score for ID 302936
                        continue
                    data.append(tmua)
            # Insert records into the corresponding table,
            # noting the data list is homogeneous as a page only
            # contains one type of record.
            type(data[0]).insert_records(data)


if __name__ == "__main__":
    # Create a new database to populate data in.
    new_database()
    for data_class in (ALevel, GCSE, TMUA):
        data_class.create_table()
    main()