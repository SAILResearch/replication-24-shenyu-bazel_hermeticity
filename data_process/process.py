import os.path

from data_process.bazel_managed_deps import process_bazel_managed_deps
from data_process.external_packages import process_external_packages
from data_process.syscall_logs import process_syscall_logs


def process_data(data_path: str):
    # process_syscall_logs(os.path.join(data_path, "syscall"), os.path.join(data_path, "syscall_processed"))
    process_bazel_managed_deps(os.path.join(data_path, "syscall_processed"),
                               os.path.join(data_path, "bazel_managed_deps.csv"))
    # process_external_packages(os.path.join(data_path, "package"), os.path.join(data_path, "package_processed"))
