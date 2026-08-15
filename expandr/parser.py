from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from expandr.models import Library


WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass
class FormField:
    name: str
    kind: str
    default: str = ""
    options: list[str] = field(default_factory=list)
    format: str = "YYYY-MM-DD"


@dataclass
class EvalResult:
    text: str
    cursor: int | None = None


class ParseError(Exception):
    pass


def _split_settings(raw: str) -> tuple[list[str], dict[str, str]]:
    positional: list[str] = []
    named: dict[str, str] = {}
    if not raw.strip():
        return positional, named
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    escaped = False
    for ch in raw:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == "{":
            depth += 1
            buf.append(ch)
            continue
        if ch == "}":
            depth = max(0, depth - 1)
            buf.append(ch)
            continue
        if ch == ";" and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    for part in parts:
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            named[key.strip()] = value.strip()
        else:
            positional.append(part)
    return positional, named


def _parse_nodes(text: str, i: int = 0, stop: set[str] | None = None) -> tuple[list[dict], int]:
    nodes: list[dict] = []
    literal: list[str] = []
    stop = stop or set()

    def flush() -> None:
        if literal:
            nodes.append({"type": "text", "text": "".join(literal)})
            literal.clear()

    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text) and text[i + 1] in "{}=;":
            literal.append(text[i + 1])
            i += 2
            continue
        if ch != "{":
            literal.append(ch)
            i += 1
            continue
        end = _matching_brace(text, i)
        inner = text[i + 1 : end]
        name, rest = _command_parts(inner)
        if name in stop:
            flush()
            return nodes, i
        flush()
        i = end + 1
        if name == "note":
            body, i = _parse_nodes(text, i, {"endnote"})
            i = _skip_command(text, i, "endnote")
            nodes.append({"type": "note", "body": body})
        elif name == "if":
            cond = rest.strip()
            branches = []
            body, i = _parse_nodes(text, i, {"else", "elseif", "endif"})
            branches.append((cond, body))
            while True:
                nxt_name, nxt_rest, i = _peek_command(text, i)
                if nxt_name == "elseif":
                    body, i = _parse_nodes(text, i, {"else", "elseif", "endif"})
                    branches.append((nxt_rest.strip(), body))
                elif nxt_name == "else":
                    else_body, i = _parse_nodes(text, i, {"endif"})
                    i = _skip_command(text, i, "endif")
                    nodes.append({"type": "if", "branches": branches, "else": else_body})
                    break
                else:
                    i = _skip_command(text, i, "endif")
                    nodes.append({"type": "if", "branches": branches, "else": []})
                    break
        elif name == "repeat":
            positional, named = _split_settings(rest)
            count = named.get("times") or (positional[0] if positional else "1")
            body, i = _parse_nodes(text, i, {"endrepeat"})
            i = _skip_command(text, i, "endrepeat")
            nodes.append({"type": "repeat", "count": count, "body": body})
        elif name == "formtoggle":
            positional, named = _split_settings(rest)
            body, i = _parse_nodes(text, i, {"endformtoggle"})
            i = _skip_command(text, i, "endformtoggle")
            nodes.append(
                {
                    "type": "command",
                    "name": "formtoggle",
                    "positional": positional,
                    "settings": named,
                    "body": body,
                }
            )
        else:
            positional, named = _split_settings(rest)
            nodes.append(
                {
                    "type": "command",
                    "name": name,
                    "positional": positional,
                    "settings": named,
                    "body": None,
                    "raw": rest,
                }
            )
    flush()
    return nodes, i


def _matching_brace(text: str, start: int) -> int:
    depth = 0
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ParseError("Unclosed command")


def _command_parts(inner: str) -> tuple[str, str]:
    inner = inner.strip()
    if inner.startswith("="):
        return "=", inner[1:].strip()
    match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", inner, re.S)
    if match and ":" not in match.group(1):
        return "assign", inner
    if ":" in inner:
        name, rest = inner.split(":", 1)
        return name.strip(), rest
    return inner.strip(), ""


def _peek_command(text: str, i: int) -> tuple[str | None, str, int]:
    while i < len(text) and text[i].isspace():
        i += 1
    if i >= len(text) or text[i] != "{":
        return None, "", i
    end = _matching_brace(text, i)
    name, rest = _command_parts(text[i + 1 : end])
    return name, rest, end + 1


def _skip_command(text: str, i: int, expected: str) -> int:
    name, _, nxt = _peek_command(text, i)
    if name == expected:
        return nxt
    return i


def parse(content: str) -> list[dict]:
    nodes, _ = _parse_nodes(content)
    return nodes


def collect_fields(nodes: list[dict], fields: list[FormField] | None = None) -> list[FormField]:
    fields = fields if fields is not None else []
    seen = {f.name for f in fields}
    for node in nodes:
        kind = node.get("type")
        if kind in {"note", "repeat"} or (kind == "command" and node.get("body")):
            collect_fields(node.get("body") or [], fields)
            seen = {f.name for f in fields}
        if kind == "if":
            for _, body in node.get("branches") or []:
                collect_fields(body, fields)
            collect_fields(node.get("else") or [], fields)
            seen = {f.name for f in fields}
        if kind != "command":
            continue
        name = node["name"]
        settings = node.get("settings") or {}
        field_name = settings.get("name") or name
        if name in {"formtext", "formparagraph", "formdate", "formmenu", "formtoggle"}:
            if field_name in seen:
                continue
            options = list(node.get("positional") or [])
            default = settings.get("default", "")
            if name == "formtoggle" and not default:
                default = "no"
            if name == "formmenu" and not default and options:
                default = options[0]
            if name == "formdate" and not default:
                default = datetime.now().strftime("%Y-%m-%d")
            fmt = (node.get("positional") or [None])[0] if name == "formdate" else "YYYY-MM-DD"
            if name == "formdate" and node.get("positional"):
                fmt = node["positional"][0]
            fields.append(
                FormField(
                    name=field_name,
                    kind=name,
                    default=default,
                    options=options,
                    format=fmt or "YYYY-MM-DD",
                )
            )
            seen.add(field_name)
    return fields


