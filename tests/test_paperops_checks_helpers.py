from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT

sys.path.insert(0, str(ROOT / "template" / "scripts"))

from paperops_checks import (  # noqa: E402
    clean_value,
    field_values,
    load_mapping,
    parse_markdown_tables,
    scalar_value,
)


class PaperopsChecksHelpersTest(unittest.TestCase):
    def test_load_mapping_accepts_yaml_json_and_invalid_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaml_path = root / "state.yml"
            json_path = root / "state.json"
            invalid_path = root / "invalid.yml"
            missing_path = root / "missing.yml"
            yaml_path.write_text("sections:\n  results:\n    state: AUDITED\n", encoding="utf-8")
            json_path.write_text('{"sections": {"discussion": {"state": "ACCEPTED"}}}\n', encoding="utf-8")
            invalid_path.write_text("sections: [", encoding="utf-8")

            self.assertEqual("AUDITED", load_mapping(yaml_path)["sections"]["results"]["state"])
            self.assertEqual("ACCEPTED", load_mapping(json_path)["sections"]["discussion"]["state"])
            self.assertEqual({}, load_mapping(invalid_path))
            self.assertEqual({}, load_mapping(missing_path))

    def test_frontmatter_scalar_and_field_values_use_shared_cleaning(self) -> None:
        front = """\
id: FIG-0001
status: "draft"
supports_claims: [CLM-0001, 未記入, ""]
manuscript_blocks:
  - `results.core.01`
  - todo
"""

        self.assertEqual("draft", scalar_value(front, "status"))
        self.assertEqual(["CLM-0001"], field_values(front, "supports_claims"))
        self.assertEqual(["results.core.01"], field_values(front, "manuscript_blocks", strip_code=True))
        self.assertEqual("quoted", clean_value("`'quoted'`", strip_code=True))

    def test_parse_markdown_tables_pads_short_rows_and_filters_by_header(self) -> None:
        text = """\
| other | value |
| --- | --- |
| skip | me |

| block_id | reader_question | operation |
| --- | --- | --- |
| results.core.01 | What is shown? | keep |
| results.refs.01 | Why refs? |
"""

        tables = parse_markdown_tables(text, required_header="block_id")

        self.assertEqual(1, len(tables))
        self.assertEqual(["block_id", "reader_question", "operation"], tables[0].headers)
        self.assertEqual("keep", tables[0].rows[0]["operation"])
        self.assertEqual("", tables[0].rows[1]["operation"])


if __name__ == "__main__":
    unittest.main()
