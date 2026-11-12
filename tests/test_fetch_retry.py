"""The download retry, and the record it leaves behind.

ISA demonstration row 4 asks for monitoring that includes *retries*, checking
that observability exists. `fetch_data.download` has always retried; until now it
did so silently, so a nightly job quietly needing three attempts every night --
which is a job about to start failing -- looked identical to one that succeeded
first time.

These tests pin both halves: that a transient failure is actually retried, and
that the attempt is written down where somebody can find it afterwards.

urlopen and sleep are both replaced, so nothing here touches the network or takes
the real 2s + 4s backoff.
"""

import io
import sys
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import fetch_data  # noqa: E402

PAYLOAD = b"english\thinglish\nhello\tnamaste yaar\n"


class _Resp(io.BytesIO):
    """Minimal stand-in for the urlopen context manager."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _ok():
    return _Resp(PAYLOAD)


def _boom():
    raise urllib.error.URLError("connection reset")


class RetryTest(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dest = Path(self.tmp.name) / "corpus.tsv"
        sleeps = []
        patcher = mock.patch.object(fetch_data.time, "sleep", sleeps.append)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.sleeps = sleeps

    def _run(self, behaviours):
        """behaviours: a list of callables, one per attempt."""
        it = iter(behaviours)

        def fake_urlopen(req, timeout=None):
            return next(it)()

        with mock.patch.object(fetch_data.urllib.request, "urlopen", fake_urlopen):
            return fetch_data.download("https://example.invalid/corpus.tsv", self.dest)

    def test_first_attempt_succeeds(self):
        size, attempts = self._run([_ok])
        self.assertEqual(size, len(PAYLOAD))
        self.assertEqual(len(attempts), 1)
        self.assertTrue(attempts[0]["ok"])
        self.assertEqual(self.sleeps, [], "no backoff should be slept on success")

    def test_two_failures_then_success_is_recovered_and_recorded(self):
        size, attempts = self._run([_boom, _boom, _ok])
        self.assertEqual(size, len(PAYLOAD))
        self.assertEqual(self.dest.read_bytes(), PAYLOAD)
        self.assertEqual([a["ok"] for a in attempts], [False, False, True])
        self.assertIn("URLError", attempts[0]["error"])
        self.assertEqual(self.sleeps, [2, 4], "backoff should be 2s then 4s")

    def test_exhausting_the_retries_raises_and_says_how_many(self):
        with self.assertRaises(fetch_data.FetchError) as cm:
            self._run([_boom, _boom, _boom])
        self.assertIn("3 attempts", str(cm.exception))

    def test_a_partial_download_is_never_left_behind(self):
        """The .part file is what stops a truncated file being hashed as good."""
        with self.assertRaises(fetch_data.FetchError):
            self._run([_boom, _boom, _boom])
        leftovers = list(Path(self.tmp.name).iterdir())
        self.assertEqual(leftovers, [], "no .part file should survive a failed fetch")


if __name__ == "__main__":
    unittest.main()
