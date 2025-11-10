"""Utilities for pulling external knowledge into the Kai workspace.

The :class:`Fetcher` centralises remote downloads so agents can
request GitHub projects, Hugging Face assets or arXiv papers without
re-implementing the networking logic.  The implementation favours the
standard library and graceful fallbacks so it continues to operate in
restricted execution environments.
"""
from __future__ import annotations

import contextlib
import fnmatch
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import requests

HF_API_BASE = "https://huggingface.co/api"


@dataclass
class FetchReport:
    """Summary information returned after a fetch operation."""

    destination: Path
    items: List[str]
    notes: Optional[str] = None


class Fetcher:
    """Download helper that knows how to reach common AI resources."""

    def __init__(self, session: Optional[requests.Session] = None, timeout: int = 60) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Generic helpers
    def _download_file(self, url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(url, stream=True, timeout=self.timeout) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        handle.write(chunk)

    # ------------------------------------------------------------------
    # GitHub
    def download_github_repo(
        self,
        repo_url: str,
        destination: Path | str,
        branch: str = "main",
        use_git: bool = True,
    ) -> FetchReport:
        """Download a GitHub repository.

        The method attempts a shallow ``git clone`` when Git is available.
        When Git is not present or the clone fails, the implementation
        falls back to downloading the branch archive.
        """

        destination_path = Path(destination).expanduser().resolve()
        if destination_path.exists() and any(destination_path.iterdir()):
            raise FileExistsError(f"Destination {destination_path} is not empty")

        destination_path.mkdir(parents=True, exist_ok=True)
        cloned = False
        notes: Optional[str] = None
        repo_name = repo_url.rstrip("/").split("/")[-1]

        if use_git and shutil.which("git"):
            try:
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth",
                        "1",
                        "--branch",
                        branch,
                        repo_url,
                        str(destination_path),
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                cloned = True
            except subprocess.CalledProcessError as exc:  # pragma: no cover - logging branch
                notes = f"git clone failed ({exc}). Falling back to archive download."
                shutil.rmtree(destination_path, ignore_errors=True)
                destination_path.mkdir(parents=True, exist_ok=True)

        if not cloned:
            archive_url = repo_url.rstrip("/") + f"/archive/refs/heads/{branch}.zip"
            with tempfile.TemporaryDirectory() as tmpdir:
                archive_path = Path(tmpdir) / "repo.zip"
                self._download_file(archive_url, archive_path)
                with zipfile.ZipFile(archive_path) as archive:
                    archive.extractall(tmpdir)
                    extracted_candidates = list(Path(tmpdir).glob(f"{repo_name}-*"))
                    if not extracted_candidates:
                        raise RuntimeError("Unable to locate extracted repository contents")
                    extracted_root = extracted_candidates[0]
                    for item in extracted_root.iterdir():
                        shutil.move(str(item), destination_path / item.name)
        return FetchReport(destination=destination_path, items=[repo_name], notes=notes)

    # ------------------------------------------------------------------
    # Hugging Face
    def download_huggingface_repo(
        self,
        repo_id: str,
        destination: Path | str,
        repo_type: str = "datasets",
        include: Optional[Iterable[str]] = None,
    ) -> FetchReport:
        """Download files from a Hugging Face repository.

        Parameters
        ----------
        repo_id:
            The organisation/name identifier.
        destination:
            Directory where the files should be stored.
        repo_type:
            Either ``"datasets"`` or ``"models"``.
        include:
            Optional iterable of shell-style patterns that restrict the
            files that are downloaded.
        """

        destination_path = Path(destination).expanduser().resolve()
        destination_path.mkdir(parents=True, exist_ok=True)

        endpoint = f"{HF_API_BASE}/{repo_type}/{repo_id}"
        response = self.session.get(endpoint, timeout=self.timeout)
        response.raise_for_status()
        metadata = response.json()
        siblings = metadata.get("siblings", [])
        patterns = list(include) if include else None

        downloaded: List[str] = []
        for entry in siblings:
            filename = entry.get("rfilename") or entry.get("filename")
            if not filename:
                continue
            if patterns and not any(fnmatch.fnmatch(filename, pattern) for pattern in patterns):
                continue

            file_url = f"https://huggingface.co/{repo_type}/{repo_id}/resolve/main/{filename}"
            target_path = destination_path / filename
            target_path.parent.mkdir(parents=True, exist_ok=True)
            self._download_file(file_url, target_path)
            downloaded.append(filename)

        note = None
        if not downloaded:
            note = "No files matched the requested filters; metadata was retrieved but nothing downloaded."
        return FetchReport(destination=destination_path, items=downloaded, notes=note)

    # ------------------------------------------------------------------
    # arXiv
    def download_arxiv_paper(
        self,
        arxiv_id: str,
        destination: Path | str | None = None,
    ) -> FetchReport:
        """Download a PDF from arXiv."""

        if not arxiv_id:
            raise ValueError("arxiv_id must be provided")

        safe_name = arxiv_id.replace("/", "_")
        destination_path = Path(destination or f"{safe_name}.pdf").expanduser().resolve()
        self._download_file(f"https://arxiv.org/pdf/{arxiv_id}.pdf", destination_path)
        return FetchReport(destination=destination_path.parent, items=[destination_path.name])

    # ------------------------------------------------------------------
    def fetch_all(
        self,
        github: Optional[List[tuple[str, str | Path]]] = None,
        huggingface: Optional[List[tuple[str, str | Path]]] = None,
        arxiv: Optional[List[tuple[str, Optional[str | Path]]]] = None,
    ) -> List[FetchReport]:
        """Convenience helper that batches multiple fetch operations."""

        reports: List[FetchReport] = []
        if github:
            for repo_url, destination in github:
                reports.append(self.download_github_repo(repo_url, destination))
        if huggingface:
            for repo_id, destination in huggingface:
                reports.append(self.download_huggingface_repo(repo_id, destination))
        if arxiv:
            for paper_id, destination in arxiv:
                reports.append(self.download_arxiv_paper(paper_id, destination))
        return reports

    # ------------------------------------------------------------------
    def close(self) -> None:
        """Close the underlying HTTP session."""

        with contextlib.suppress(Exception):
            self.session.close()


__all__ = ["Fetcher", "FetchReport"]
