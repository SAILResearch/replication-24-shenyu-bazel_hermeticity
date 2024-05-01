import re
from functools import lru_cache
from importlib.resources import read_text

from lark import Lark

import strace_parser.data as data
from strace_parser.json_transformer import JsonTransformer


@lru_cache(1)
def get_parser() -> Lark:
    grammar = read_text(data, "grammar.txt")
    return Lark(grammar, parser="lalr", transformer=JsonTransformer())


def ignore_errors(e):
    # print(e)
    pass

class Parser:
    def __init__(self):
        self.parser = get_parser()

        self.clean_data_regexps = [
            re.compile(r'(?m)^.* --- SIG.*\n?'),
            re.compile(r'(?m)^[^0-9]+.*\n?'),
            re.compile(r'\s*/\*.*\*/\s*'),
        ]

    def parse(self, trace_log, sort=False):
        for regexp in self.clean_data_regexps:
            trace_log = regexp.sub('', trace_log)

        events = self.parser.parse(trace_log, on_error=ignore_errors)

        events = sorted(events, key=lambda x: x["timestamp"])

        return events
