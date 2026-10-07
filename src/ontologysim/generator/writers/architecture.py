from pathlib import Path
from xml.etree import ElementTree as ET


def write_architecture(
    data: dict[str, list[dict[str, object]]],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("AUTOSAR")

    ecus_element = ET.SubElement(root, "ECUS")

    for ecu in data["ecus"]:
        ecu_element = ET.SubElement(ecus_element, "ECU")

        for field, value in ecu.items():
            child = ET.SubElement(
                ecu_element,
                field.upper().replace("_", "-"),
            )

            if value is not None:
                child.text = str(value)

    components_element = ET.SubElement(
        root,
        "COMPONENTS",
    )

    for component in data["components"]:
        component_element = ET.SubElement(
            components_element,
            "COMPONENT",
        )

        for field, value in component.items():
            child = ET.SubElement(
                component_element,
                field.upper().replace("_", "-"),
            )

            if isinstance(value, list):
                child.text = ";".join(str(item) for item in value)
            elif value is not None:
                child.text = str(value)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    tree.write(
        path,
        encoding="utf-8",
        xml_declaration=True,
    )
