import csv

class CSVReader:
    @staticmethod
    def read_data(file_path, delimiter="\t"):
        with open(file_path, newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file, delimiter=delimiter))
