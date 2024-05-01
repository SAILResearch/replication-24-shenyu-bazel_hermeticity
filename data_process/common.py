import pandas as pd
import util.file


def read_external_packages(external_deps_dir_path: str) -> pd.DataFrame:
    data = pd.DataFrame({})
    for f in util.file.get_filepaths(external_deps_dir_path):
        df = pd.read_csv(f).drop(columns=["path"]).dropna().drop_duplicates()

        df["category"] = df["type"].apply(lambda row: "Unmanaged (Top)" if row == "top" else "Unmanaged (Transitive)")
        df["dep_type"] = df["syscall"].map(lambda row: "toolchain" if row == "execve" else "library")
        df = df.drop(columns=["syscall", "type"]).drop_duplicates()
        df = df.rename(columns={"pkg_name": "dep_name", "project": "project_name"})

        # If a dep both appears in toolchain and library, we consider it as a toolchain dep
        toolchain_deps = df.loc[df["dep_type"] == "toolchain"]["dep_name"].unique()
        df["dep_type"] = df["dep_name"].map(lambda row: "toolchain" if row in toolchain_deps else "library")

        data = pd.concat([data, df])

    data = data.drop(data[data["dep_name"] == "unknown"].index)
    data = data.drop(data[data["project_name"] == "project"].index)
    return data.drop_duplicates()
