import re
from functools import lru_cache
from importlib.resources import read_text

from lark import Lark

import data as data
from json_transformer import JsonTransformer


@lru_cache(1)
def get_parser() -> Lark:
    grammar = read_text(data, "grammar.txt")
    return Lark(grammar, parser="lalr")


def ignore_errors(e):
    print(e)


class Parser:
    def __init__(self):
        self.parser = get_parser()
        self.transformer = JsonTransformer()

    def parse(self, trace_log):
        trace_log = re.sub(r'(?m)^.* --- SIG.*\n?', '', trace_log)
        trace_log = re.sub(r'(?m)^[^0-9]+.*\n?', '', trace_log)
        trace_log = re.sub(r'\s*/\*.*\*/\s*', '', trace_log)

        tree = self.parser.parse(trace_log, on_error=ignore_errors)

        events = self.transformer.transform(tree)
        events = sorted(events, key=lambda x: x["timestamp"])

        return events





if __name__ == "__main__":
    parser = Parser()
    with open("testdata/test_log.log", "r") as f:
        trace_log = f.read()
        events = parser.parse(trace_log)
        print(events)