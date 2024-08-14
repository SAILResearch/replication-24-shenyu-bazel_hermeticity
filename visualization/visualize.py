import datetime
import itertools
import os.path
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import scipy
import seaborn as sns
from cliffs_delta import cliffs_delta
import scikit_posthocs as sp

import strace_parser.util
import util.file
from data_process.common import read_external_packages



def visualize(data_path: str):
    sns.set_theme(style="whitegrid")
    # visualize_syscall(os.path.join(data_path, "syscall_processed"))
    # count_unknown_files(os.path.join(data_path, "package_processed"))
    # visualize_deps(os.path.join(data_path, "package_processed"), os.path.join(data_path, "bazel_managed_deps.csv"))
    visualize_deps_by_deptype(os.path.join(data_path, "package_processed"))
    # visualize_external_managed_dep(os.path.join(data_path, "package_processed"),
    #                                os.path.join(data_path, "external_managed_packages_manually_examined.csv"))
    # visualize_prevalence(os.path.join(data_path, "package_processed"))
    # visualize_release_frequency(os.path.join(data_path, "package_processed"),
    #                             os.path.join(data_path, "package_release_dates"))
    # visualize_update_frequency(os.path.join(data_path, "package_processed"), os.path.join(data_path, "installed_tools"),
    #                            os.path.join(data_path, "package_release_dates"))


def search_dep_type(unmanaged_deps_df, row):
    query_res = unmanaged_deps_df.loc[
        (unmanaged_deps_df["project_name"] == row["project_name"]) & (
                unmanaged_deps_df["dep_name"] == row["dep_name"])]["dep_type"]

    if query_res.empty:
        return "row_to_be_removed"
    else:
        return query_res.iloc[0]

def count_unknown_files(external_deps_dir_path):
    data = pd.DataFrame({})
    for f in util.file.get_filepaths(external_deps_dir_path):
        df = pd.read_csv(f).drop(columns=["syscall", "type"]).dropna().drop_duplicates()

        data = pd.concat([data, df])

    def mapped_unknown_files(df, project_name, pkg_name, path):
        if pkg_name != "unknown":
            return pkg_name

        if "java-17-openjdk" in path:
            jdk_pkg_exists = len(df.loc[(df["project"] == project_name) & (df["pkg_name"] == "openjdk-17-jre-headless")]) != 0
            if jdk_pkg_exists:
                return "openjdk-17-jre-headless"

            jdk_pkg_exists = len(df.loc[(df["project"] == project_name) & (df["pkg_name"] == "openjdk-17-jre")]) != 0
            if jdk_pkg_exists:
                return "openjdk-17-jre"

        return "unknown"

    data["pkg_name"] = data.apply(lambda row: mapped_unknown_files(data, row["project"], row["pkg_name"], row["path"]), axis=1)

    total_number_unknown_files = len(data.loc[data["pkg_name"] == "unknown"])
    print(f"total number of unknown files: {total_number_unknown_files}")

    def cache_files(path):
        if re.search(r"cache", path):
            return True
        if re.search(r".cargo", path):
            return True
        if re.search(r"/usr/local/go/", path):
            return True

        return False

    cache_files_df = data.loc[(data["path"].apply(cache_files)) & (data["pkg_name"] == "unknown")]
    non_cache_files_df = data.loc[(~data["path"].apply(cache_files)) & (data["pkg_name"] == "unknown")]

    total_number_cache_files = len(cache_files_df)
    print(f"total number of cache files: {total_number_cache_files}")

    total_number_files = len(data)
    print(f"total number of files: {total_number_files}")


def visualize_external_managed_dep(external_deps_dir_path, external_managed_deps_dir_path):
    plt.figure(figsize=(8, 4))

    unmanaged_deps_df = read_external_packages(external_deps_dir_path)
    unmanaged_deps_df = unmanaged_deps_df[unmanaged_deps_df["category"] == "Unmanaged (Top)"]

    external_managed_df = pd.read_csv(external_managed_deps_dir_path)
    external_managed_df["category"] = "External Managed (Top)"
    external_managed_df.drop(columns=["managed_by", "version_specified"], inplace=True)

    unmanaged_deps_df = unmanaged_deps_df[unmanaged_deps_df["project_name"].isin(external_managed_df["project_name"])]

    external_managed_df["dep_type"] = external_managed_df.apply(lambda row: search_dep_type(unmanaged_deps_df, row),
                                                                axis=1)
    external_managed_df = external_managed_df[external_managed_df["dep_type"] != "row_to_be_removed"]

    df = pd.concat([unmanaged_deps_df, external_managed_df])
    df = df.astype({"category": "category", "dep_type": "category", "project_name": "category"})
    df = df.groupby(["category", "dep_type", "project_name"], observed=False).size().reset_index(name='counts')

    ax = sns.boxplot(x="counts", y="dep_type", hue="category", data=df, dodge=True, palette=["#50B848", "#D2B63C"])
    # ax.set(xlabel='Dependency Type', ylabel='Count')
    # ax.legend().set_title("Dependency Category")
    ax.set(ylabel="", xlabel="", yticklabels=[])
    plt.legend([], [], frameon=False)

    plt.tight_layout()
    savefig("./images/external_managed_deps")
    plt.show()

    print(
        f"the median of external managed top-level library: {df.loc[(df['dep_type'] == 'library') & (df['category'] == 'External Managed (Top)')]['counts'].median()}")
    print(
        f"the median of external managed top-level toolchain: {df.loc[(df['dep_type'] == 'toolchain') & (df['category'] == 'External Managed (Top)')]['counts'].median()}")


