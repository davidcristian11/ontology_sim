from pathlib import Path
from xml.etree import ElementTree as ET


def write_requirements(
    records: list[dict[str, object]],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("REQ-IF")
    content = ET.SubElement(root, "REQ-IF-CONTENT")
    spec_objects = ET.SubElement(content, "SPEC-OBJECTS")

    for record in records:
        spec_object = ET.SubElement(spec_objects, "SPEC-OBJECT")

        for field, value in record.items():
            element = ET.SubElement(
                spec_object,
                field.upper().replace("_", "-"),
            )

            if isinstance(value, list):
                element.text = ";".join(str(item) for item in value)
            elif value is not None:
                element.text = str(value)

    tree = ET.ElementTree(root)

    ET.indent(tree, space="  ")

    tree.write(
        path,
        encoding="utf-8",
        xml_declaration=True,
    )
