"""Index authored Niagara2DSL stages and selected inputs in a Fab export."""

import argparse
import json
from pathlib import Path
import sys


def fields(dsl, form, names):
    attrs = dsl.attrs(form)
    return {name: attrs[":" + name] for name in names.split() if ":" + name in attrs}


def stage_index(dsl, script, queries):
    stage = fields(dsl, script, "usage usage-id")
    calls = {}
    for group in dsl.children(script, "effective-inputs"):
        for item in dsl.children(group, "effective-input"):
            at = dsl.attrs(item)
            if at[":module-state"] != "enabled-on-stage" or at[":value-status"].startswith("inactive"):
                continue
            key = (at[":function"], at[":node"])
            call = calls.setdefault(key, {"function": key[0], "node": key[1]})
            if at[":input"].casefold() not in queries:
                continue
            row = fields(dsl, item, "input source value-status branch-state")
            row["line"] = item.line
            # Take only immediate sources. Defaults or reads inside a shadowed
            # candidate would describe a different branch.
            row["sources"] = []
            for source in dsl.children(item):
                attrs = dsl.attrs(source)
                if source.head == "rapid-iteration" and attrs.get(":disposition") == "selected":
                    row["sources"].append(fields(dsl, source, "parameter value"))
                elif source.head == "default-binding" and attrs.get(":disposition") == "selected":
                    row["sources"].append(fields(dsl, source, "target"))
                elif source.head == "connection":
                    row["sources"].append(fields(dsl, source, "kind function output"))
                elif source.head == "literal" and at[":source"] == "callsite-literal":
                    row["sources"].append(fields(dsl, source, "value"))
                elif source.head == "script-default" and at[":source"] == "script-default":
                    if at[":value-status"] == "authored-value" and attrs.get(":disposition") in ("candidate", "selected"):
                        row["sources"].extend(
                            fields(dsl, value, "value object") for value in dsl.children(source, "literal")
                            if dsl.attrs(value).get(":ignored") != "true"
                        )
            call.setdefault("inputs", []).append(row)
    stage["calls_with_active_inputs"] = list(calls.values())
    return stage


def emitter_index(dsl, emitter, queries):
    row = fields(dsl, emitter, "name asset mode handle")
    row["id"] = dsl.positional_id(emitter)
    if ":enabled" in dsl.attrs(emitter):
        row["enabled"] = dsl.attrs(emitter)[":enabled"] == "true"
    unresolved = [fields(dsl, detail, "reason") for detail in dsl.children(emitter, "unresolved")]
    if unresolved:
        row["unresolved"] = unresolved
    row["line"] = emitter.line
    for settings in dsl.children(emitter, "emitter-settings"):
        row.update(fields(dsl, settings, "simulation"))
        for prop in dsl.children(settings, "property"):
            at = dsl.attrs(prop)
            if at.get(":name") == "bLocalSpace":
                row["local_space"] = at[":value"].casefold() == "true"
    row["stages"] = [stage_index(dsl, script, queries) for script in dsl.children(emitter, "script")]
    row["renderers"] = []
    for renderer in dsl.children(emitter, "renderer"):
        entry = fields(dsl, renderer, "index class enabled")
        if "enabled" in entry:
            entry["enabled"] = entry["enabled"] == "true"
        entry["id"] = dsl.positional_id(renderer)
        entry["line"] = renderer.line
        entry["material_references"] = [
            fields(dsl, ref, "asset resolution") for ref in dsl.children(renderer, "material-reference")
        ]
        row["renderers"].append(entry)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="Directory containing the Niagara2DSL manifest.json")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project with the Niagara2DSL plugin")
    parser.add_argument("--input", action="append", default=[], help="Exact Niagara input name; repeat as needed")
    args = parser.parse_args()
    plugin = args.project.resolve() / "Plugins/Niagara2DSL/Scripts"
    if not (plugin / "verify_export.py").is_file():
        parser.error("Pass the GASP58 root or another trusted project containing Plugins/Niagara2DSL via --project")
    sys.path.insert(0, str(plugin))
    import verify_export as dsl

    directory = args.export.resolve()
    queries = {name.casefold() for name in args.input}
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8-sig"))
        source, document = dsl.read_document(directory, manifest["document"])
        root, = dsl.parse(source)
        if root.head != "niagara-dsl" or dsl.attrs(root).get(":source") != manifest["source_asset"]:
            raise ValueError("Manifest and Niagara DSL source identity differ")
        systems = dsl.children(root, "system")
        result = {
            "asset": manifest["source_asset"], "engine": manifest.get("engine_version"),
            "dsl_sha256": document["sha256"], "coverage": manifest.get("coverage", {}).get("status"),
            "diagnostic_count": len(manifest.get("diagnostics", [])),
            "scope": "Authored inputs in each stage; call order and runtime values require separate evidence.",
            "user_defaults": [], "system_stages": [], "emitters": [],
        }
        for system in systems:
            for store in dsl.children(system, "parameters"):
                result["user_defaults"].extend(
                    fields(dsl, p, "name type value") for p in dsl.children(store, "parameter")
                    if dsl.attrs(p).get(":name", "").startswith("User.")
                )
            result["system_stages"].extend(stage_index(dsl, s, queries) for s in dsl.children(system, "script"))
        for parent in [root, *systems]:
            result["emitters"].extend(emitter_index(dsl, e, queries) for e in dsl.children(parent, "emitter"))
        if not systems and not result["emitters"]:
            raise ValueError("Unsupported Niagara DSL root layout")
    except (OSError, KeyError, ValueError) as error:
        parser.exit(1, f"Cannot index export: {error}\n")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
