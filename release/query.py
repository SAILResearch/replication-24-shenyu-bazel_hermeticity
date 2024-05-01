import datetime
from email.utils import parsedate_to_datetime
import re
import urllib.request

from pyquery import PyQuery

package_main_page = "https://packages.debian.org/bullseye/"


class Release:
    def __init__(self, package: str, date: str, version: str, repo) -> None:
        self.package = package
        self.date = date
        self.version = version
        self.repo = repo

    def __str__(self) -> str:
        return f"{self.package}: {self.version} at {self.date} ({self.repo})"


def package_release_dates(package: str) -> list[Release]:
    url = f"{package_main_page}{package}"
    content = urllib.request.urlopen(url).read().decode("utf-8")

    query = PyQuery(content)
    change_log_url = query("div#pmoreinfo").find("a:contains('Debian Changelog')").attr("href")
    if change_log_url is None:
        print(f"Could not find changelog url for package {package}")
        return []
    print(f"changelog url for package {package}: {change_log_url}")

    change_log = urllib.request.urlopen(change_log_url).read().decode("utf-8")
    blocks = re.split(r"(?:^|\n)(\S+ \(.+\) .+; urgency=.*)", change_log)
    blocks = list(filter(None, blocks))

    releases = []
    for release_info, release_changes_and_date in zip(blocks[0::2], blocks[1::2]):
        if m := re.match(r"(.+) \((.+)\) (.+); urgency=.*", release_info):
            package = m.group(1)
            version = m.group(2)
            repo = m.group(3)
        else:
            raise ValueError(f"Could not parse the release info of package {package} from {release_info}")

        if m := re.search(r" -- .+ <.*> (.+)", release_changes_and_date):
            date = m.group(1)
            date = parsedate_to_datetime(date)
        else:
            raise ValueError(f"Could not parse the release date of package {package} from {release_changes_and_date}")

        # we only want releases after 17th June 2017
        if date < datetime.datetime(2017, 6, 17, tzinfo=date.tzinfo):
            break

        release = Release(package, date.isoformat(), version, repo)
        releases.append(release)

    return releases
