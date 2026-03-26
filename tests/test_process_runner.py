from __future__ import annotations

import sys
import unittest

from support import ensure_src_on_path

ensure_src_on_path()

from duolingal.core.process_runner import run_command
from duolingal.domain.models import CommandSpec


class ProcessRunnerTests(unittest.TestCase):
    def test_runs_command_and_captures_output(self) -> None:
        result = run_command(
            CommandSpec(
                executable=sys.executable,
                args=["-c", "print('runner-ok')"],
            )
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("runner-ok", result.stdout)
        self.assertGreaterEqual(result.duration_ms, 0)


if __name__ == "__main__":
    unittest.main()