def visualize_deps_by_deptype(external_deps_dir_path):
    unmanaged_deps_df = read_external_packages(external_deps_dir_path)
    unmanaged_deps_df = unmanaged_deps_df.astype(
        {"category": "category", "dep_type": "category", "project_name": "category"})
    unmanaged_deps_df = unmanaged_deps_df.groupby(["category", "dep_type", "project_name"],
                                                  observed=False).size().reset_index(name='counts')

    ax = sns.boxplot(x="dep_type", y="counts", palette="Set2", hue="category", data=unmanaged_deps_df, dodge=True)
    ax.set(xlabel='Dependency Type', ylabel='Count')
    ax.legend().set_title("Dependency Category")

    plt.tight_layout()
    savefig("./images/external_deps_by_deptype")
    plt.show()

    print(f"the number of projects that have 0 top-level unmanaged library: "
          f"{len(unmanaged_deps_df.loc[(unmanaged_deps_df['dep_type'] == 'library') & (unmanaged_deps_df['category'] == 'Unmanaged (Top)') & (unmanaged_deps_df['counts'] == 0)]['project_name'].unique())}")
    print(f"the number of projects that have 0 top-level unmanaged toolchain: "
          f"{len(unmanaged_deps_df.loc[(unmanaged_deps_df['dep_type'] == 'toolchain') & (unmanaged_deps_df['category'] == 'Unmanaged (Top)') & (unmanaged_deps_df['counts'] == 0)]['project_name'].unique())}")

    top_level_unmanaged_library = unmanaged_deps_df.loc[
        (unmanaged_deps_df['dep_type'] == 'library') & (unmanaged_deps_df['category'] == 'Unmanaged (Top)')]['counts']
    transitive_unmanaged_library = unmanaged_deps_df.loc[
        (unmanaged_deps_df['dep_type'] == 'library') & (unmanaged_deps_df['category'] == 'Unmanaged (Transitive)')][
        'counts']

    top_level_unmanaged_toolchain = unmanaged_deps_df.loc[
        (unmanaged_deps_df['dep_type'] == 'toolchain') & (unmanaged_deps_df['category'] == 'Unmanaged (Top)')]['counts']
    transitive_unmanaged_toolchain = unmanaged_deps_df.loc[
        (unmanaged_deps_df['dep_type'] == 'toolchain') & (unmanaged_deps_df['category'] == 'Unmanaged (Transitive)')][
        'counts']

    print(f"total number of top level unmanaged library: {top_level_unmanaged_library.sum()}")
    print(f"total number of transitive unmanaged library: {transitive_unmanaged_library.sum()}")
    print(f"median top level unmanaged library: {top_level_unmanaged_library.median()}")
    print(f"median transitive unmanaged library: {transitive_unmanaged_library.median()}")
    print(f"total number of top level unmanaged toolchain: {top_level_unmanaged_toolchain.sum()}")
    print(f"total number of transitive unmanaged toolchain: {transitive_unmanaged_toolchain.sum()}")
    print(f"median top level unmanaged toolchain: {top_level_unmanaged_toolchain.median()}")
    print(f"median transitive unmanaged toolchain: {transitive_unmanaged_toolchain.median()}")

    p_value = scipy.stats.mannwhitneyu(top_level_unmanaged_library, top_level_unmanaged_toolchain)
    print(f"p-value: {p_value}")

    effect_size = cliffs_delta(top_level_unmanaged_library, top_level_unmanaged_toolchain)
    print(f"effect size: {effect_size}")


def visualize_deps(external_deps_dir_path, bazel_managed_deps_path):
    unmanaged_deps_df = read_external_packages(external_deps_dir_path)

    managed_deps_df = pd.read_csv(bazel_managed_deps_path).dropna().drop_duplicates()
    managed_deps_df["category"] = "Managed"
    df = pd.concat([unmanaged_deps_df, managed_deps_df])

    df = df.astype({"category": "category", "dep_type": "category", "project_name": "category"})
    df = df.groupby(["category", "dep_type", "project_name"], observed=False).size().reset_index(name='counts')

    unmanaged_all_count_df = df.loc[df["category"] != "Managed"].copy()
    unmanaged_all_count_df["category"] = "Unmanaged (All)"
    unmanaged_all_count_df = unmanaged_all_count_df.groupby(["project_name", "dep_type", "category"], as_index=False,
                                                            observed=False).agg({"counts": "sum"})

    # unmanaged_and_managed_all_count_df = pd.concat([df[df["category"] == "Managed"], unmanaged_all_count_df])
    unmanaged_and_managed_all_count_df = pd.concat([df, unmanaged_all_count_df])
    unmanaged_and_managed_all_count_df["counts"] += 1

    ax = sns.boxplot(x="counts", y="dep_type", hue="category", data=unmanaged_and_managed_all_count_df,
                     dodge=True,
                     hue_order=["Unmanaged (Top)", "Unmanaged (Transitive)", "Unmanaged (All)", "Managed"],
                     palette=["#50B848", "#486DB5", "#944E9E", "#D25232", "#D2B63C"])
    ax.set_xscale("log")
    plt.setp(ax.patches, linewidth=0.5)

    ax.set(ylabel='Dependency Type', xlabel='Log10 (Number of Dependency + 1)')
    # ax.legend().set_title("Dependency Category")
    plt.legend([], [], frameon=False)
    ax.set(ylabel="", xlabel="", yticklabels=[])

    plt.tight_layout()
    savefig("./images/external_deps")
    plt.show()

    unmanaged_and_managed_all_count_df["counts"] -= 1

    unmanaged_library = unmanaged_and_managed_all_count_df.loc[
        (unmanaged_and_managed_all_count_df['category'] == 'Unmanaged (All)') & (
                unmanaged_and_managed_all_count_df['dep_type'] == 'library')][
        'counts']
    managed_library = unmanaged_and_managed_all_count_df.loc[
        (unmanaged_and_managed_all_count_df['category'] == 'Managed') & (
                unmanaged_and_managed_all_count_df['dep_type'] == 'library')][
        'counts']

    print(f"total number of unmanaged library: {unmanaged_library.sum()}")
    print(f"total number of managed library: {managed_library.sum()}")
    print(f"median unmanaged library: {unmanaged_library.median()}")
    print(f"median managed library: {managed_library.median()}")

    p_value = scipy.stats.mannwhitneyu(unmanaged_library, managed_library)
    print(f"p-value: {p_value}")

    effect_size = cliffs_delta(unmanaged_library, managed_library)
    print(f"effect size: {effect_size}")

    unmanaged_toolchain = unmanaged_and_managed_all_count_df.loc[
        (unmanaged_and_managed_all_count_df['category'] == 'Unmanaged (All)') & (
                unmanaged_and_managed_all_count_df['dep_type'] == 'toolchain')][
        'counts']
    managed_toolchain = unmanaged_and_managed_all_count_df.loc[
        (unmanaged_and_managed_all_count_df['category'] == 'Managed') & (
                unmanaged_and_managed_all_count_df['dep_type'] == 'toolchain')][
        'counts']

    print(f"total number of unmanaged toolchain: {unmanaged_toolchain.sum()}")
    print(f"total number of managed toolchain: {managed_toolchain.sum()}")
    print(f"median unmanaged toolchain: {unmanaged_toolchain.median()}")
    print(f"median managed toolchain: {managed_toolchain.median()}")

    p_value = scipy.stats.mannwhitneyu(unmanaged_toolchain, managed_toolchain)
    print(f"p-value: {p_value}")

    effect_size = cliffs_delta(unmanaged_toolchain, managed_toolchain)
    print(f"effect size: {effect_size}")


