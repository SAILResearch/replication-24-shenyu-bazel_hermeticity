from strace_parser.parser import Parser

if __name__ == "__main__":
    parser = Parser()

    with open("./testdata/trace.log", "r") as tl:
        trace_log = tl.read()

    parser.parse(trace_log)
