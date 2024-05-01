from abc import abstractmethod
import datetime

from github import Github, Auth

GITHUB_TOKEN = "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"

class Tool:
    def __init__(self, name: str, version: str, date: datetime.datetime, runner: str):
        self.name = name
        self.version = version
        self.date = date
        self.runner = runner

    def __str__(self) -> str:
        return f"{self.name}: {self.version} at {self.date.isoformat()} ({self.runner})"


class InstalledToolAnalyzer:
    def __init__(self):
        self.g = Github(auth=Auth.Token(GITHUB_TOKEN))

    @abstractmethod
    def analyze(self) -> list[Tool]:
        pass

    def list_commits(self, org: str, repo: str, path: str) -> list[tuple[str, datetime.datetime, str]]:
        commits = self.g.get_repo(f"{org}/{repo}").get_commits(path=path, since=datetime.datetime(2021, 4, 1))
        return [(commit.sha, commit.commit.committer.date, path) for commit in commits]

    def get_file(self, org: str, repo: str, commit: str, path: str) -> str:
        return self.g.get_repo(f"{org}/{repo}").get_contents(path, commit).decoded_content.decode("utf-8")

