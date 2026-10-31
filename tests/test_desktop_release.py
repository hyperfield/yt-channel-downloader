"""Release guards that must hold before packaging or uploading desktop builds."""

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import desktop_release
import package_macos


class DesktopReleaseTests(unittest.TestCase):
    def test_release_rejects_mismatched_tag(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            desktop_release.release_version("v99999.0.0")

    def test_release_accepts_its_own_tag(self):
        version = desktop_release.release_version()
        self.assertEqual(desktop_release.release_version("v" + version), version)

    def test_download_rejects_missing_digest_before_fetching_binary(self):
        release = {"assets": [{"name": "tool", "browser_download_url": "https://example.invalid/tool"}]}
        with tempfile.TemporaryDirectory() as temporary, patch(
            "desktop_release.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(release).encode()),
        ) as request:
            target = Path(temporary) / "tool"
            with self.assertRaisesRegex(ValueError, "No SHA-256"):
                desktop_release.github_download("example/tools", "tool", target)
            self.assertFalse(target.exists())
            request.assert_called_once()

    def test_download_rejects_checksum_mismatch_without_writing_tool(self):
        release = {"assets": [{
            "name": "tool", "browser_download_url": "https://example.invalid/tool", "digest": "sha256:" + "0" * 64,
        }]}
        with tempfile.TemporaryDirectory() as temporary, patch(
            "desktop_release.urllib.request.urlopen",
            side_effect=[io.BytesIO(json.dumps(release).encode()), io.BytesIO(b"untrusted executable")],
        ):
            target = Path(temporary) / "tool"
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                desktop_release.github_download("example/tools", "tool", target)
            self.assertFalse(target.exists())

    def test_no_mac_credentials_selects_unsigned_build(self):
        self.assertIsNone(package_macos.signing_credentials({}))

    def test_partial_mac_credentials_cannot_silently_produce_unsigned_build(self):
        for name in package_macos.SIGNING_SECRETS:
            with self.subTest(secret=name), self.assertRaisesRegex(ValueError, "Partial macOS"):
                package_macos.signing_credentials({name: "configured"})

    def test_complete_mac_credentials_selects_signing(self):
        credentials = dict.fromkeys(package_macos.SIGNING_SECRETS, "configured")
        self.assertEqual(package_macos.signing_credentials(credentials), credentials)

    def test_failed_signing_commands_redact_credentials(self):
        from subprocess import CompletedProcess
        with patch.dict("os.environ", {"APPLE_APP_SPECIFIC_PASSWORD": "private-test-password"}), patch(
            "package_macos.subprocess.run", return_value=CompletedProcess([], 1, "", "error: private-test-password"),
        ):
            with self.assertRaises(RuntimeError) as caught:
                package_macos.run(["notarytool"], "Notarization")
        self.assertNotIn("private-test-password", str(caught.exception))
        self.assertIn("***", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
