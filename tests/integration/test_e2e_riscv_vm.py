"""End-to-end test for RISC-V QEMU virtual machine.

This module provides integration test for building and profiling C++ projects
on a RISC-V architecture using QEMU virtualization. It automates the setup of
a RISC-V VM, installation of dependencies, and runs amphimixis to compile a test project inside the VM.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
import yaml

IP_ADDRESS = "127.0.0.1"
USERNAME = "root"
PASSWORD = "root"
WORKDIR = "/tmp/riscv_vm_test"
TESTING_PROJECT_URL = "https://github.com/leethomason/tinyxml2.git"


@pytest.mark.integration
def test_e2e_riscv_vm(riscv_vm_run_and_install_packages):
    """End-to-end test for building and profiling on a RISC-V QEMU VM."""

    repo_url = TESTING_PROJECT_URL
    wd_path = tempfile.mkdtemp(prefix="temp_dir")
    repo_path = Path(wd_path) / "repo"
    command = ["git", "clone", repo_url, repo_path]
    subprocess.run(command, check=True)
    orig_dir = Path.cwd()
    try:
        input_config = _create_input_yaml()
        config_path = Path(f"{wd_path}/input.yml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(input_config, f)

        os.chdir(wd_path)
        result = subprocess.run(
            ["python3", orig_dir / "amixis.py", str(repo_path)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
    finally:
        os.chdir(orig_dir)


@pytest.fixture
def riscv_vm_run_and_install_packages():
    """Fixture to start and configure RISC-V QEMU virtual machine."""

    Path(WORKDIR).mkdir(parents=True, exist_ok=True)
    zip_archive = Path(WORKDIR) / "debian.zip"
    repo_with_image = Path(WORKDIR) / "dqib_riscv64-virt"
    qcow2_file = repo_with_image / "image.qcow2"

    url = "https://gitlab.com/api/v4/projects/giomasce%2Fdqib/jobs/artifacts/master/download?job=convert_riscv64-virt"

    if not qcow2_file.exists():
        if not zip_archive.exists():
            subprocess.run(["wget", "-O", str(zip_archive), f"{url}"], check=True)
        subprocess.run(["unzip", str(zip_archive), "-d", str(WORKDIR)], check=True)

    kernel = repo_with_image / "kernel"
    initrd = repo_with_image / "initrd"
    qemu_cmd = [
        "qemu-system-riscv64",
        "-machine",
        "virt",
        "-cpu",
        "rv64",
        "-m",
        "4G",
        "-device",
        "virtio-blk-device,drive=hd",
        "-drive",
        f"file={str(qcow2_file)},if=none,id=hd",
        "-device",
        "virtio-net-device,netdev=net",
        "-netdev",
        "user,id=net,hostfwd=tcp:127.0.0.1:2222-:22",
        "-kernel",
        str(kernel),
        "-object",
        "rng-random,filename=/dev/urandom,id=rng",
        "-device",
        "virtio-rng-device,rng=rng",
        "-nographic",
        "-append",
        "root=LABEL=rootfs console=ttyS0",
        "-initrd",
        str(initrd),
    ]

    process = subprocess.Popen(qemu_cmd, text=True)
    time.sleep(120)

    subprocess.run(
        [
            "ssh-keygen",
            "-f",
            "~/.ssh/known_hosts",
            "-R",
            f"[{IP_ADDRESS}]:2222",
        ],
        capture_output=True,
        text=True,
    )

    vm_update_cmd = "apt-get update"
    vm_install_packages = "apt-get install -y cmake make g++ linux-perf"
    run_command(str(vm_update_cmd))
    time.sleep(60)
    run_command(str(vm_install_packages))
    time.sleep(120)

    yield process
    process.terminate()


def run_command(command: str) -> None:
    """Execute a command inside the RISC-V VM via SSH.
    Uses sshpass for password authentication to connect to the running VM.
    The VM must be accessible on localhost:2222 with root/root credentials."""

    subprocess.run(
        [
            "sshpass",
            "-p",
            PASSWORD,
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-p",
            "2222",
            f"{USERNAME}@{IP_ADDRESS}",
            command,
        ],
        capture_output=True,
        text=True,
    )


def _create_input_yaml() -> dict:
    return {
        "build_system": "CMake",
        "runner": "Make",
        "platforms": [
            {
                "id": 1,
                "address": IP_ADDRESS,
                "arch": "riscv",
                "username": USERNAME,
                "port": 2222,
                "password": PASSWORD,
            }
        ],
        "recipes": [
            {
                "id": 1,
                "config_flags": "",
                "compiler_flags": {"cxx_flags": "-O2"},
            }
        ],
        "builds": [
            {
                "build_machine": 1,
                "toolchain": {"cxx_compiler": "/usr/bin/g++"},
                "sysroot": "/",
                "run_machine": 1,
                "recipe_id": 1,
            }
        ],
    }
