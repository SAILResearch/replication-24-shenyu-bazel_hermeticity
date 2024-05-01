import logging
import re
from typing import Any

from lark import Transformer, Tree


def convert(cls):
    def f(self, children):
        return cls(children[0])

    return f


def first_child():
    def f(self, children):
        return children[0]

    return f


class JsonTransformer(Transformer):
    def start(self, children):
        return children

    def line(self, children):
        timestamp, body = children
        # body["pid"] = pid
        body["timestamp"] = timestamp
        return body

    def syscall(self, children):
        name, args, result = children
        return {
            "type": "syscall",
            "name": name,
            "args": unescape_hex_str(args),
            "result": unescape_hex_str(result),
        }

    def args(self, children):
        return str(children[0])

    def alert_body(self, children):
        return {
            "type": "alert",
            "result": str(children[0]),
        }

    key = convert(str)

    body = first_child()

    name = convert(str)

    result = convert(str)

    timestamp = convert(float)

    value = first_child()


def unescape_hex_str(s: str):
    try:
        # we only unescape strings like this "\x2f\x72"`
        for escaped in re.findall(r"(?:\\x[0-9a-fA-F]{2})+", s):
            s = s.replace(escaped, bytes.fromhex(escaped.replace(r"\x", "")).decode("utf-8"))
    except Exception as e:
        logging.debug(f"unable to unescape hex string {s}, skip it")
    return s


def to_json(tree: Tree) -> Any:
    return JsonTransformer().transform(tree)
