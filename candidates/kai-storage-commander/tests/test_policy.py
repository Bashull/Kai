import unittest

from kai_storage_commander.policy import PolicyError, build_plan


class PolicyTests(unittest.TestCase):
    def test_read_only_action_is_allowed_without_confirmation(self):
        plan = build_plan({"action": "list", "path": "~/storage/downloads"})
        self.assertEqual(plan.action, "list")
        self.assertFalse(plan.requires_confirmation)
        self.assertFalse(plan.payload["dry_run"])

    def test_mutating_action_defaults_to_dry_run(self):
        plan = build_plan({"action": "move", "path": "/sdcard/Download/a.txt", "dest": "/sdcard/Documents/a.txt"})
        self.assertTrue(plan.requires_confirmation)
        self.assertTrue(plan.payload["dry_run"])
        self.assertFalse(plan.payload["confirm"])

    def test_forbidden_shell_action_is_rejected(self):
        with self.assertRaises(PolicyError):
            build_plan({"action": "shell", "query": "rm -rf /"})

    def test_nul_byte_in_path_is_rejected(self):
        with self.assertRaises(PolicyError):
            build_plan({"action": "stat", "path": "/sdcard/Download/a\x00.txt"})

    def test_ambiguous_relative_path_is_rejected(self):
        with self.assertRaises(PolicyError):
            build_plan({"action": "stat", "path": "Download/a.txt"})

    def test_move_requires_destination(self):
        with self.assertRaises(PolicyError):
            build_plan({"action": "move", "path": "/sdcard/Download/a.txt"})


if __name__ == "__main__":
    unittest.main()
