import csv
import os
from os import path

import util.file
from release.query import package_release_dates


def process_packages(data_path: str):
    external_deps_dir_path = path.join(data_path, "package_processed")

    packages = extract_external_packages(external_deps_dir_path)
    for package in packages:
        print(package)

    result_dir = path.join(data_path, "package_release_dates")
    os.makedirs(result_dir, exist_ok=True)

    for package in packages:
        print(f"Processing package {package}")
        releases = package_release_dates(package)
        with open(path.join(result_dir, f"{package}.csv"), "w") as file:
            writer = csv.writer(file)
            writer.writerow(["package", "source_package", "date", "version", "repo"])
            for release in releases:
                writer.writerow([package, release.package, release.date, release.version, release.repo])


def extract_external_packages(external_deps_dir_path):
    packages = set()
    for f in util.file.get_filepaths(external_deps_dir_path):
        with open(f, "r") as file:
            reader = csv.reader(file)

            rows = list(reader)
        for row in rows:
            packages.add(row[1])
    packages.remove("unknown")
    packages.remove("pkg_name")
    return packages
