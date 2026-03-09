"""Helper functions for tests"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from testcontainers.compose import DockerCompose


@pytest.fixture
def clone_repo():
    """The fixture for cloning a repository from GitHub to a temporary directory.
    Comment out the lines after yield if you don't want the directory with the cloned repository
    to be deleted. Don't forget to delete it after debugging."""
    repo_paths = []

    def _clone_repo(repo_url):
        repo_path = tempfile.mkdtemp(prefix="temp_dir")
        command = ["git", "clone", "--depth", "1", repo_url, repo_path]
        subprocess.run(command, check=True)
        repo_paths.append(repo_path)
        return Path(repo_path)

    yield _clone_repo

    if not os.getenv("CI"):
        for path in repo_paths:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def create_working_space():
    """The fixture for creating a temporary working directory.
    Comment out lines after yield if you don't want the working directory to be deleted.
    Don't forget to delete it after debugging."""
    working_dirs = []

    def _create_temp_file():
        working_dir = tempfile.mkdtemp(prefix="test_workspace_")
        working_dirs.append(working_dir)
        return Path(working_dir)

    yield _create_temp_file

    if not os.getenv("CI"):
        for dir_ in working_dirs:
            if os.path.exists(dir_):
                shutil.rmtree(dir_, ignore_errors=True)


@pytest.fixture
def create_file():
    """Create temporary files with automatic cleanup."""
    files = []

    def create_file_(name_file: str, text_file: str, directory: Path):
        program_file_path = directory / name_file
        program_file_path.write_text(text_file, encoding="utf-8")

    yield create_file_

    for f in files:
        if f.exists():
            f.unlink()


@pytest.fixture
def _docker_compose():
    """Run Docker Compose for integration tests.
    Comment out the line 'compose.stop()' if you don't want the containers to be deleted.
    Don't forget to delete them after debugging."""
    compose = DockerCompose(
        context="tests/integration", compose_file_name="docker-compose.test.yml"
    )
    compose.start()

    yield compose

    if not os.getenv("CI"):
        compose.stop()
