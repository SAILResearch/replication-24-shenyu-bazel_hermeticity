import os

from cirunner.circleci import CircleCIToolAnalyzer
from cirunner.gha import GHAToolAnalyzer


def process_installed_tools(data_path: str):
    data_dir = os.path.join(data_path, "installed_tools")

    # ci_tools = {"gha": GHAToolAnalyzer(), "circleci": CircleCIToolAnalyzer()}
    ci_tools = { "circleci": CircleCIToolAnalyzer()}

    for ci_name, analyzer in ci_tools.items():
        gha_installed_tools_dir = os.path.join(data_dir, ci_name)
        os.makedirs(gha_installed_tools_dir, exist_ok=True)

        tools = set(analyzer.analyze())

        runner_tools = {}
        for tool in tools:
            if tool.runner not in runner_tools:
                runner_tools[tool.runner] = []
            runner_tools[tool.runner].append(tool)

        for runner, installed_tools in runner_tools.items():
            runner_dir = os.path.join(gha_installed_tools_dir, runner)
            os.makedirs(runner_dir, exist_ok=True)

            tool_history = {}
            for tool in installed_tools:
                if tool.name not in tool_history:
                    tool_history[tool.name] = []
                tool_history[tool.name].append(tool)

            for tool_name, history in tool_history.items():
                history = sorted(history, key=lambda x: x.date)
                history_by_date = []

                for tool in history:
                    if len(history_by_date) == 0:
                        history_by_date.append([tool])
                    elif history_by_date[-1][0].date == tool.date:
                        history_by_date[-1].append(tool)
                    else:
                        history_by_date.append([tool])

                merged_history = []
                last_history_group = None

                for history_group in history_by_date:
                    if last_history_group is None:
                        last_history_group = history_group
                        merged_history.extend(history_group)
                        continue

                    if len(last_history_group) != len(history_group):
                        last_history_group = history_group
                        merged_history.extend(history_group)
                        continue

                    # if every tool in the history_group can find a tool with the same version in the last_history_group,
                    # then merge the history_group into the last_history_group
                    for tool in history_group:
                        if not any(x for x in last_history_group if x.version == tool.version):
                            last_history_group = history_group
                            merged_history.extend(history_group)
                            break

                with open(os.path.join(runner_dir, f"{tool_name}.csv"), "w") as file:
                    file.write("tool_name,version,date\n")
                    for tool in merged_history:
                        file.write(f"{tool.name},{tool.version},{tool.date.isoformat()}\n")
