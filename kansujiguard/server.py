"""MCP server (stdio, JSON-RPC 2.0). Python standard library only, no network.

Start: python -m kansujiguard.server
"""
import json
import sys

from . import __version__
from .guard import convert, parse_number

PROTOCOLS = ["2025-06-18", "2025-03-26", "2024-11-05"]
RO = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}

TOOLS = [
    {
        "name": "jp_kansuji_convert",
        "title": "Convert kanji numerals in Japanese text (safely)",
        "annotations": RO,
        "description": ("Convert kanji numerals in Japanese text to digits only where they are clearly numbers "
                        "(三億五千万円 -> 350000000円, 第三条 -> 第3条, 令和六年三月十五日 -> 令和6年3月15日, 金壱萬円 -> 金10000円). "
                        "Names, places, companies, words and idioms are kept (一宮市, 五十嵐, 三菱, 統一, 一石二鳥). "
                        "Spans whose meaning depends on the reading (十分, 一時, 一番, 二三人) or that are approximate (数万円) "
                        "are kept and returned in flags. Returns text, changes (start/end/before/after/value/reason), kept, flags. "
                        "Use before searching, indexing or extracting numbers from Japanese text. 漢数字を安全に数字へ。"),
        "inputSchema": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Japanese text"}}, "required": ["text"]},
    },
    {
        "name": "jp_kansuji_parse",
        "title": "Parse one Japanese numeral",
        "annotations": RO,
        "description": ("Parse one numeral string to an integer: kanji (三億五千万), formal daiji (壱萬, 参拾), flat digits "
                        "(二〇二四) or mixed (1億2,300万). Returns {value} or {value: null, error} when it is malformed."),
        "inputSchema": {"type": "object", "properties": {
            "numeral": {"type": "string"}}, "required": ["numeral"]},
    },
]


def _parse(a):
    s = _str_arg(a, "numeral")
    v = parse_number(s)
    return {"input": s, "value": v} if v is not None else {"input": s, "value": None, "error": "malformed numeral"}


def _str_arg(args, key):
    v = args.get(key)
    if not isinstance(v, str):
        raise ValueError(f"'{key}' must be a string")
    return v


HANDLERS = {
    "jp_kansuji_convert": lambda a: convert(_str_arg(a, "text")),
    "jp_kansuji_parse": _parse,
}


def handle(msg):
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:
        return None
    try:
        if method == "initialize":
            want = params.get("protocolVersion")
            result = {"protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                      "capabilities": {"tools": {"listChanged": False}},
                      "serverInfo": {"name": "jp-kansuji-guard", "version": __version__},
                      "instructions": "Before turning Japanese kanji numerals into digits, call jp_kansuji_convert. It never guesses: spans it cannot decide come back in flags, unchanged."}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            name = params.get("name")
            if name not in HANDLERS:
                return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
            try:
                out = HANDLERS[name](params.get("arguments") or {})
                result = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}],
                          "structuredContent": out, "isError": False}
            except ValueError as e:
                result = {"content": [{"type": "text", "text": str(e)}], "isError": True}
        else:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": mid, "result": result}
    except Exception as e:  # keep the server alive
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": f"Internal error: {e}"}}


def main():
    for s in (sys.stdin, sys.stdout):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}) + "\n")
            sys.stdout.flush()
            continue
        resp = handle(msg) if isinstance(msg, dict) else None
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
