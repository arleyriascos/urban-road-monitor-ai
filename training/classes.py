"""Read the class names and the license from the data.yaml that comes with a dataset.

Roboflow and Ultralytics write that file in a few shapes, and none of them needs a full YAML
parser here: an inline list, a block list, or a block map from number to name.
"""

import ast
import re

_NAMES_LINE = re.compile(r"^names\s*:(.*)$")
_LICENSE_LINE = re.compile(r"^\s*license\s*:\s*(.+?)\s*$", re.MULTILINE)
_MAP_ITEM = re.compile(r"^(\d+)\s*:\s*(.+)$")


class ClassNamesError(ValueError):
    """The data.yaml has no class names, or they cannot be read."""


def read_class_names(yaml_text: str) -> list[str]:
    """Return the class names ordered by class number."""
    lines = yaml_text.splitlines()
    for index, line in enumerate(lines):
        match = _NAMES_LINE.match(line)
        if match is None:
            continue
        inline = _strip_comment(match.group(1)).strip()
        names = _parse_inline(inline) if inline else _parse_block(lines[index + 1 :])
        if not names:
            raise ClassNamesError("la lista 'names' del data.yaml está vacía")
        return names
    raise ClassNamesError("el data.yaml no tiene la clave 'names'")


def read_license(yaml_text: str) -> str | None:
    """Return the license written in the data.yaml, if there is one (Roboflow adds it)."""
    match = _LICENSE_LINE.search(yaml_text)
    if match is None:
        return None
    value = _unquote(_strip_comment(match.group(1)).strip())
    return value or None


def _strip_comment(text: str) -> str:
    """Remove a trailing ' # comment' that is not inside quotes."""
    quote: str | None = None
    for position, char in enumerate(text):
        if quote is not None:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "#" and (position == 0 or text[position - 1] in " \t"):
            return text[:position]
    return text


def _unquote(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def _parse_inline(text: str) -> list[str]:
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return _parse_inline_without_quotes(text)

    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value]
    if isinstance(value, dict):
        return _from_numbered({int(key): str(name).strip() for key, name in value.items()})
    raise ClassNamesError(f"no se entiende la lista de clases: {text}")


def _parse_inline_without_quotes(text: str) -> list[str]:
    """Read ``[a, b]`` or ``{0: a, 1: b}`` when the names are not quoted."""
    parts = [part.strip() for part in text[1:-1].split(",") if part.strip()]
    if text.startswith("[") and text.endswith("]"):
        return [_unquote(part) for part in parts]
    if text.startswith("{") and text.endswith("}"):
        numbered: dict[int, str] = {}
        for part in parts:
            item = _MAP_ITEM.match(part)
            if item is None:
                break
            numbered[int(item.group(1))] = _unquote(item.group(2).strip())
        else:
            return _from_numbered(numbered)
    raise ClassNamesError(f"no se entiende la lista de clases: {text}")


def _parse_block(lines: list[str]) -> list[str]:
    as_list: list[str] = []
    as_map: dict[int, str] = {}
    for line in lines:
        if not line.strip():
            continue
        content = _strip_comment(line).strip()
        indented = line[0] in " \t"
        if content.startswith("- "):
            as_list.append(_unquote(content[2:].strip()))
            continue
        map_match = _MAP_ITEM.match(content)
        if indented and map_match is not None:
            as_map[int(map_match.group(1))] = _unquote(map_match.group(2).strip())
            continue
        break
    if as_list and as_map:
        raise ClassNamesError("la lista 'names' mezcla elementos con '-' y con número")
    return as_list if as_list else _from_numbered(as_map)


def _from_numbered(numbered: dict[int, str]) -> list[str]:
    if sorted(numbered) != list(range(len(numbered))):
        raise ClassNamesError("los números de clase deben ir de 0 en adelante, sin huecos")
    return [numbered[number] for number in range(len(numbered))]
