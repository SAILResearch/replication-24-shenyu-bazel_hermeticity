import os
import re
import shutil
from os import path

import git
import pandas as pd

import util.file
from data_process.common import read_external_packages

project_path = "externalmanaged/projects.csv"


def identify_package_for_projects(data_dir: str):
    projects_df = pd.read_csv(project_path)
    external_deps_df = read_external_packages(path.join(data_dir, "package_processed"))

    external_managed_packages = {}
    dockerfile_usage = {}
    for project in projects_df["project"]:
        org, project = project.split("_", maxsplit=1)
        tmp_path = path.join("/tmp", org, project)

        if project not in external_managed_packages:
            external_managed_packages[project] = set()

        if project not in dockerfile_usage:
            dockerfile_usage[project] = False

        # remove the directory if it exists
        shutil.rmtree(tmp_path, ignore_errors=True)
        os.makedirs(tmp_path)

        print(f"Cloning {project} from {org} into {tmp_path}...")
        git.Git(tmp_path).clone(f"https://github.com/{org}/{project}.git")

        packages = set(external_deps_df[external_deps_df["project_name"] == project]["dep_name"].unique())
        all_files = util.file.get_filepaths(tmp_path)
        dockerfile_usage[project] = any("Dockerfile" in f for f in all_files)

        for f in all_files:
            # print(f"Searching for packages in {f}...")
            if os.path.islink(f):
                continue

            with open(f, encoding="utf8", errors='ignore') as file:
                content = file.read()
                identified_package = None
                for package in packages:
                    m = re.search(rf"\s{package}[\s.]", content)
                    build_essential = False
                    if not m and package in ("dpkg-dev", "g++", "gcc", "libc6-dev", "libc-dev", "make"):
                        m = re.search(rf"\sbuild-essential[\s.]", content)
                        build_essential = True

                    if m:
                        print(f"Found possible usage {package} in {f}!")
                        external_managed_packages[project].add(package if not build_essential else f"{package}_build-essential")
                        # stop search as soon as we find a match and remove the package from the list to save time
                        identified_package = package
                        break
                if identified_package:
                    packages.remove(identified_package)

    with open(path.join(data_dir, "external_managed_packages.csv"), "w") as f:
        f.write("project_name,dep_name\n")
        for project, packages in external_managed_packages.items():
            for package in packages:
                f.write(f"{project},{package}\n")
    with open(path.join(data_dir, "dockerfile_usage.csv"), "w") as f:
        f.write("project_name,used_dockerfile\n")
        for project, used in dockerfile_usage.items():
            f.write(f"{project},{used}\n")