debian_priorities = {
    "required": ["adduser", "apt", "base-files", "base-passwd", "bash", "bsdutils", "cdebconf", "coreutils", "dash",
                 "debconf", "debian-archive-keyring", "debianutils", "diffutils", "dpkg", "e2fsprogs", "findutils",
                 "gawk", "gcc-10-base", "gcc-9-base", "gpgv", "gpgv1", "gpgv2", "grep", "gzip", "hostname",
                 "init-system-helpers", "install-info", "libacl1", "libapt-pkg6.0", "libattr1", "libaudit-common",
                 "libaudit1", "libblkid1", "libbz2-1.0", "libc-bin", "libc6", "libcap-ng0", "libcap2", "libcom-err2",
                 "libcrypt1", "libdb5.3", "libdebconfclient0", "libdebian-installer4", "libelogind0", "libext2fs2",
                 "libffi7", "libgcc-s1", "libgcrypt20", "libgmp10", "libgnutls30", "libgpg-error0", "libgssapi-krb5-2",
                 "libhogweed6", "libidn2-0", "libk5crypto3", "libkeyutils1", "libkrb5-3", "libkrb5support0", "liblz4-1",
                 "liblzma5", "libmount1", "libmpfr6", "libnettle8", "libnewt0.52", "libnsl2", "libp11-kit0",
                 "libpam-modules", "libpam-modules-bin", "libpam-runtime", "libpam0g", "libpcre2-8-0", "libpcre3",
                 "libreadline8", "libseccomp2", "libselinux1", "libsemanage-common", "libsemanage1", "libsepol1",
                 "libsigsegv2", "libslang2", "libsmartcols1", "libss2", "libssl1.1", "libstdc++6", "libsystemd0",
                 "libtasn1-6", "libtextwrap1", "libtinfo6", "libtirpc-common", "libtirpc3", "libudev1", "libunistring2",
                 "libuuid1", "libxxhash0", "libzstd1", "login", "logsave", "lsb-base", "mawk", "mount", "ncurses-base",
                 "ncurses-bin", "original-awk", "passwd", "perl-base", "readline-common", "sed", "sysvinit-utils",
                 "tar", "tzdata", "util-linux", "zlib1g"],
    "important": ["anacron", "apt-utils", "bcron", "bsdextrautils", "bsdmainutils", "cpio", "cron", "debconf-i18n",
                  "dmidecode", "dmsetup", "fdisk", "groff-base", "ifupdown", "init", "initscripts", "insserv",
                  "iproute2", "iputils-ping", "isc-dhcp-client", "isc-dhcp-common", "kmod", "less", "libapparmor1",
                  "libargon2-1", "libbg2", "libbpf0", "libbsd0", "libcap2-bin", "libcryptsetup12", "libdevmapper1.02.1",
                  "libdns-export1110", "libedit2", "libeinfo1", "libelf1", "libestr0", "libexpat1", "libfastjson4",
                  "libfdisk1", "libgdbm-compat4", "libgdbm6", "libip4tc2", "libisc-export1105", "libjansson4",
                  "libjson-c5", "libkmod2", "liblocale-gettext-perl", "liblognorm5", "libmd0", "libmnl0", "libmpdec3",
                  "libncurses6", "libncursesw6", "libnftables1", "libnftnl11", "libperl5.32", "libpipeline1",
                  "libpopt0", "libprocps8", "libpython3-stdlib", "libpython3.9-minimal", "libpython3.9-stdlib",
                  "librc1", "libsqlite3-0", "libtext-charwidth-perl", "libtext-iconv-perl", "libtext-wrapi18n-perl",
                  "libuchardet0", "libxtables12", "logrotate", "mailcap", "man-db", "media-types", "mime-support",
                  "nano", "ncal", "netbase", "nftables", "openrc", "perl", "perl-modules-5.32", "procps", "python3",
                  "python3-minimal", "python3.9", "python3.9-minimal", "rsyslog", "runit-helper", "sensible-utils",
                  "startpar", "systemd", "systemd-cron", "systemd-sysv", "sysuser-helper", "sysv-rc", "sysvinit-core",
                  "tasksel", "tasksel-data", "ucspi-unix", "udev", "vim-common", "vim-tiny", "whiptail", "xxd"],
    "standard": ["apt-listchanges", "bash-completion", "bind9-dnsutils", "bind9-host", "bind9-libs", "bzip2",
                 "ca-certificates", "dbus", "debian-faq", "distro-info-data", "doc-debian", "file", "gettext-base",
                 "krb5-locales", "libbrotli1", "libc-l10n", "libcbor0", "libcurl3-gnutls", "libdbus-1-3", "libfido2-1",
                 "libfstrm0", "libicu67", "libldap-2.4-2", "liblmdb0", "liblockfile-bin", "libmagic-mgc", "libmagic1",
                 "libmaxminddb0", "libnghttp2-14", "libnss-systemd", "libpam-systemd", "libpci3", "libprotobuf-c1",
                 "libpsl5", "librtmp1", "libsasl2-2", "libsasl2-modules-db", "libssh2-1", "libuv1", "libxml2",
                 "locales", "lsof", "manpages", "ncurses-term", "netcat-traditional", "openssh-client", "openssl",
                 "pci.ids", "pciutils", "python-apt-common", "python3-apt", "python3-certifi", "python3-chardet",
                 "python3-debconf", "python3-debian", "python3-debianbts", "python3-httplib2", "python3-idna",
                 "python3-pkg-resources", "python3-pycurl", "python3-pysimplesoap", "python3-reportbug",
                 "python3-requests", "python3-six", "python3-urllib3", "reportbug", "systemd-timesyncd", "telnet",
                 "traceroute", "ucf", "wamerican", "wget", "xz-utils"],
}


