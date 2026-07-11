from __future__ import annotations

import importlib
import sys
import unittest

from tests.helpers import ROOT


sys.path.insert(0, str(ROOT / "src"))


class P3CompilePrivacyHardeningTest(unittest.TestCase):
    def test_exact_and_adjacent_secret_keys_are_rejected_without_value_leak(self) -> None:
        inputs = importlib.import_module("paperops.compiler.inputs")
        cases = (
            {"extensions": {"api_key": "secret-api-value"}},
            {"extensions": {"access_token": "secret-access-value"}},
            {"extensions": {"clientSecret": "secret-client-value"}},
            {"extensions": {"raw_reviewer_text": "private-review-value"}},
            {"extensions": {"private_raw": "private-raw-value"}},
        )
        for value in cases:
            with self.subTest(value=tuple(value["extensions"])):
                with self.assertRaises(inputs.CompileInputError) as raised:
                    inputs._frozen_mapping(value, "model.yml")
                self.assertEqual(
                    raised.exception.finding.code,
                    "compile.input_privacy",
                )
                for secret in value["extensions"].values():
                    self.assertNotIn(secret, raised.exception.finding.message)

    def test_token_metrics_and_public_identifiers_are_allowed(self) -> None:
        inputs = importlib.import_module("paperops.compiler.inputs")
        value = {
            "extensions": {
                "token_count": 2048,
                "token_budget": 8192,
                "tokenizer_version": "software:tokenizer-v2",
                "public_source": "https://example.org/software/release",
                "public_doi": "doi:10.1234/example.software",
            }
        }

        frozen = inputs._frozen_mapping(value, "model.yml")

        self.assertEqual(
            dict(frozen["extensions"]),
            value["extensions"],
        )

    def test_credential_urls_and_private_raw_sentinels_are_rejected(self) -> None:
        inputs = importlib.import_module("paperops.compiler.inputs")
        values = (
            "sftp://alice:secret-sftp@example.org/private/data",
            "ssh://alice:secret-ssh@example.org/private/data",
            "raw-review: unredacted-review-value",
            "private raw: unredacted-private-value",
        )
        for secret in values:
            with self.subTest(kind=secret.split(":", 1)[0]):
                with self.assertRaises(inputs.CompileInputError) as raised:
                    inputs._frozen_mapping(
                        {"extensions": {"x-note": secret}},
                        "model.yml",
                    )
                self.assertEqual(
                    raised.exception.finding.code,
                    "compile.input_privacy",
                )
                self.assertNotIn(secret, raised.exception.finding.message)


if __name__ == "__main__":
    unittest.main()
