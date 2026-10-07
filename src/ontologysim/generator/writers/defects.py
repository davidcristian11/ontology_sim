from pathlib import Path

from openpyxl import Workbook


def write_defects(
    records: list[dict[str, object]],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "KPM"

    if not records:
        workbook.save(path)
        return

    headers = list(records[0])

    worksheet.append(headers)

    for record in records:
        worksheet.append([_excel_value(record.get(header)) for header in headers])

    workbook.save(path)


def _excel_value(value: object) -> object:
    if isinstance(value, list):
        return ";".join(str(item) for item in value)

    return value
