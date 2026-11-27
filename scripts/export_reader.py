"""Read and verify the relative documents used by the Niagara export indexer."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PureWindowsPath


class Quoted(str):
    """A string literal, never a DSL form name or keyword."""


@dataclass
class Form:
    items: list
    line: int
    column: int

    @property
    def head(self):
        return self.items[0] if self.items and type(self.items[0]) is str else None


class InvalidExport(ValueError):
    pass


def tokens(text):
    """Lex comments and JSON-compatible quoted escapes emitted by Quote()."""
    i, line, column = 0, 1, 1
    while i < len(text):
        char = text[i]
        if char.isspace():
            if char == "\n":
                line, column = line + 1, 1
            else:
                column += 1
            i += 1
            continue
        if char == ";":
            end = text.find("\n", i)
            if end < 0:
                return
            column += end - i
            i = end
            continue
        if char in "()":
            yield char, char, line, column
            i, column = i + 1, column + 1
            continue
        start, start_line, start_column = i, line, column
        if char == '"':
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise InvalidExport(f"Unterminated string at {start_line}:{start_column}")
            raw = text[start:i]
            try:
                value = Quoted(json.loads(raw))
            except ValueError as exc:
                raise InvalidExport(f"Invalid string escape at {start_line}:{start_column}: {exc}") from exc
            if i < len(text) and not (text[i].isspace() or text[i] in "();"):
                raise InvalidExport(f"Missing delimiter after string at {start_line}:{start_column}")
            # Raw control characters are rejected by json.loads; escaped newlines
            # do not change the source line number.
            column += len(raw)
            yield "atom", value, start_line, start_column
            continue
        while i < len(text) and not text[i].isspace() and text[i] not in '();"':
            if ord(text[i]) < 0x20:
                raise InvalidExport(f"Unexpected control character at {line}:{column + i - start}")
            i += 1
        if i == start or (i < len(text) and text[i] == '"'):
            raise InvalidExport(f"Unexpected quote in atom at {line}:{column}")
        value = text[start:i]
        column += i - start
        yield "atom", value, start_line, start_column


def parse(text):
    """Iterative parser: no recursion limit for nested function graphs."""
    roots, stack = [], []
    for kind, value, line, column in tokens(text):
        if kind == "(":
            form = Form([], line, column)
            (stack[-1].items if stack else roots).append(form)
            stack.append(form)
        elif kind == ")":
            if not stack:
                raise InvalidExport(f"Unexpected closing parenthesis at {line}:{column}")
            form = stack.pop()
            if not form.head:
                raise InvalidExport(f"Form needs an unquoted name at {form.line}:{form.column}")
        elif stack:
            stack[-1].items.append(value)
        else:
            raise InvalidExport(f"Atom outside a form at {line}:{column}")
    if stack:
        form = stack[-1]
        raise InvalidExport(f"Unclosed form at {form.line}:{form.column}")
    return roots


def children(form, head=None):
    return [item for item in form.items if isinstance(item, Form) and (head is None or item.head == head)]


def attrs(form):
    result = {}
    i = 1
    while i < len(form.items):
        key = form.items[i]
        if type(key) is str and key.startswith(":"):
            if key in result:
                raise InvalidExport(f"Duplicate {key} in {form.head} at line {form.line}")
            if i + 1 == len(form.items) or isinstance(form.items[i + 1], Form):
                raise InvalidExport(f"Missing scalar value for {key} at line {form.line}")
            value = form.items[i + 1]
            if type(value) is str and value.startswith(":"):
                raise InvalidExport(f"Missing value for {key} at line {form.line}")
            result[key], i = value, i + 2
        else:
            i += 1
    return result


def text_value(value, label):
    if not isinstance(value, str) or not value:
        raise InvalidExport(f"{label} must be a nonempty string")
    return str(value)


def list_value(value, label):
    if not isinstance(value, list):
        raise InvalidExport(f"{label} must be an array")
    return value


def object_value(value, label):
    if not isinstance(value, dict):
        raise InvalidExport(f"{label} must be an object")
    return value


def read_document(directory, description):
    description = object_value(description, "document")
    relative = text_value(description.get("path"), "document.path")
    # Manifest document paths are relative to the export directory, including
    # material provider documents. Reject absolute paths and traversal/symlinks.
    if Path(relative).is_absolute() or PureWindowsPath(relative).drive or PureWindowsPath(relative).root:
        raise InvalidExport(f"Document path is not relative: {relative}")
    path = (directory / relative).resolve()
    if not path.is_relative_to(directory):
        raise InvalidExport(f"Document path escapes export directory: {relative}")
    expected = text_value(description.get("sha256"), "document.sha256")
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise InvalidExport(f"Invalid SHA-256 for {relative}")
    text_value(description.get("format"), "document.format")
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise InvalidExport(f"SHA-256 mismatch for {relative}: expected {expected}, actual {actual}")
    text = data.decode("utf-8-sig", errors="strict")
    return text, {"path": relative, "sha256": actual, "bytes": len(data), "utf8": True}


def positional_id(form):
    if len(form.items) < 2 or type(form.items[1]) is not str or not form.items[1].startswith("$"):
        raise InvalidExport(f"{form.head} needs a local $id at line {form.line}")
    return form.items[1]
