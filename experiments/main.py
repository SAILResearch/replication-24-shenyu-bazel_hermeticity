import csv
import logging
import multiprocessing
import re
import subprocess
from parser import Parser as StraceParser

project_file_path = "./projects.csv"
experiment_results_dir_path = "./results"


class Project:
    def __init__(self, project, target):
        self.project = project
        self.project_org, self.project_name = project.split("_", maxsplit=1)
        self.target = target if target else "//:all"


class PkgInfo:
    def __init__(self, name: str, path: str, syscall: str, type: str):
        self.name = name
        self.path = path
        self.syscall = syscall
        self.type = type


def run_experiment(project: Project) -> [PkgInfo]:
    logging.info(f"start running experiment for {project.project}")
    logging.info(f"target: {project.target}")
    if not prepare_experiment(project):
        logging.error(f"failed to prepare experiment for {project.project_name}, skip it")
        return []

    cmd = f'./perform_build.sh -p {project.project_name} -t {project.target}'

    logging.info(f"starting collect the strace logs for {project.project_name}, build target {project.target}")
    process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = process.communicate(cmd.encode('utf-8'))

    if process.returncode != 0:
        logging.error(
            f"failed to run experiment for {project.project_name}, stdout: {stdout} error: {stderr}")
        raise Exception(f"failed to run experiment for {project.project_name}, stdout: {stdout} error: {stderr}")

    logging.info(f"successfully generate strace logs, starting to analyze them")
    return []
    # trace_logs_path = f"/results/{project.project_name}/merged_trace_logs.log"
    # return analyze_strace_logs(project, trace_logs_path)


# cloud-spanner-emulator
# rules_kotlin
# brunsli
# copybara
# go-jsonnet
# squzy
def analyze_strace_logs(project: Project, trace_logs_path: str) -> [PkgInfo]:
    logging.info(f"start identifying accessed packages for {project.project_name}")

    host_system_access = list(parse_trace_logs(trace_logs_path))

    with multiprocessing.Manager() as manager:
        L = manager.list()
        pool = multiprocessing.Pool(4)

        for i in range(4):
            logging.info(f"start identifying accessed packages for {project.project_name}, part {i}")
            pool.apply_async(identify_related_pkgs,
                             args=(L, i, host_system_access))

        pool.close()
        pool.join()
        accessed_pkgs = set(list(L))

    accessed_pkgs = analyze_dep_level(accessed_pkgs)

    return accessed_pkgs


cached_pkg_deps = {}


def analyze_dep_level(accessed_pkgs: set):
    for pkg in accessed_pkgs:
        if pkg[0] in cached_pkg_deps or pkg[0] == "unknown":
            continue

        cmd = f"apt-cache depends --no-recommends --no-suggests {pkg[0]}"
        process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate(cmd.encode('utf-8'))

        if process.returncode != 0:
            logging.warning(f"failed to run apt-cache depends for {pkg[0]}, stderr: {stderr}")
            continue

        if stdout:
            stdout = stdout.decode("utf-8")
            deps = stdout.split("\n")[1:]
            for dep in deps:
                # extract pkg, example: Depends: g++
                dep_segs = dep.split(":")
                if len(dep_segs) != 2:
                    continue

                dep_name = dep_segs[1].strip()
                if dep_name not in cached_pkg_deps:
                    cached_pkg_deps[dep_name] = set()
                cached_pkg_deps[dep_name].add(pkg[0])
        else:
            logging.warning(f"failed to run apt-cache depends for {pkg[0]}, stdout: {stdout}")
            continue

    pkgs = []
    for pkg in accessed_pkgs:
        if pkg[0] == "unknown":
            pkg_type = "unknown"
        elif pkg[0] in cached_pkg_deps:
            pkg_type = "transitive"
        else:
            pkg_type = "top"

        pkgs.append(PkgInfo(pkg[0], pkg[1], pkg[2], pkg_type))

    return pkgs


def identify_related_pkgs(L, i, host_system_access: list):
    try:
        accessed_pkgs = set()
        cached_matches = {}

        logging.info(f"{len(host_system_access) / 4} paths to be identified")
        for path in host_system_access[i::4]:
            if not path[2] or path[2] == "False":
                continue

            if path[1] in cached_matches:
                accessed_pkgs.add((cached_matches[path[1]], path[0], path[1]))
                continue

            # run apt-file search to find packages file belongs to
            cmd = f"apt-file search -F {path[1]}"
            process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            stdout, stderr = process.communicate(cmd.encode('utf-8'))

            logging.debug(f"[{i}] cmd {cmd} stdout {stdout} stderr {stderr}")
            if process.returncode != 0:
                if path[1].startswith("/usr/lib/x86_64-linux-gnu"):
                    cmd = f"apt-file search -F {path[1].replace('/usr/lib', '/lib')}"
                    process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                    stdout, stderr = process.communicate(cmd.encode('utf-8'))
                elif path[1].startswith("/usr/sbin"):
                    cmd = f"apt-file search -F {path[1].replace('/usr/sbin', '/usr/bin')}"
                    process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                    stdout, stderr = process.communicate(cmd.encode('utf-8'))

            if process.returncode != 0:
                logging.debug(f"[{i}] apt-file search found no package for path: {path[1]}")
                pkg_name = "unknown"
                cached_matches[path[1]] = pkg_name
                accessed_pkgs.add((pkg_name, path[0], path[1]))
            else:
                stdout = stdout.decode("utf-8")
                # get the first line of output
                query_res = stdout.split("\n")[0].split(":")
                if len(query_res) != 2:
                    logging.warning(f"no package found for path: {path[1]}")
                    pkg_name = "unknown"
                else:
                    pkg_name = stdout.split("\n")[0].split(":")[0]
                cached_matches[path[1]] = pkg_name
                logging.debug("[i] apt-file search found package %s for path: %s", pkg_name, path[1])
                accessed_pkgs.add((pkg_name, path[0], path[1]))

    except Exception as e:
        logging.error(f"failed to identify related packages for {path[1]}, reason {e}")

    L.extend(list(accessed_pkgs))