def change_width(ax, new_value):
    for patch in ax.patches:
        current_width = patch.get_width()
        diff = current_width - new_value

        # we change the bar width
        patch.set_width(new_value)

        # we recenter the bar
        patch.set_x(patch.get_x() + diff * .5)


def visualize_prevalence(external_deps_dir_path: str):
    df = read_external_packages(external_deps_dir_path)

    debian_package_priority = {}
    for priority, packages in debian_priorities.items():
        for package in packages:
            debian_package_priority[package] = priority

    df["debian_priority"] = df["dep_name"].map(
        lambda row: "Default Installed" if row in debian_package_priority else "Optional")

    # for project_name in df["project_name"].unique():
    #     for category in df["category"].unique():
    #         print(f"project ({category}): {project_name}")
    #         toolchains = df.loc[
    #             (df['project_name'] == project_name) & (df['dep_type'] == 'toolchain') & (df['category'] == category)]
    #         libraries = df.loc[
    #             (df['project_name'] == project_name) & (df['dep_type'] == 'library') & (df['category'] == category)]
    #
    #         print(
    #             f"{category} required toolchains: {toolchains.loc[toolchains['debian_priority'] == 'required']['dep_name'].unique()}")
    #         print(
    #             f"{category} required libraries: {libraries.loc[libraries['debian_priority'] == 'required']['dep_name'].unique()}")
    #
    #         print(
    #             f"{category} important toolchains: {toolchains.loc[toolchains['debian_priority'] == 'important']['dep_name'].unique()}")
    #         print(
    #             f"{category} important libraries: {libraries.loc[libraries['debian_priority'] == 'important']['dep_name'].unique()}")
    #
    #         print(
    #             f"{category} standard toolchains: {toolchains.loc[toolchains['debian_priority'] == 'standard']['dep_name'].unique()}")
    #         print(
    #             f"{category} standard libraries: {libraries.loc[libraries['debian_priority'] == 'standard']['dep_name'].unique()}")
    #
    #         print(
    #             f"{category} optional toolchains: {toolchains.loc[toolchains['debian_priority'] == 'optional']['dep_name'].unique()}")
    #         print(
    #             f"{category} optional libraries: {libraries.loc[libraries['debian_priority'] == 'optional']['dep_name'].unique()}")
    #
    #         print("----------------------------------------")

    df = df.astype(
        {"dep_type": "category", "category": "category", "project_name": "category", "debian_priority": "category"})
    df = df.groupby(["project_name", "dep_type", "category", "debian_priority"], observed=False).size().reset_index(
        name='counts')

    all_dep_type = df.copy().groupby(["project_name", "debian_priority"], observed=False).agg(
        {"counts": "sum"}).reset_index()
    all_dep_type["dep_type"] = "All"
    all_dep_type["category"] = "All"

    # df = pd.concat([df, all_dep_type])

    default_installed = df[df['debian_priority'] == 'Default Installed']
    optional = df[df['debian_priority'] == 'Optional']

    plt.figure(figsize=(3, 4))

    ax = sns.boxplot(x="debian_priority", y="counts", data=all_dep_type, color="#50B848")
    ax.set(xlabel="", ylabel="", xticklabels=[])
    ax.set_ylim(0, 70)

    plt.tight_layout()
    savefig("./images/deps_prevalence_all")
    plt.show()

    plt.figure(figsize=(3, 4))
    ax = sns.boxplot(x="dep_type", y="counts", data=default_installed, palette=["#50B848", "#486DB5"], hue="category",
                     dodge=True)
    ax.set(xlabel="", ylabel="", xticklabels=[], yticklabels=[])
    ax.set_ylim(0, 70)
    plt.legend([], [], frameon=False)

    plt.tight_layout()
    savefig("./images/deps_prevalence_default_installed")
    plt.show()

    plt.figure(figsize=(3, 4))
    ax = sns.boxplot(x="dep_type", y="counts", data=optional, palette=["#50B848", "#486DB5"], hue="category",
                     dodge=True)
    ax.set(xlabel="", ylabel="", xticklabels=[], yticklabels=[])
    ax.set_ylim(0, 70)
    plt.legend([], [], frameon=False)

    plt.tight_layout()
    savefig("./images/deps_prevalence_optional")
    plt.show()

    # fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=True, sharex=True)
    #
    # ax = sns.boxplot(x="dep_type", y="counts", data=default_installed, palette="Set2", hue="category", dodge=True,
    #                     ax=axes[0])
    #
    # ax.set(xlabel="Dependency Type", ylabel="Number of Package")
    # ax.legend().set_title("Dependency Category")
    # ax.set_title("Default Installed")
    #
    #
    # ax = sns.boxplot(x="dep_type", y="counts", data=optional, palette="Set2", hue="category", dodge=True,
    #                     ax=axes[1])
    #
    # ax.set(xlabel="Dependency Type", ylabel="Number of Package")
    # ax.legend().set_title("Dependency Category")
    # ax.set_title("Optional")
    #
    plt.tight_layout()
    plt.show()

    #
    #
    #
    # df["dep_type"] = df["dep_type"].str.cat(df["category"], sep=" - ")
    #
    # df = df.drop(columns=["category"]).drop_duplicates()
    # df = df.astype({"dep_type": "category", "project_name": "category", "debian_priority": "category"})
    # df = df.groupby(["dep_type", "project_name", "debian_priority"], observed=False).size().reset_index(name='counts')
    #
    # all_dep_type = df.copy().groupby(["project_name", "debian_priority"], observed=False).agg(
    #     {"counts": "sum"}).reset_index()
    # all_dep_type["dep_type"] = "All"
    #
    # df = pd.concat([df, all_dep_type])
    #
    # ax = sns.boxplot(x="debian_priority", y="counts", data=df, palette="Set2", hue="dep_type",
    #                  hue_order=["All", "library - Unmanaged (Top)", "library - Unmanaged (Transitive)",
    #                             "toolchain - Unmanaged (Top)", "toolchain - Unmanaged (Transitive)"], dodge=True)
    # ax.set(xlabel="Package Priority", ylabel="Number of Package")
    # ax.legend().set_title("Dependency Type")
    #
    # plt.tight_layout()
    # savefig("./images/deps_priority")
    # plt.show()
    #
    # default_installed = df[df['debian_priority'] == 'Default Installed'].groupby('project_name')['counts'].sum()
    # optional = df[df['debian_priority'] == 'Optional'].groupby('project_name')['counts'].sum()
    #
    # print(f"median default installed: {default_installed.median()}")
    # print(f"median optional: {optional.median()}")
    #
    # p_value = scipy.stats.mannwhitneyu(default_installed, optional)
    # print(f"p-value: {p_value}")
    #
    # effect_size = cliffs_delta(default_installed, optional)
    # print(f"effect size: {effect_size}")
    #
    # default_installed_top_libraries = \
    #     df[(df['dep_type'] == 'library - Unmanaged (Top)') & (df['debian_priority'] == 'Default Installed')][
    #         'counts']
    # default_installed_transitive_libraries = \
    #     df[(df['dep_type'] == 'library - Unmanaged (Transitive)') & (df['debian_priority'] == 'Default Installed')][
    #         'counts']
    # default_installed_top_toolchains = \
    #     df[(df['dep_type'] == 'toolchain - Unmanaged (Top)') & (df['debian_priority'] == 'Default Installed')][
    #         'counts']
    # default_installed_transitive_toolchains = \
    #     df[(df['dep_type'] == 'toolchain - Unmanaged (Transitive)') & (df['debian_priority'] == 'Default Installed')][
    #         'counts']
    # optional_top_libraries = \
    #     df[(df['dep_type'] == 'library - Unmanaged (Top)') & (df['debian_priority'] == 'Optional')][
    #         'counts']
    # optional_transitive_libraries = \
    #     df[(df['dep_type'] == 'library - Unmanaged (Transitive)') & (df['debian_priority'] == 'Optional')][
    #         'counts']
    # optional_top_toolchains = \
    #     df[(df['dep_type'] == 'toolchain - Unmanaged (Top)') & (df['debian_priority'] == 'Optional')][
    #         'counts']
    # optional_transitive_toolchains = \
    #     df[(df['dep_type'] == 'toolchain - Unmanaged (Transitive)') & (df['debian_priority'] == 'Optional')][
    #         'counts']
    #
    # print(f"median default installed top libraries: {default_installed_top_libraries.median()}")
    # print(f"median default installed transitive libraries: {default_installed_transitive_libraries.median()}")
    # print(f"median default installed top toolchains: {default_installed_top_toolchains.median()}")
    # print(f"median default installed transitive toolchains: {default_installed_transitive_toolchains.median()}")
    # print(f"median optional top libraries: {optional_top_libraries.median()}")
    # print(f"median optional transitive libraries: {optional_transitive_libraries.median()}")
    # print(f"median optional top toolchains: {optional_top_toolchains.median()}")
    # print(f"median optional transitive toolchains: {optional_transitive_toolchains.median()}")
    #
    # p_value = scipy.stats.mannwhitneyu(default_installed_top_libraries, optional_top_libraries)
    # print(f"p-value: {p_value}")
    #
    # effect_size = cliffs_delta(default_installed_top_libraries, optional_top_libraries)
    # print(f"effect size: {effect_size}")
    #
    # p_value = scipy.stats.mannwhitneyu(default_installed_top_toolchains, optional_top_toolchains)
    # print(f"p-value: {p_value}")
    #
    # effect_size = cliffs_delta(default_installed_top_toolchains, optional_top_toolchains)
    # print(f"effect size: {effect_size}")


