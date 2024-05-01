import csv
import logging
import os

from util.file import get_filepaths

gnu_core_utils = ["chcon", "chmod", "chgrp", "chown", "chroot", "cp", "dd", "df", "dir", "dircolors", "du", "install", "ln",
                  "ls", "mkdir", "mkfifo", "mknod", "mktemp", "mv", "realpath", "rm", "rmdir", "shred", "stat", "sync",
                  "touch", "truncate", "vdir", "b2sum", "base32", "base64", "cat", "cksum", "comm", "csplit", "cut",
                  "expand", "fmt", "fold", "head", "join", "md5sum", "nl", "numfmt", "od", "paste", "pr", "ptx",
                  "sha1sum", "sha224sum", "sha256sum", "sha384sum", "sha512sum", "shuf", "sort", "split", "sum", "tac",
                  "tail", "tr", "tsort", "unexpand", "uniq", "wc", "who", "whoami", "yes", "arch", "basename", "date",
                  "dirname", "echo", "env", "expr", "factor", "false", "groups", "hostid", "id", "logname", "nice",
                  "nohup", "nproc", "pathchk", "pinky", "printenv", "printf", "pwd", "readlink", "runcon", "seq",
                  "sleep",
                  "stat", "stdbuf", "stty", "su", "tee", "test", "timeout", "true", "tty", "uname", "unlink", "uptime",
                  "users", "whoami", "yes"]

procps = ["kill", "ps", "sysctl", "free", "pgrep", "pkill", "pmap", "pwdx", "tload", "skill", "slabtop", "snice", "top",
          "uptime", "vmstat", "watch"]

binutils = ["addr2line", "ar", "as", "c++filt", "elfedit", "gprof", "ld", "ld.bfd", "ld.gold", "nm", "objcopy",
            "objdump", "ranlib", "readelf", "size", "strings", "strip"]


base_files = ["/etc/debian_version", "/etc/dpkg/origins/debian", "/etc/dpkg/origins/ubuntu", "/etc/host.conf",
              "/etc/issue", "/etc/issue.net", "/etc/legal", "/etc/lsb-release", "/etc/os-release",
              "/etc/profile.d/01-locale-fix.sh", "/etc/update-motd.d/00-header", "/etc/update-motd.d/10-help-text",
              "/etc/update-motd.d/50-motd-news", "/lib/systemd/system/motd-news.service",
              "/lib/systemd/system/motd-news.timer", "/usr/bin/locale-check", "/usr/lib/os-release",
              "/usr/share/base-files/dot.bashrc", "/usr/share/base-files/dot.profile",
              "/usr/share/base-files/dot.profile.md5sums", "/usr/share/base-files/info.dir",
              "/usr/share/base-files/motd", "/usr/share/base-files/networks", "/usr/share/base-files/profile",
              "/usr/share/base-files/profile.md5sums", "/usr/share/base-files/staff-group-for-usr-local",
              "/usr/share/common-licenses/Apache-2.0", "/usr/share/common-licenses/Artistic",
              "/usr/share/common-licenses/BSD", "/usr/share/common-licenses/CC0-1.0", "/usr/share/common-licenses/GFDL",
              "/usr/share/common-licenses/GFDL-1.2", "/usr/share/common-licenses/GFDL-1.3",
              "/usr/share/common-licenses/GPL", "/usr/share/common-licenses/GPL-1", "/usr/share/common-licenses/GPL-2",
              "/usr/share/common-licenses/GPL-3", "/usr/share/common-licenses/LGPL",
              "/usr/share/common-licenses/LGPL-2",
              "/usr/share/common-licenses/LGPL-2.1", "/usr/share/common-licenses/LGPL-3",
              "/usr/share/common-licenses/MPL-1.1",
              "/usr/share/common-licenses/MPL-2.0", "/usr/share/doc/base-files/FAQ", "/usr/share/doc/base-files/README",
              "/usr/share/doc/base-files/README.FHS", "/usr/share/doc/base-files/changelog.gz",
              "/usr/share/doc/base-files/copyright", "/usr/share/lintian/overrides/base-files"]