def parse_trace_logs(trace_logs_path: str):
    strace_parser = StraceParser()

    host_system_access = set()
    with open(trace_logs_path, "r") as f:
        for line in f:
            try:
                evt = strace_parser.parse(line)[0]
            except Exception as e:
                logging.error(f"failed to parse line {line}, reason {e}")
                continue

            if evt["type"] == "alert":
                continue

            if "args" in evt and ("<pipe" in evt["args"] or "<socket:" in evt["args"]):
                continue

            name, paths, succeed = extract_path_from_system_call_evt(evt)
            if paths is None or len(paths) == 0:
                continue

            for p in paths:
                if not p.startswith('/'):
                    continue

                if p.startswith(("/proc", "/root/.cache/bazel", "/repo", "/tmp")):
                    continue

                host_system_access.add((name, p, succeed))
    return host_system_access


def extract_path_from_system_call_evt(evt) -> (str, [str], bool):
    sys_call_name = evt["name"]
    paths = []

    if "result" not in evt or "args" not in evt:
        return sys_call_name, paths, False

    res = evt["result"]
    args = evt["args"]

    # creat,open,openat,rename,renameat,mkdir,mkdirat,rmdir,link,linkat,symlink,symlinkat,unlink,unlinkat,read,readv,write,writev,execve,execveat
    if sys_call_name in ["openat", "mkdirat"]:
        if res.startswith("-1"):
            # example args: 'AT_FDCWD, "/usr/lib/x86_64-linux-gnu/libmpc.so.3", O_RDONLY|O_CLOEXEC'
            paths = [args.split(", ")[1].strip('"')]
            return sys_call_name, paths, False

        # example result: '3</usr/lib/x86_64-linux-gnu/libmpc.so.3.2.0>'
        matches = re.search(r"[0-9]+<(.*)>", res)
        if not matches:
            return sys_call_name, paths, False

        paths = [matches.group(1)]

        return sys_call_name, paths, True

    if sys_call_name in ["rename", "link", "symlink"]:
        # example args: '"MANIFEST.tmp", "MANIFEST"'
        paths = [p.strip('" ') for p in args.split(',')]

        return sys_call_name, paths, not res.startswith("-1")

    if sys_call_name in ["mkdir", "rmdir", "unlink", "stat", "lstat", "execve"]:
        # example args: '"__main__/main", ...'
        paths = [args.split(", ")[0].strip('"')]
        return sys_call_name, paths, not res.startswith("-1")

    if sys_call_name in ["symlinkat", "linkat", "unlinkat", "fstat", "read", "write", "execveat"]:
        # example args: '41</root/.cache/bazel/_bazel_root/9533582a5508bd6708f2c68b643bd2ca/external/rules_cc/temp3865738003580278094>, "rules_cc-0.0.2.tar.gz", 0'
        matches = re.search(r"[0-9]+<(.*)>", args.split(", ")[0])
        if not matches:
            return sys_call_name, paths, False

        paths = [matches.group(1)]
        return sys_call_name, paths, not res.startswith("-1")

    print(f"Could not extract path from system call {sys_call_name}, skip it")
    return (sys_call_name, None, None)


def clone_repository(project) -> bool:
    project_git_url = f"https://github.com/{project.project_org}/{project.project_name}.git"
    cmd = f'''
    mkdir -p /repo/{project.project_name}
    if [ ! -d "/repo/{project.project_name}/{project.project_name}" ]; then
        git clone {project_git_url} /repo/{project.project_name}/{project.project_name}
    fi
    '''

    logging.info(f"cloning repository {project_git_url}")
    process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    _, err = process.communicate(cmd.encode('utf-8'))

    if process.returncode != 0:
        logging.error(f"failed to clone repository {project_git_url}, reason {err}")
        return False

    return True


def prepare_experiment(project):
    return clone_repository(project)


def start_experiments():
    logging.info("start experiments")

    with open(project_file_path, "r+") as project_file:
        project_reader = csv.DictReader(project_file, delimiter=",")
        projects = [Project(row["project"], row["target"]) for row in project_reader]

    for project in projects:
        try:
            results = run_experiment(project)
        except Exception as e:
            logging.error(f"fetal: failed to run experiment for {project.project}, reason {e}")
            continue
        with open(f"{experiment_results_dir_path}/{project.project_name}.csv", "w") as experiment_results_file:
            experiment_results_file.write("project,pkg_name,syscall,path,type\n")
            for res in results:
                experiment_results_file.write(
                    f"{project.project_name},{res.name},{res.path},{res.syscall},{res.type}\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p')
    start_experiments()