def visualize_release_frequency(external_deps_dir_path: str, package_release_dates_path: str):
    package_df = read_external_packages(external_deps_dir_path)
    debian_package_release_frequency = {}
    for f in util.file.get_filepaths(package_release_dates_path):
        package_name = Path(f).stem

        df = pd.read_csv(f)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df[(df["date"] < datetime.datetime(2023, 6, 10, tzinfo=datetime.timezone.utc)) &
                (df["date"] >= datetime.datetime(2017, 6, 17, tzinfo=datetime.timezone.utc))]

        df = df[df["repo"] != "experimental"]

        debian_package_release_frequency[package_name] = len(df)

    package_df["release_frequency"] = package_df["dep_name"].map(
        lambda row: debian_package_release_frequency[row] if row in debian_package_release_frequency else 0)

    package_df["median_release_frequency"] = package_df.apply(lambda row: package_df.loc[
        (package_df["category"] == row["category"]) & (package_df["project_name"] == row["project_name"]) & (
                package_df["dep_type"] == row["dep_type"])][
        "release_frequency"].median(), axis=1)

    package_df = package_df.drop(columns=["dep_name", "release_frequency"]).drop_duplicates()
    ax = sns.boxplot(x="dep_type", y="median_release_frequency", hue="category", data=package_df, palette="Set2",
                     dodge=True,
                     order=["library", "toolchain"])
    ax.set(xlabel="Category", ylabel="The Median Number of Release")

    sns.move_legend(ax, loc="upper left", title="", bbox_to_anchor=(1, 1), fontsize=12)

    plt.tight_layout()
    savefig("./images/release_frequency")
    plt.show()

    print(f"the release frequency: {package_df['median_release_frequency'].median()}")

    top_libraries_release_frequency = \
        package_df.loc[(package_df["dep_type"] == "library") & (package_df["category"] == "Unmanaged (Top)")][
            "median_release_frequency"]
    transitive_libraries_release_frequency = \
        package_df.loc[(package_df["dep_type"] == "library") & (package_df["category"] == "Unmanaged (Transitive)")][
            "median_release_frequency"]

    top_toolchains_release_frequency = \
        package_df.loc[(package_df["dep_type"] == "toolchain") & (package_df["category"] == "Unmanaged (Top)")][
            "median_release_frequency"]
    transitive_toolchains_release_frequency = \
        package_df.loc[(package_df["dep_type"] == "toolchain") & (package_df["category"] == "Unmanaged (Transitive)")][
            "median_release_frequency"]

    print(f"median top libraries release frequency: {top_libraries_release_frequency.median()}")
    print(f"median transitive libraries release frequency: {transitive_libraries_release_frequency.median()}")
    print(f"median top toolchains release frequency: {top_toolchains_release_frequency.median()}")
    print(f"median transitive toolchains release frequency: {transitive_toolchains_release_frequency.median()}")

    print(
        f"the size: {len(top_libraries_release_frequency)}, {len(transitive_libraries_release_frequency)}, {len(top_toolchains_release_frequency)}, {len(transitive_toolchains_release_frequency)}")

    p_value = scipy.stats.kruskal(top_libraries_release_frequency, transitive_libraries_release_frequency,
                                  top_toolchains_release_frequency, transitive_toolchains_release_frequency)
    print(f"p_value: {p_value}")

    posthoc = sp.posthoc_dunn(
        [top_libraries_release_frequency, transitive_libraries_release_frequency, top_toolchains_release_frequency,
         transitive_toolchains_release_frequency], p_adjust='holm')
    print(posthoc)

    p_value = scipy.stats.mannwhitneyu(top_libraries_release_frequency, transitive_libraries_release_frequency)
    print(f"p_value between top libraries and transitive libraries: {p_value}")

    effect_size = cliffs_delta(top_libraries_release_frequency, transitive_libraries_release_frequency)
    print(f"effect size: {effect_size}")

    p_value = scipy.stats.mannwhitneyu(top_toolchains_release_frequency, transitive_toolchains_release_frequency)
    print(f"p_value between top toolchains and transitive toolchains: {p_value}")

    effect_size = cliffs_delta(top_toolchains_release_frequency, transitive_toolchains_release_frequency)
    print(f"effect size: {effect_size}")


