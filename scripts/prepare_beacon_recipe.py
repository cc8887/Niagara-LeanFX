"""Write the bundled beacon template as a Niagara-UE-Lite recipe."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="File for the generated recipe")
    args = parser.parse_args()
    template = Path(__file__).resolve().parents[1] / "assets" / "converging-beacon.json"
    recipe = json.loads(template.read_text(encoding="utf-8"))
    for operation in recipe["operations"]:
        match operation["op"]:
            case "add-module":
                operation["asset"] = "/" + operation["asset"]
            case "add-renderer":
                operation["class"] = "/" + operation["class"]
            case "renderer-properties":
                properties = operation["properties"]
                properties["Material"] = "/" + properties["Material"]
    args.output.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
