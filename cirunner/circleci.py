import datetime
import re
import subprocess

import requests

from cirunner import Tool, InstalledToolAnalyzer


class CircleCIToolAnalyzer(InstalledToolAnalyzer):
    tag_name_regex = r"\d{4}\.\d{2}-(\d{2}\.\d{2})"

    def analyze(self) -> list[Tool]:
        runner_tags = self.get_runner_tags()

        tools = []
        for runner, tags in runner_tags.items():
            for tag, date in tags:
                print(f"starting to analyze the installed tools for {tag}")

                cmd = f"docker run --rm cimg/base:{tag} apt list --installed"

                proc = subprocess.run(
                    [cmd],
                    capture_output=True,
                    text=True,
                    shell=True
                )

                if proc.returncode != 0:
                    raise Exception(f"{proc.stderr}")

                for m in re.finditer(r"(\S+)/\w+ (\S+) \S+ \[\S+]", proc.stdout):
                    tool_name = m.group(1)
                    tool_version = m.group(2)
                    tool = Tool(tool_name, tool_version, date, runner)
                    tools.append(tool)
        return tools


    def get_img_tags(self) -> list[dict]:
        url = "https://hub.docker.com/v2/repositories/cimg/base/tags?page_size=100&page=1"

        tags = []
        tag_res = requests.get(url).json()
        tags.extend(tag_res["results"])
        while tag_res["next"] is not None:
            tags.extend(tag_res["results"])
            tag_res = requests.get(tag_res["next"]).json()

        return tags

    def get_runner_tags(self) -> dict[str, list[tuple[str, datetime.datetime]]]:
        tags = self.get_img_tags()

        runner_tags = {}
        for tag in tags:
            tag_name = tag["name"]
            if m := re.match(self.tag_name_regex, tag_name):
                runner = m.group(1)
                date = datetime.datetime.strptime(tag["tag_last_pushed"], "%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                print(f"will not process tag {tag_name} since we cannot know which runner it is for")
                continue

            if runner not in runner_tags:
                runner_tags[runner] = []
            runner_tags[runner].append((tag_name, date))

        return runner_tags