def visualize_update_frequency(external_deps_dir_path: str, package_update_frequency_path: str,
                               package_release_dates_path: str):
    # runners = {
    #     "gha": ["Ubuntu1804", "Ubuntu2004", "Ubuntu2204"],
    #     "circleci": ["Ubuntu1804", "Ubuntu2004", "Ubuntu2204"]
    # }
    runners = {
        "gha": ["Ubuntu2004", "Ubuntu2204"],
        "circleci": ["Ubuntu2004", "Ubuntu2204"]
    }

    source_package_map = {}
    for f in util.file.get_filepaths(package_release_dates_path):
        df = pd.read_csv(f)
        package_name = df["package"].iloc[0]
        source_package_name = df["source_package"].iloc[0]
        if source_package_name == "python3-defaults":
            source_package_name = "python3"
        source_package_map[package_name] = source_package_name

    for ci, runners in runners.items():
        for runner in runners:
            package_df = read_external_packages(external_deps_dir_path)
            package_df["source_package"] = package_df["dep_name"].map(
                lambda n: source_package_map[n] if n in source_package_map else n)

            cirunner_package_update_frequency = {}
            cirunner_package_update_frequency_path = os.path.join(package_update_frequency_path, ci, runner)
            for f in util.file.get_filepaths(cirunner_package_update_frequency_path):
                package_name = Path(f).stem

                df = pd.read_csv(f).drop_duplicates()
                df["date"] = pd.to_datetime(df["date"], utc=True)

                if package_name.startswith("openjdk_"):
                    package_name = package_name.replace("openjdk_", "openjdk-")

                cirunner_package_update_frequency[package_name] = len(df)

            package_df["ci_update_frequency"] = package_df.apply(
                lambda row: map_ci_runner_package_to_debian_package(row["source_package"], row["dep_name"],
                                                                    cirunner_package_update_frequency), axis=1) - 1

            package_df["ci_package_percentage"] = package_df.apply(lambda row: package_df.loc[
                                                                                   (package_df["project_name"] == row[
                                                                                       "project_name"]) & (package_df[
                                                                                                               "ci_update_frequency"] >= 0)].shape[
                                                                                   0] / package_df.loc[
                                                                                   package_df["project_name"] == row[
                                                                                       "project_name"]].shape[0],
                                                                   axis=1)

            ci_package_percentage_df = package_df[["project_name", "ci_package_percentage"]].drop_duplicates()
            package_df = package_df[package_df["ci_update_frequency"] >= 0]
            package_df["median_ci_update_frequency"] = package_df.apply(lambda row: package_df.loc[
                (package_df["category"] == row["category"]) & (package_df["project_name"] == row["project_name"]) & (
                        package_df["dep_type"] == row["dep_type"])][
                "ci_update_frequency"].max(), axis=1)

            package_df = package_df.drop(columns=["source_package", "dep_name", "ci_package_percentage",
                                                  "ci_update_frequency"]).drop_duplicates()

            # f, (ax_up_box, ax_low_box) = plt.subplots(2, gridspec_kw={"height_ratios": (.15, .85)})
            # sns.boxplot(x="ci_package_percentage", data=ci_package_percentage_df, ax=ax_up_box)
            # sns.boxplot(x="dep_type", y="median_ci_update_frequency", hue="category", data=package_df, palette="Set2",
            #             dodge=True, order=["library", "toolchain"],
            #             ax=ax_low_box, hue_order=["Unmanaged (Top)", "Unmanaged (Transitive)"])

            plt.figure(figsize=(3, 4))

            ax = sns.boxplot(x="dep_type", y="median_ci_update_frequency", hue="category", data=package_df,
                             palette=["#50B848", "#486DB5"], dodge=True, order=["library", "toolchain"],
                             hue_order=["Unmanaged (Top)", "Unmanaged (Transitive)"])
            ax.set_ylim(0, 25)
            ax.set(xlabel="", ylabel="", xticklabels=[], yticklabels=[])
            ax.legend([], [], frameon=False)

            plt.tight_layout()
            savefig(f"./images/{ci}_{runner}_update_frequency")
            plt.show()

            top_libraries_update_frequency = package_df.loc[
                (package_df["dep_type"] == "library") & (package_df["category"] == "Unmanaged (Top)")][
                "median_ci_update_frequency"]

            transitive_libraries_update_frequency = package_df.loc[
                (package_df["dep_type"] == "library") & (package_df["category"] == "Unmanaged (Transitive)")][
                "median_ci_update_frequency"]

            top_toolchains_update_frequency = package_df.loc[
                (package_df["dep_type"] == "toolchain") & (package_df["category"] == "Unmanaged (Top)")][
                "median_ci_update_frequency"]

            transitive_toolchains_update_frequency = package_df.loc[
                (package_df["dep_type"] == "toolchain") & (package_df["category"] == "Unmanaged (Transitive)")][
                "median_ci_update_frequency"]

            print(f"{ci}/{runner} median top libraries update frequency: {top_libraries_update_frequency.median()}")
            print(
                f"{ci}/{runner} median transitive libraries update frequency: {transitive_libraries_update_frequency.median()}")
            print(f"{ci}/{runner} median top toolchains update frequency: {top_toolchains_update_frequency.median()}")
            print(
                f"{ci}/{runner} median transitive toolchains update frequency: {transitive_toolchains_update_frequency.median()}")

            print(f"{ci}/{runner} highest top libraries update frequency: {top_libraries_update_frequency.max()}")
            print(f"{ci}/{runner} highest transitive libraries update frequency: {transitive_libraries_update_frequency.max()}")
            print(f"{ci}/{runner} highest top toolchains update frequency: {top_toolchains_update_frequency.max()}")
            print(f"{ci}/{runner} highest transitive toolchains update frequency: {transitive_toolchains_update_frequency.max()}")


    # fig, axes = plt.subplots(len(runners), 2, figsize=(12, 12), sharey=True, sharex=True)
    #
    # frequencies = {}
    # row, col = 0, 0
    # ci_runner_package_df = pd.DataFrame({})
    # ci_runner_package_update_df = pd.DataFrame({})
    # for ci, runners in runners.items():
    #     for runner in runners:
    #         package_df = read_external_packages(external_deps_dir_path)
    #         package_df["source_package"] = package_df["dep_name"].map(
    #             lambda n: source_package_map[n] if n in source_package_map else n)
    #
    #         cirunner_package_update_frequency = {}
    #         cirunner_package_update_frequency_path = os.path.join(package_update_frequency_path, ci, runner)
    #         for f in util.file.get_filepaths(cirunner_package_update_frequency_path):
    #             package_name = Path(f).stem
    #
    #             df = pd.read_csv(f).drop_duplicates()
    #             df["date"] = pd.to_datetime(df["date"], utc=True)
    #
    #             if package_name.startswith("openjdk_"):
    #                 package_name = package_name.replace("openjdk_", "openjdk-")
    #
    #             cirunner_package_update_frequency[package_name] = len(df)
    #
    #         package_df["ci_update_frequency"] = package_df["source_package"].map(
    #             lambda row: cirunner_package_update_frequency[
    #                 row] if row in cirunner_package_update_frequency else 0) - 1
    #
    #         package_df["is_package_in_ci"] = package_df["ci_update_frequency"].map(
    #             lambda freq: "existed in CI runner image" if freq >= 0 else "not existed in CI runner image")
    #         ci_runner_package_df_for_runner = package_df.copy().groupby(["project_name", "is_package_in_ci"],
    #                                                                     observed=False).size().reset_index(
    #             name='counts')
    #
    #         ci_runner_package_df_for_runner["runner"] = f"{ci}/{runner}"
    #         ci_runner_package_df = pd.concat([ci_runner_package_df, ci_runner_package_df_for_runner])
    #         package_df["runner"] = f"{ci}/{runner}"
    #
    #         ci_runner_package_update_df = pd.concat([ci_runner_package_update_df, package_df.copy()])
    #
    #         package_df = package_df.drop(columns=["project_name", "source_package"]).drop_duplicates()
    #         package_df = package_df[package_df["ci_update_frequency"] >= 0]
    #
    #         ax = sns.boxplot(x="dep_type", y="ci_update_frequency", hue="category", data=package_df, palette="Set2",
    #                          dodge=True, ax=axes[row][col], hue_order=["Unmanaged (Top)", "Unmanaged (Transitive)"])
    #         ax.set(xlabel="Category", ylabel="CI Update Frequency")
    #         ax.set_title(f"{ci}/{runner}")
    #         if col == 0:
    #             ax.set_ylim(0, 20)
    #         col += 1
    #
    #         unmanaged_top_libraries_update_frequency = \
    #             package_df.loc[(package_df["dep_type"] == "library") & (package_df["category"] == "Unmanaged (Top)")][
    #                 "ci_update_frequency"]
    #
    #         unmanaged_transitive_libraries_update_frequency = \
    #             package_df.loc[
    #                 (package_df["dep_type"] == "library") & (package_df["category"] == "Unmanaged (Transitive)")][
    #                 "ci_update_frequency"]
    #
    #         unmanaged_top_toolchains_update_frequency = \
    #             package_df.loc[(package_df["dep_type"] == "toolchain") & (package_df["category"] == "Unmanaged (Top)")][
    #                 "ci_update_frequency"]
    #
    #         unmanaged_transitive_toolchains_update_frequency = \
    #             package_df.loc[
    #                 (package_df["dep_type"] == "toolchain") & (package_df["category"] == "Unmanaged (Transitive)")][
    #                 "ci_update_frequency"]
    #
    #         print(
    #             f"{ci}/{runner} median top libraries update frequency: {unmanaged_top_libraries_update_frequency.median()}")
    #         print(
    #             f"{ci}/{runner} median transitive libraries update frequency: {unmanaged_transitive_libraries_update_frequency.median()}")
    #         print(
    #             f"{ci}/{runner} median top toolchains update frequency: {unmanaged_top_toolchains_update_frequency.median()}")
    #         print(
    #             f"{ci}/{runner} median transitive toolchains update frequency: {unmanaged_transitive_toolchains_update_frequency.median()}")
    #
    #         p_value = scipy.stats.kruskal(unmanaged_top_libraries_update_frequency,
    #                                       unmanaged_transitive_libraries_update_frequency,
    #                                       unmanaged_top_toolchains_update_frequency,
    #                                       unmanaged_transitive_toolchains_update_frequency)
    #         print(f"{ci}/{runner} p_value: {p_value}")
    #
    #         posthoc = sp.posthoc_dunn(
    #             [unmanaged_top_libraries_update_frequency, unmanaged_transitive_libraries_update_frequency,
    #              unmanaged_top_toolchains_update_frequency,
    #              unmanaged_transitive_toolchains_update_frequency], p_adjust='holm')
    #         print(posthoc)
    #
    #         if ci not in frequencies:
    #             frequencies[ci] = {}
    #         if runner not in frequencies[ci]:
    #             frequencies[ci][runner] = {}
    #
    #         frequencies[ci][runner]["top_libraries"] = unmanaged_top_libraries_update_frequency
    #         frequencies[ci][runner]["transitive_libraries"] = unmanaged_transitive_libraries_update_frequency
    #         frequencies[ci][runner]["top_toolchains"] = unmanaged_top_toolchains_update_frequency
    #         frequencies[ci][runner]["transitive_toolchains"] = unmanaged_transitive_toolchains_update_frequency
    #     row += 1
    #     col = 0
    #
    # plt.tight_layout()
    # savefig("./images/ci_update_frequency")
    # plt.show()
    #
    # gha_ubuntu2004_dep_freq = list(
    #     itertools.chain.from_iterable([l for _, l in frequencies["gha"]["Ubuntu2004"].items()]))
    # gha_ubuntu2204_dep_freq = list(
    #     itertools.chain.from_iterable([l for _, l in frequencies["gha"]["Ubuntu2204"].items()]))
    #
    # circleci_ubuntu2004_dep_freq = list(
    #     itertools.chain.from_iterable([l for _, l in frequencies["circleci"]["Ubuntu2004"].items()]))
    # circleci_ubuntu2204_dep_freq = list(
    #     itertools.chain.from_iterable([l for _, l in frequencies["circleci"]["Ubuntu2204"].items()]))
    #
    # p_value = scipy.stats.kruskal(gha_ubuntu2004_dep_freq, gha_ubuntu2204_dep_freq, circleci_ubuntu2004_dep_freq,
    #                               circleci_ubuntu2204_dep_freq)
    # print(f"p_value: {p_value}")
    #
    # posthoc = sp.posthoc_dunn(
    #     [gha_ubuntu2004_dep_freq, gha_ubuntu2204_dep_freq, circleci_ubuntu2004_dep_freq, circleci_ubuntu2204_dep_freq],
    #     p_adjust='holm')
    # print(posthoc)


