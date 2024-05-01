import datetime
import re

import github.GithubException

from cirunner import Tool, InstalledToolAnalyzer


class GHAToolAnalyzer(InstalledToolAnalyzer):
    # runners = ["Ubuntu1804", "Ubuntu2004", "Ubuntu2204"]
    runners = ["Ubuntu1804", "Ubuntu2004", "Ubuntu2204"]

    def analyze(self) -> list[Tool]:
        tools = []
        for runner in self.runners:
            commits = []

            config_paths = [f"images/ubuntu/{runner}-Readme.md", f"images/linux/{runner}-Readme.md", f"images/linux/{runner}-README.md"]
            for config_path in config_paths:
                commits.extend(self.list_commits("actions", "runner-images", config_path))

            for commit, date, config_path in commits:
                print(f"Processing commit {commit} for runner {runner}")
                try:
                    file = self.get_file("actions", "runner-images", commit, config_path)
                    tools.extend(self.parse_version(file, runner, date))
                except github.GithubException as e:
                    print(f"Failed to get file {config_path} at commit {commit}: {e}")
        return tools

    def parse_version(self, toolset: str, runner_name, date: datetime.datetime) -> list[Tool]:
        blocks = re.split(r"(?:^|\n)#+ (.+)", toolset)
        blocks = list(filter(None, blocks))
        while len(blocks) > 0 and not blocks[0].startswith("Ubuntu"):
            blocks = blocks[1:]

        tools = []
        for block_title, block_details in zip(blocks[0::2], blocks[1::2]):
            block_title = block_title.strip()
            block_details = block_details.strip()
            # we don't care about these configurations
            if block_title in ("Environment variables", "Homebrew note", "Cached Docker images", ".NET Core SDK"):
                continue

            # these are cached tools that can be downloaded from GHA's cache server and are not installed in the image.
            if block_title in ("Go", "Node.js", "Python", "PyPy", "Ruby"):
                continue

            # if the first line of block details all is a line starts with `- `,
            # then it is a Markdown list showing the tools and their versions
            if re.match(r"- .*", block_details):
                for m in re.finditer(r"- (.*)", block_details):
                    tool_spec = m.group(1)
                    if m := re.match(r"([^:]+): (.+)", tool_spec):
                        tool_name = m.group(1).lower().replace(" ", "_")
                        tool_versions = m.group(2).split(", ")
                    elif m := re.match(r"(.+) (\S+)", tool_spec):
                        tool_name = m.group(1).lower().replace(" ", "_")
                        tool_versions = [m.group(2)]
                    else:
                        print(f"Could not parse tool spec {tool_spec} for {block_title}: {block_details}")
                        break

                    for tool_version in tool_versions:
                        tool_version = tool_version.strip()
                        tool = Tool(tool_name, tool_version, date, runner_name)
                        tools.append(tool)
            # if the first line of block details is a line starts with `| `,
            # then it is a Markdown table showing the tools and their versions
            elif re.match(r"\| .*", block_details):
                lines = block_details.split("\n")
                for line in lines[2:]:
                    line = line.strip()
                    # the table possibly ends
                    if not line.startswith("|"):
                        break

                    specs = line.strip(" |").split("|")
                    if block_title == "Java":
                        tool_version = specs[0].strip()
                        major_version = tool_version.split(".")[0]

                        tool_name = f"openjdk_{major_version}"
                        tool = Tool(tool_name, tool_version, date, runner_name)
                        tools.append(tool)
                        continue

                    tool_name = specs[0].strip().lower().replace(" ", "_")
                    tool_versions = re.split(r"<br>", specs[1])

                    for tool_version in tool_versions:
                        tool_version = tool_version.strip()
                        tool = Tool(tool_name, tool_version, date, runner_name)
                        tools.append(tool)

        return tools
