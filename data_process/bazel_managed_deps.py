import asyncio
import csv
import logging
import os
import re

from util.file import get_filepaths

bazel_dir_matcher = re.compile(r"/(root|home/zhengshenyu)/.cache/bazel/.*")
external_dep_matcher = re.compile(r"/(root|home/zhengshenyu)/.cache/bazel/_bazel_root/[^/]+/external/([^/]+)/")


def process_bazel_managed_deps(syscall_logs_path: str, output_path: str):
    tmp_output_path = output_path + ".tmp"
    dep_types = dict()

    async def _async_process_bazel_managed_deps():
        logging.info(f"processing Bazel-managed dependencies")
        with open(tmp_output_path, "w") as f:
            # f.write("project_name,dep_name,dep_type,path\n")
            f.write("project_name,dep_name,dep_type\n")

            log_line_queue = asyncio.Queue()
            loop = asyncio.get_event_loop()

            pending_files = get_filepaths(syscall_logs_path)
            pending_files_groups = [pending_files[i::5] for i in range(5)]
            log_file_reader_tasks = [loop.create_task(identify_bazel_managed_deps(pending_files_group, log_line_queue))
                                     for pending_files_group in pending_files_groups]
            log_filter = dict()
            result_writer_tasks = [loop.create_task(write_bazel_managed_deps(log_line_queue, f, log_filter, dep_types))
                                   for _ in range(5)]

            await asyncio.gather(*log_file_reader_tasks)

            await log_line_queue.join()

            for task in result_writer_tasks:
                task.cancel()

            logging.info(f"finished processing Bazel-managed dependencies for {syscall_logs_path}")

    asyncio.run(_async_process_bazel_managed_deps())

    post_process_bazel_managed_deps(tmp_output_path, output_path, dep_types)


def post_process_bazel_managed_deps(tmp_output_path: str, output_path: str, dep_types: dict):
    with open(tmp_output_path) as source, open(output_path, "w") as target:
        reader = csv.reader(source)
        next(reader)
        writer = csv.writer(target)

        writer.writerow(["project_name", "dep_name", "dep_type"])
        for row in reader:
            project_name, dep_name, dep_type = row
            if dep_name in dep_types[project_name]:
                dep_type = dep_types[project_name][dep_name]

            writer.writerow([project_name, dep_name, dep_type])

    os.remove(tmp_output_path)


async def identify_bazel_managed_deps(pending_files: [str], log_line_queue: asyncio.Queue):
    for f in pending_files:
        project_name = os.path.basename(f).replace(".csv", "")

        logging.info(f"process Bazel-managed dependencies for {project_name}")

        with open(f, "r") as log_file:
            next(log_file)
            for line in log_file:
                d = line.strip().split(",")
                syscall, path, succeed = d[1], d[2], d[-1]
                if succeed != "True":
                    continue

                if not bazel_dir_matcher.search(path):
                    continue

                if match := external_dep_matcher.search(line):
                    dep_name = match.group(2)
                    # remove __links suffix for dep name as some Javascript Bazel projects create multiple folder for
                    # the same dependency
                    if dep_name.endswith("__links"):
                        dep_name = dep_name[:-len("__links")]
                    dep_type = "toolchain" if syscall == "execve" else "library"

                    # relative_path_in_external = path.partition("/external/")[2]

                    await log_line_queue.put((project_name, dep_name, dep_type))
                    # await log_line_queue.put(f"{project_name},{dep_name},{dep_type},{relative_path_in_external}\n")
                    # relinquish control to other tasks
                    await asyncio.sleep(0)

        await log_line_queue.put((project_name,))


async def write_bazel_managed_deps(log_line_queue: asyncio.Queue, file, log_filter: dict, dep_types: dict):
    while True:
        line = await log_line_queue.get()
        try:
            project_name = line[0]
            if project_name not in log_filter:
                log_filter[project_name] = set()

            project_log_filter = log_filter[project_name]
            if len(line) == 1:
                project_log_filter.clear()
                del log_filter[project_name]
                continue

            if line in project_log_filter:
                continue

            _, dep_name, dep_type = line
            if project_name not in dep_types:
                dep_types[project_name] = {}

            project_dep_type = dep_types[project_name]
            if dep_name not in project_dep_type:
                project_dep_type[dep_name] = dep_type
            else:
                prev_dep_type = project_dep_type[dep_name]
                if prev_dep_type == "toolchain" or dep_type == "toolchain":
                    project_dep_type[dep_name] = "toolchain"
                    dep_type = "toolchain"

            if (project_name, dep_name, dep_type) in project_log_filter:
                continue

            project_log_filter.add(line)
            file.write(f"{project_name},{dep_name},{dep_type}\n")
        except Exception as e:
            logging.error(f"error writing Bazel-managed dependencies: {e}")
        finally:
            log_line_queue.task_done()