def map_ci_runner_package_to_debian_package(source_package, binary_package, cirunner_package_update_frequency):
    for package in [binary_package, source_package]:
        if package in cirunner_package_update_frequency:
            return cirunner_package_update_frequency[package]

        # if the package ends with a version number, we remove it and try to match the pacakge again
        if m := re.match(r"^(.*)-\d+$", package):
            if m.group(1) in cirunner_package_update_frequency:
                return cirunner_package_update_frequency[m.group(1)]

        if f"{package}-dev" in cirunner_package_update_frequency:
            return cirunner_package_update_frequency[f"{package}-dev"]

        if package.startswith("lib") and package.lstrip("lib") in cirunner_package_update_frequency:
            return cirunner_package_update_frequency[package.lstrip("lib")]

    return 0


def visualize_syscall(syscall_data_path: str):
    # data = pd.DataFrame({})
    # for f in util.file.get_filepaths(syscall_data_path):
    #     df = pd.read_csv(f, usecols=['syscall', 'path', 'succeed'], dtype={'syscall': 'category'},
    #                      engine='c').drop_duplicates().dropna()
    #
    #     # we remove any read/write operations on /tmp and /dev/null
    #     df = df[~df["path"].str.startswith(("/tmp", "/dev/null", "anon_inode:[eventfd]", "/proc"))]
    #
    #     df = df[df["succeed"]]
    #     df["operation_type"] = df["syscall"].map(lambda row: strace_parser.util.syscall_operation_type(row))
    #     df["operation_scope"] = df["path"].map(lambda row: strace_parser.util.syscall_operation_scope(row))
    #
    #     df = df.groupby(["operation_type", "operation_scope"]).size().reset_index(name='counts')
    #     df["project"] = os.path.basename(f).replace(".csv", "")
    #     data = pd.concat([data, df])
    #
    # ax = sns.stripplot(x="operation_scope", y="counts", hue="operation_type", data=data, log_scale=True, dodge=True)
    # ax.set(xlabel='operation scope', ylabel='count')
    # ax.legend().set_title("operation type")
    # ax.set_title("syscall operation scope")
    #
    # plt.tight_layout()
    # plt.savefig("syscall_operation_scope.png")
    # plt.show()

    nums_hermetic_dep_files = 0
    nums_hermetic_other_files = 0

    # for f in util.file.get_filepaths(syscall_data_path):
    #     df = pd.read_csv(f, usecols=['path', 'succeed'],
    #                      engine='c').drop_duplicates().dropna()
    #     df = df[df["succeed"]]
    #
    #     dep_matcher = re.compile(r"/(root|home/zhengshenyu)/.cache/bazel/_bazel_root/[^/]+/external/([^/]+)/")
    #
    #
    #     df = df[df["path"].str.match("/(root|home/zhengshenyu)/.cache/bazel/.*")]
    #
    #     df["file_type"] = df["path"].map(lambda row: "hermetic dep" if dep_matcher.match(row) else "hermetic other")
    #     print(f"project: {os.path.basename(f)}: num hermetic dep files: {df[df['file_type'] == 'hermetic dep'].shape[0]}")



def reindex_df(df, weight_col):
    """expand the dataframe to prepare for resampling
    result is 1 row per count per sample"""
    df = df.reindex(df.index.repeat(df[weight_col]))
    df.reset_index(drop=True, inplace=True)
    return (df)


def savefig(path, fig_types=("pdf", "png", "svg")):
    for fig_type in fig_types:
        plt.savefig(f"{path}.{fig_type}")


if __name__ == "__main__":
    visualize("/Users/zhengshenyu/PycharmProjects/bazel_hermeticity/data")
