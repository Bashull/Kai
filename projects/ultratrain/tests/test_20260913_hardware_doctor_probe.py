import unittest
from importlib import metadata
from types import SimpleNamespace

from projects.ultratrain.hardware_doctor import (
    build_runtime_descriptor,
    probe_hardware,
    probe_package_identities,
)
from projects.ultratrain.hardware_doctor_contract import CapabilityState


class HardwareDoctorProbeTests(unittest.TestCase):
    def test_package_probe_records_exact_versions_and_missing(self):
        versions = {"transformers": "5.16.0", "trl": "1.13.0"}

        def version_getter(name):
            if name not in versions:
                raise metadata.PackageNotFoundError(name)
            return versions[name]

        report = probe_package_identities(
            ("transformers", "trl", "unsloth"),
            version_getter=version_getter,
        )
        self.assertEqual([(x.name, x.version) for x in report.packages], [
            ("transformers", "5.16.0"),
            ("trl", "1.13.0"),
        ])
        self.assertEqual(report.missing, ("unsloth",))

    def test_nvidia_probe_parses_vram_without_promoting_capabilities(self):
        def runner(*args, **kwargs):
            return SimpleNamespace(
                returncode=0,
                stdout="NVIDIA RTX 4090, 24564\nNVIDIA RTX 3090, 24576\n",
                stderr="",
            )

        hardware = probe_hardware(
            runner=runner,
            ram_reader=lambda: 128 * 1024**3,
            platform_reader=lambda: "linux",
            cpu_reader=lambda: "fixture-cpu",
        )
        self.assertEqual(hardware.ram_bytes, 128 * 1024**3)
        self.assertEqual(len(hardware.gpus), 2)
        self.assertEqual(hardware.gpus[0].name, "NVIDIA RTX 4090")
        self.assertEqual(hardware.gpus[0].vram_bytes, 24564 * 1024**2)

    def test_missing_nvidia_smi_is_a_valid_cpu_only_snapshot(self):
        def runner(*args, **kwargs):
            raise FileNotFoundError("nvidia-smi")

        hardware = probe_hardware(
            runner=runner,
            ram_reader=lambda: 16 * 1024**3,
            platform_reader=lambda: "windows",
            cpu_reader=lambda: "fixture-cpu",
        )
        self.assertEqual(hardware.gpus, ())

    def test_runtime_builder_does_not_infer_capabilities_from_packages(self):
        versions = {"liger-kernel": "0.8.2"}

        def version_getter(name):
            return versions[name]

        runtime, report = build_runtime_descriptor(
            provider_id="canonical",
            package_names=("liger-kernel",),
            version_getter=version_getter,
        )
        self.assertFalse(report.missing)
        self.assertEqual(
            runtime.capability_state("liger.preference_frozen_weight_fastpath"),
            CapabilityState.UNKNOWN,
        )

    def test_unsloth_conflict_profile_requires_process_boundary(self):
        versions = {
            "unsloth": "2026.9.4",
            "trl": "0.23.1",
            "transformers": "5.5.0",
        }

        def version_getter(name):
            return versions[name]

        runtime, _ = build_runtime_descriptor(
            provider_id="unsloth-2026.9.4",
            package_names=("unsloth", "trl", "transformers"),
            isolation="process",
            conflicts=("canonical:trl>=1.13.0", "canonical:transformers>=5.16"),
            license_boundary="core:Apache-2.0;studio-cli:AGPL-3.0",
            version_getter=version_getter,
        )
        self.assertTrue(runtime.requires_isolation)
        self.assertEqual(runtime.isolation, "process")


if __name__ == "__main__":
    unittest.main()