def _blaze_time_format(fmt: str) -> str:
    mapping = [
        ("YYYY", "%Y"),
        ("MMMM", "%B"),
        ("MMM", "%b"),
        ("MM", "%m"),
        ("DD", "%d"),
        ("HH", "%H"),
        ("hh", "%I"),
        ("mm", "%M"),
        ("ss", "%S"),
        ("A", "%p"),
        ("D", "%#d"),
    ]
    out = fmt
    for src, dest in mapping:
        out = out.replace(src, dest)
    return out


def _shift_datetime(value: datetime, shift: str) -> datetime:
    match = re.fullmatch(r"([+-]?)(\d+)([YMDWhms])", shift.strip())
    if not match:
        return value
    sign, amount_s, unit = match.groups()
    amount = int(amount_s) * (-1 if sign == "-" else 1)
    if unit == "Y":
        return value.replace(year=value.year + amount)
    if unit == "M":
        month = value.month - 1 + amount
        year = value.year + month // 12
        month = month % 12 + 1
        day = min(value.day, 28)
        return value.replace(year=year, month=month, day=day)
    deltas = {"D": timedelta(days=amount), "W": timedelta(weeks=amount), "h": timedelta(hours=amount), "m": timedelta(minutes=amount), "s": timedelta(seconds=amount)}
    return value + deltas[unit]


def _coerce(value: Any) -> Any:
    raw = str(value).strip()
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if re.fullmatch(r"-?\d+\.\d+", raw):
        return float(raw)
    return value


def _safe_eval(expr: str, ctx: dict[str, Any]) -> Any:
    expr = expr.strip()
    if not expr:
        return ""
    namespace = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "yes": True,
        "no": False,
    }
    namespace.update(ctx)
    try:
        return eval(expr, {"__builtins__": {}}, namespace)
    except Exception:
        return False


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().casefold()
    return text not in {"", "0", "no", "false", "off"}


def evaluate(
    content: str,
    answers: dict[str, Any],
    library: Library | None = None,
    clipboard: str = "",
    imported: set[str] | None = None,
) -> EvalResult:
    nodes = parse(content)
    ctx: dict[str, Any] = {key: _coerce(value) for key, value in answers.items()}
    chunks: list[str] = []
    cursor: int | None = None

    def walk(items: list[dict], silent: bool = False) -> None:
        nonlocal cursor
        for node in items:
            kind = node.get("type")
            if kind == "text":
                if not silent:
                    chunks.append(node["text"])
            elif kind == "note":
                walk(node["body"], silent=True)
            elif kind == "if":
                matched = False
                for cond, body in node["branches"]:
                    if _truthy(_safe_eval(cond, ctx)):
                        walk(body, silent)
                        matched = True
                        break
                if not matched:
                    walk(node.get("else") or [], silent)
            elif kind == "repeat":
                count_val = _safe_eval(str(node.get("count") or "1"), ctx)
                try:
                    count = int(count_val)
                except (TypeError, ValueError):
                    count = 1
                for _ in range(max(0, count)):
                    walk(node["body"], silent)
            elif kind == "command":
                _eval_command(node, silent)

    def _eval_command(node: dict, silent: bool) -> None:
        nonlocal cursor
        name = node["name"]
        settings = node.get("settings") or {}
        positional = node.get("positional") or []
        if name == "assign":
            raw = node.get("raw") or ""
            left, right = raw.split("=", 1)
            ctx[left.strip()] = _safe_eval(right, ctx)
            return
        if name == "=":
            value = _safe_eval(node.get("raw") or "", ctx)
            if not silent:
                chunks.append(str(value))
            return
        if name == "time":
            fmt = positional[0] if positional else "YYYY-MM-DD"
            now = datetime.now()
            if settings.get("at"):
                try:
                    now = datetime.fromisoformat(str(_safe_eval(settings["at"], ctx)))
                except ValueError:
                    pass
            if settings.get("shift"):
                now = _shift_datetime(now, settings["shift"])
            if not silent:
                chunks.append(now.strftime(_blaze_time_format(fmt)))
            return
        if name == "clipboard":
            if not silent:
                chunks.append(clipboard)
            return
        if name == "cursor":
            if not silent:
                cursor = sum(len(part) for part in chunks)
            return
        if name == "import":
            shortcut = (positional[0] if positional else settings.get("snippet") or "").strip()
            if library and shortcut:
                used = imported if imported is not None else set()
                key = shortcut.casefold()
                if key not in used:
                    used.add(key)
                    found = library.find_by_shortcut(shortcut)
                    if found:
                        nested = evaluate(found[1].content, answers, library, clipboard, used)
                        if not silent:
                            chunks.append(nested.text)
            return
        if name in {"formtext", "formparagraph", "formmenu", "formdate"}:
            field_name = settings.get("name") or name
            value = answers.get(field_name, settings.get("default", ""))
            ctx[field_name] = _coerce(value)
            if not silent:
                chunks.append(str(value))
            return
        if name == "formtoggle":
            field_name = settings.get("name") or "toggle"
            on = _truthy(answers.get(field_name, settings.get("default", "no")))
            ctx[field_name] = "yes" if on else "no"
            if on:
                walk(node.get("body") or [], silent)
            return

    walk(nodes)
    return EvalResult(text="".join(chunks), cursor=cursor)
