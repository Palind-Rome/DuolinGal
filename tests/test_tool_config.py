from __future__ import annotations

import json
import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.core.tool_config import load_toolchain_config
from duolingal.core.tooling import resolve_tooling_status


class ToolConfigTests(unittest.TestCase):
    def test_loads_toolchain_config_and_marks_configured_tool_as_found(self) -> None:
        with temporary_workspace() as temp_dir:
            fake_tool = temp_dir / "KrkrExtract.exe"
            touch(fake_tool)

            config_path = temp_dir / "toolchain.local.json"
            config_path.write_text(
                json.dumps(
                    {
                        "krkrextract": {
                            "path": str(fake_tool),
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            config = load_toolchain_config(config_path)
            tools = {tool.key: tool for tool in resolve_tooling_status(config)}

            self.assertEqual(config.tools["krkrextract"].path, str(fake_tool))
            self.assertEqual(tools["krkrextract"].status.value, "found")
            self.assertEqual(tools["krkrextract"].configured_path, str(fake_tool))

    def test_missing_config_file_returns_empty_config(self) -> None:
        with temporary_workspace() as temp_dir:
            config = load_toolchain_config(temp_dir / "missing.json")
            self.assertEqual(config.tools, {})


if __name__ == "__main__":
    unittest.main()
