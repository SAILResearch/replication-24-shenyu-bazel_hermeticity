import asyncio
import logging
import os
from zipfile import ZipFile

import strace_parser.parser as strace_parser
from util.file import get_filepaths

parser = strace_parser.get_parser()


def process_syscall_logs(strace_data_path: str, output_path: str):
    async def _async_process_syscall_logs():
        log_line_queue = asyncio.Queue()
        parsed_line_queue = asyncio.Queue()

        loop = asyncio.get_event_loop()

        pending_files = get_filepaths(strace_data_path)
        pending_files_groups = [pending_files[i::5] for i in range(5)]
        log_file_reader_tasks = [loop.create_task(iter_strace_logs(pending_files_group, log_line_queue, output_path))
                                 for pending_files_group in pending_files_groups]

        log_file_processor_tasks = [loop.create_task(parse_strace_line(log_line_queue, parsed_line_queue)) for _ in
                                    range(5)]
        fds = {}
        result_writer_tasks = [loop.create_task(write_parsed_line(parsed_line_queue, fds, output_path)) for _ in
                               range(5)]

        await asyncio.gather(*log_file_reader_tasks)

        await log_line_queue.join()
        await parsed_line_queue.join()

        for task in log_file_processor_tasks:
            task.cancel()
        for task in result_writer_tasks:
            task.cancel()
        for _, fd in fds.items():
            fd.close()

        logging.info(f"finished processing syscall logs for {strace_data_path}")

    asyncio.run(_async_process_syscall_logs())


async def iter_strace_logs(pending_files: [str], log_line_queue: asyncio.Queue, output_path: str):
    for f in pending_files:
        project_name = os.path.basename(f).replace("_trace_logs.zip", "")

        logging.info(f"processing strace logs for {project_name}")

        if os.path.exists(os.path.join(output_path, f"{project_name}.csv")):
            logging.info(f"skipping {project_name} since it is already processed")
            continue

        with ZipFile(f, "r") as zf:
            for log_archive in zf.namelist():
                with zf.open(log_archive, "r") as log_file:
                    for line in log_file:
                        await log_line_queue.put((project_name, line))
                        # relinquish control to other tasks
                        await asyncio.sleep(0)


async def parse_strace_line(log_line_queue: asyncio.Queue, parsed_line_queue: asyncio.Queue):
    while True:
        project_name, line = await log_line_queue.get()

        try:
            evt = parser.parse(line.decode("utf-8"))[0]
            paths, succeed = strace_parser.util.extract_path_from_system_call_evt(evt)
            if paths is None or len(paths) == 0:
                continue
            await parsed_line_queue.put((project_name, evt["name"], paths, succeed))
        except Exception as e:
            logging.warning(f"failed to parse line {line}, reason {e}")
        finally:
            log_line_queue.task_done()


async def write_parsed_line(parsed_line_queue: asyncio.Queue, fds, output_base_path: str):
    while True:
        project_name, syscall, paths, succeed = await parsed_line_queue.get()
        if project_name not in fds:
            output_file_path = os.path.join(output_base_path, f"{project_name}.csv")
            output_file = open(output_file_path, "w")
            output_file.write("project,syscall,path,succeed\n")
            fds[project_name] = output_file
        else:
            output_file = fds[project_name]

        for path in paths:
            output_file.write(f"{project_name},{syscall},{path},{succeed}\n")
        parsed_line_queue.task_done()
