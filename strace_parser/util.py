import re
import cython


def extract_path_from_system_call_evt(evt) -> ([str], bool):
    sys_call_name = evt["name"]
    paths = []

    if "result" not in evt or "args" not in evt:
        return paths, False

    res = evt["result"]
    args = evt["args"]

    # creat,open,openat,rename,renameat,mkdir,mkdirat,rmdir,link,linkat,symlink,symlinkat,unlink,unlinkat,read,readv,write,writev,execve,execveat
    if sys_call_name in ["openat", "mkdirat"]:
        if res.startswith("-1"):
            # example args: 'AT_FDCWD, "/usr/lib/x86_64-linux-gnu/libmpc.so.3", O_RDONLY|O_CLOEXEC'
            paths = [args.split(", ")[1].strip('"')]
            return paths, False

        # example result: '3</usr/lib/x86_64-linux-gnu/libmpc.so.3.2.0>'
        matches = re.search(r"[0-9]+<(.*)>", res)
        if not matches:
            return paths, False

        paths = [matches.group(1)]

        return paths, True

    if sys_call_name in ["rename", "link", "symlink"]:
        # example args: '"MANIFEST.tmp", "MANIFEST"'
        paths = [p.strip('" ') for p in args.split(',')]

        return paths, not res.startswith("-1")

    if sys_call_name in ["mkdir", "rmdir", "unlink", "stat", "lstat", "execve"]:
        # example args: '"__main__/main", ...'
        paths = [args.split(", ")[0].strip('"')]
        return paths, not res.startswith("-1")

    if sys_call_name in ["symlinkat", "linkat", "unlinkat", "fstat", "read", "write", "execveat"]:
        # example args: '41</root/.cache/bazel/_bazel_root/9533582a5508bd6708f2c68b643bd2ca/external/rules_cc/temp3865738003580278094>, "rules_cc-0.0.2.tar.gz", 0'
        matches = re.search(r"[0-9]+<(.*)>", args.split(", ")[0])
        if not matches:
            return paths, False

        paths = [matches.group(1)]
        return paths, not res.startswith("-1")

    print(f"Could not extract path from system call {sys_call_name}, skip it")
    return None, None


read_operations = ["read", "readv", "open", "openat", "execv"]
write_operations = ["creat", "rename", "renameat", "rmdir", "link", "linkat", "symlinkat", "symlink", "unlink",
                    "unlinkat", "write", "writev"]


def syscall_operation_type(syscall: str) -> str:
    if syscall in read_operations:
        return "read"
    elif syscall in write_operations:
        return "write"
    else:
        return "others"


def syscall_operation_scope(path: str) -> str:
    if path.startswith(("/root/.cache/bazel", "/repo", "/home/zhengshenyu/experiments")) or not path.startswith("/"):
        return "managed"
    else:
        return "host"
