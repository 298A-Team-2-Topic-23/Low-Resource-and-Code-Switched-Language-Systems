"""The training-curve parser, pinned against mlx_lm's real output.

Why this test exists: the first version of `scripts/train_lora_mlx.py` matched
`Iter 10: Train loss 2.145`, the format of an older mlx_lm. mlx_lm 0.32 prints a
table instead. The regexes matched nothing, silently, and a 3,199-second
training run finished with an empty loss curve -- the one artefact Team Meeting 2
slide 6 asks for by name. Nothing failed; the record was simply blank.

So the parser is now tested against verbatim lines from that run's log,
including the ANSI colour codes mlx_lm emits and the `save` lines that sit
between reports.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from train_lora_mlx import (  # noqa: E402
    checkpoint_advice, diverged, overfitting, parse_line, recover_from_log)

# Verbatim from runs/20261110T220440Z, ANSI codes included.
REAL_LINES = [
    "  \x1b[1miter   train_loss     tok/s     tokens\x1b[0m",
    "  \x1b[38;5;244m 500\x1b[0m    \x1b[1;32m2.013 ▼\x1b[0m    \x1b[1m    6\x1b[0m    \x1b[38;5;244m 14.5k\x1b[0m",
    "  save  0000500_adapters.safetensors",
    "  \x1b[38;5;244m 510\x1b[0m    \x1b[1;33m2.383 ▲\x1b[0m    \x1b[1m    7\x1b[0m    \x1b[38;5;244m 14.8k\x1b[0m",
    "  \x1b[38;5;244m 550\x1b[0m    \x1b[1;35mval\x1b[0m \x1b[1m2.025\x1b[0m    \x1b[38;5;244m39.74s\x1b[0m",
    "  \x1b[38;5;244m 600\x1b[0m    \x1b[1;35mval\x1b[0m \x1b[1m  nan\x1b[0m    \x1b[38;5;244m35.79s\x1b[0m",
    "train ████ 100% ·   600/600",
]


class ParseLineTest(unittest.TestCase):

    def parse(self, lines):
        train, val = [], []
        for line in lines:
            parse_line(line, train, val)
        return train, val

    def test_real_lines_yield_the_expected_points(self):
        train, val = self.parse(REAL_LINES)
        self.assertEqual(train, [(500, 2.013), (510, 2.383)])
        self.assertEqual(val[0], (550, 2.025))
        self.assertEqual(val[1][0], 600)
        self.assertTrue(val[1][1] != val[1][1], "nan should parse as nan")

    def test_a_val_line_is_not_also_read_as_a_train_point(self):
        """Both start with an iteration number, so order of matching matters."""
        train, val = self.parse(
            ["  \x1b[38;5;244m 550\x1b[0m    \x1b[1;35mval\x1b[0m \x1b[1m2.025\x1b[0m    39.74s"])
        self.assertEqual(train, [])
        self.assertEqual(val, [(550, 2.025)])

    def test_save_lines_are_ignored(self):
        self.assertEqual(self.parse(["  save  0000500_adapters.safetensors"]), ([], []))

    def test_header_and_progress_bar_are_ignored(self):
        train, val = self.parse([REAL_LINES[0], REAL_LINES[-1]])
        self.assertEqual((train, val), ([], []))

    def test_nan_train_loss_is_captured_not_dropped(self):
        """The 1e-4 run reported nan. Dropping it would hide the divergence."""
        train, _ = self.parse(
            ["  \x1b[38;5;244m  10\x1b[0m    \x1b[1;32m  nan ▼\x1b[0m    \x1b[1m    6\x1b[0m    0.3k"])
        self.assertEqual(len(train), 1)
        self.assertEqual(train[0][0], 10)
        self.assertTrue(train[0][1] != train[0][1])


class RecoverFromLogTest(unittest.TestCase):

    def test_recovers_a_curve_from_a_saved_log(self):
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        path = Path(d.name) / "log.txt"
        path.write_text("\n".join(REAL_LINES), encoding="utf-8")
        train, val = recover_from_log(path)
        self.assertEqual(train, [(500, 2.013), (510, 2.383)])
        self.assertEqual(len(val), 2)


class VerdictTest(unittest.TestCase):
    """The seed-42 run's actual validation curve."""

    CURVE = [(450, 2.003), (500, 2.111), (550, 2.025), (600, 2.378)]

    def test_strict_divergence_does_not_fire_on_this_curve(self):
        """2.111 -> 2.025 breaks the monotonic rise, and that is intended: the
        strict test must not call ordinary noise divergence."""
        self.assertFalse(diverged(self.CURVE))

    def test_overfitting_does_fire(self):
        """18.7% worse than the best, 150 iterations after it. Reporting only
        'not diverged' here would be true and misleading."""
        self.assertTrue(overfitting(self.CURVE))

    def test_overfitting_is_quiet_on_a_still_improving_run(self):
        self.assertFalse(overfitting([(50, 3.0), (100, 2.5), (150, 2.0)]))

    def test_overfitting_needs_two_points(self):
        self.assertFalse(overfitting([(50, 3.0)]))

    def test_advice_names_a_real_saved_checkpoint(self):
        advice = checkpoint_advice(self.CURVE, 100)
        self.assertEqual(advice["best_val_iter"], 450)
        self.assertEqual(advice["prefer_saved_checkpoint"], 400,
                         "checkpoints exist at multiples of save_every, not only "
                         "at iterations carrying a validation report")

    def test_no_advice_when_the_last_point_is_the_best(self):
        self.assertIsNone(checkpoint_advice([(50, 3.0), (100, 2.0)], 100))


if __name__ == "__main__":
    unittest.main()