def process_external_packages(packages_path: str, output_base: str):
    logging.info(f"processing external packages from {packages_path}")
    for source_path in get_filepaths(packages_path):
        project_name = os.path.basename(source_path).replace(".csv", "")
        target_path = os.path.join(output_base, f"{project_name}.csv")

        with open(source_path, "r") as source_file, open(target_path, "w") as target_file:
            csv_reader = csv.reader(source_file)
            csv_writer = csv.writer(target_file)

            csv_writer.writerow(["project", "pkg_name", "syscall", "path", "type"])

            unknown_rows = []
            package_type = {}
            known_rows = []
            # project,pkg_name,syscall,path,type
            for row in csv_reader:
                project, pkg_name, syscall, path, pkg_type = row
                if pkg_name == "unknown":
                    unknown_rows.append(row)
                    continue

                package_type[pkg_name] = pkg_type
                known_rows.append(row)

            for unknown_row in unknown_rows:
                project, pkg_name, syscall, path, pkg_type = unknown_row
                if syscall == "execve":
                    if path.startswith("/usr/local/go"):
                        pkg_name = "golang"
                    executable_name = os.path.basename(path)
                    if executable_name == "bazel":
                        continue
                    if executable_name in gnu_core_utils:
                        pkg_name = "coreutils"
                    elif executable_name in procps:
                        pkg_name = "procps"
                    elif executable_name in binutils:
                        pkg_name = "binutils"
                    elif executable_name == "cc":
                        pkg_name = "gcc"
                    elif executable_name == "hostname":
                        pkg_name = "hostname"
                    elif executable_name == "sh":
                        pkg_name = "dash"
                    elif executable_name == "gzip":
                        pkg_name = "gzip"
                    elif executable_name == "cargo":
                        pkg_name = "cargo"
                    elif executable_name == "rustc":
                        pkg_name = "rustc"
                    elif executable_name == "grep":
                        pkg_name = "grep"
                    elif executable_name == "bash":
                        pkg_name = "bash"
                    elif executable_name == "sed":
                        pkg_name = "sed"
                    elif executable_name == "tar":
                        pkg_name = "tar"
                    elif executable_name == "locale":
                        pkg_name = "libc-bin"
                    elif executable_name == "awk":
                        pkg_name = "gawk"
                    elif executable_name == "python3":
                        pkg_name = "python3-minimal"
                    elif executable_name == "java":
                        for pkg, _ in package_type.items():
                            if pkg.startswith("openjdk"):
                                pkg_name = pkg
                                break

                elif path in base_files:
                    pkg_name = "base-files"
                elif path == "/etc/timezone":
                    pkg_name = "tzdata"
                elif path.startswith("/usr/lib/locale/C.UTF-8"):
                    pkg_name = "libc-bin"

                if pkg_name != "unknown":
                    pkg_type = package_type[pkg_name] if pkg_name in package_type else "top"
                    package_type[pkg_name] = pkg_type

                csv_writer.writerow([project, pkg_name, syscall, path, pkg_type])

            for row in known_rows:
                project, pkg_name, syscall, path, pkg_type = row
                if pkg_name == "libpcre3" and "grep" in package_type:
                    pkg_type = "transitive"
                if pkg_name == "libpython3.9-stdlib" and "python3-minimal" in package_type:
                    pkg_type = "transitive"
                if pkg_name == "liblz4-1" and "libsystemd0" in package_type:
                    pkg_type = "transitive"
                if pkg_name == "libprocps8" and "procps" in package_type:
                    pkg_type = "transitive"
                if pkg_name == "libgpg-error0" and "libgcrypt20" in package_type:
                    pkg_type = "transitive"
                if pkg_name == "libctf0" and "binutils" in package_type:
                    pkg_type = "transitive"
                if pkg_name  == "libpcre2-8-0" and "libselinux1" in package_type:
                    pkg_type = "transitive"
                if pkg_name in ("openjdk-17-jdk", "openjdk-17-jdk-headless") and "openjdk-17-jre-headless" in package_type:
                    pkg_type = package_type["openjdk-17-jre-headless"]
                    pkg_name = "openjdk-17-jre-headless"
                if pkg_name == "libatk-wrapper-java-jni" and "openjdk-17-jre-headless" in package_type:
                    pkg_type = "transitive"
                if pkg_name == "libkrb5-3" and ("libgssapi-krb5-2" in package_type or "libk5crypto3" in package_type):
                    pkg_type = "transitive"
                if pkg_name in ["libp11-kit0", "libtasn1-6"] and "libgnutls30" in package_type:
                    pkg_type = "transitive"
                if pkg_name in ["libldap-2.4-2", "libbrotli1", "libpsl5", "librtmp1", "libnghttp2-14"] and "libcurl3-gnutls" in package_type:
                    pkg_type = "transitive"
                if pkg_name == "libssh2-1" and ("cargo" in package_type or "libcurl3-gnutls" in package_type):
                    pkg_type = "transitive"
                if pkg_name == "libgcrypt20" and "libsystemd0" in package_type:
                    pkg_type = "transitive"
                if pkg_name in ["libsigsegv2", "libreadline8"] and "gawk" in package_type:
                    pkg_type = "transitive"
                if pkg_name in ["libssl1.1", "libexpat1"] and "libpython3.9-minimal" in package_type:
                    pkg_type = "transitive"
                if pkg_name == "gcc" and "g++-10" in package_type:
                    pkg_type = "transitive"
                if pkg_name == "binutils-x86-64-linux-gnu" and "gcc" in package_type:
                    pkg_type = "transitive"

                csv_writer.writerow([project, pkg_name, syscall, path, pkg_type])

    logging.info(f"finished processing external packages from {packages_path}")
