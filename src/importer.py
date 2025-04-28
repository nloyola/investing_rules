import argparse
from .base_command import BaseCommand
from rich.console import Console
import pandas as pd

console = Console()


class ImporterCommand(BaseCommand):
    _NAME = "import"
    _DESCRIPTION = "Imports stock tickers from an Excel file."

    def __init__(self) -> None:
        super().__init__(self._NAME, self._DESCRIPTION)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--excel", help="import ticker symbols from an Excel file")

    def handle(self, args: argparse.Namespace) -> None:
        excel_filename = args.excel
        if excel_filename is not None:
            self.excel_import(excel_filename)

    def excel_import(self, filename: str) -> None:
        excel_file = filename
        df = pd.read_excel(excel_file)

        # Convert to JSON
        json_data = df.to_json(orient="records", indent=4)

        # Save to a .json file
        with open("output.json", "w") as f:
            f.write(json_data)
