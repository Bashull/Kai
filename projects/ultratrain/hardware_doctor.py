from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass, field
from importlib import metadata
from typing import Callable, Iterable, Sequence

from .hardware_doctor_contract import (
    CapabilityEvidence,
    GPUDevice,
    HardwareSnapshot,
    PackageIdentity,
    RuntimeProviderDescriptor,
)


VersionGetter = Callable[[str], str]
Runner = Callable[..., object]


@dataclass(frozen=True)
class PackageProbeReport:
    packages: tuple[PackageIdentity, ...] = field(default_factory=tuple)
    missing: tuple[str, ...] = field(default_factory=tuple)


def probe_package_identities(
    package_names: Iterable[str],
    *,
    version_getter: VersionGetter = metadata.version,
) -> PackageProbeReport:
    packages: list[PackageIdentity] = []
    missing: list[str] = []
    for raw_name in package_names:
        name = str(raw_name).strip()
        if not name:
            continue
        try:
            version = str(version_getter(name)).strip()
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        if not version:
            missing.append(name)
            continue
        packages.append(PackageIdentity(name=name, version=version, source="python-metadata"))
    return PackageProbeReport(tuple(packages), tuple(missing))


def _physical_ram_bytes() -> int:
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        return max(0, page_size * pages)
    except (AttributeError, OSError, ValueError):
        return 0


def _platform_name() -> str:
    return (platform.system() or platform.platform() or "unknown").lower()


def _cpu_name() -> str:
    value = platform.processor() or platform.machine() or "unknown"
    return value.strip() or "unknown"


def _probe_nvidia_gpus(runner: Runner = subprocess.run) -> tuple[GPUDevice, ...]:
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return ()
    if int(getattr(completed, "returncode", 1)) != 0:
        return ()

    devices: list[GPUDevice] = []
    for ordinal, raw_line in enumerate(str(getattr(completed, "stdout", "")).splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.rsplit(",", 1)]
        if len(parts) != 2:
            continue
        name, memory_mib = parts
        try:
            vram_bytes = int(memory_mib) * 1024**2
        except ValueError:
            continue
        devices.append(GPUDevice(ordinal=ordinal, name=name, vram_bytes=vram_bytes, backend="cuda"))
    return tuple(devices)


def probe_hardware(
    *,
    runner: Runner = subprocess.run,
    ram_reader: Callable[[], int] = _physical_ram_bytes,
    platform_reader: Callable[[], str] = _platform_name,
    cpu_reader: Callable[[], str] = _cpu_name,
) -> HardwareSnapshot:
    return HardwareSnapshot(
        platform=str(platform_reader()),
        ram_bytes=max(0, int(ram_reader())),
        cpu=str(cpu_reader()),
        gpus=_probe_nvidia_gpus(runner),
        source="hardware-doctor:stdlib+nvidia-smi",
    )


def build_runtime_descriptor(
    *,
    provider_id: str,
    package_names: Sequence[str],
    isolation: str = "shared",
    capabilities: Sequence[CapabilityEvidence] = (),
    conflicts: Sequence[str] = (),
    license_boundary: str | None = None,
    version_getter: VersionGetter = metadata.version,
) -> tuple[RuntimeProviderDescriptor, PackageProbeReport]:
    report = probe_package_identities(package_names, version_getter=version_getter)
    runtime = RuntimeProviderDescriptor(
        provider_id=provider_id,
        isolation=isolation,
        packages=report.packages,
        capabilities=tuple(capabilities),
        conflicts=tuple(conflicts),
        license_boundary=license_boundary,
    )
    return runtime, report
