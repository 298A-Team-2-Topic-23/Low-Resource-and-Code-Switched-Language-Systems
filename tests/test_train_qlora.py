"""CPU-side tests for the QLoRA trainer (298-54).

The training loop needs a GPU and is unverified until 298-51 confirms the allocation.
Everything that runs on CPU is tested here, and the label masking is the part worth
testing hardest: computing loss over the prompt as well as the completion teaches the
model to echo the instruction back, and nothing about the output makes that visible --
the loss curve looks fine and the chrF++ is quietly lower.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "models"))

import train_qlora as tq  # noqa: E402


class FakeTokenizer:
    """Stands in for a real tokenizer: one token per character, so the arithmetic in the
    tests can be done by hand."""

    eos_token_id = 99

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "P" * 10          # a 10-token prompt, whatever the message

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": [ord(c) for c in text]}


class ReadPairsTest(unittest.TestCase):

    def _write(self, text):
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "train.tsv"
        p.write_text(text, encoding="utf-8")
        return p

    def test_reads_two_columns_and_ignores_extras(self):
        p = self._write("hello\tnamaste\textra\nbye\talvida\n")
        self.assertEqual(tq.read_pairs(p), [("hello", "namaste"), ("bye", "alvida")])

    def test_drops_a_header_row_by_name(self):
        p = self._write("english\thinglish\nhello\tnamaste\n")
        self.assertEqual(tq.read_pairs(p), [("hello", "namaste")])

    def test_skips_rows_missing_a_side(self):
        p = self._write("hello\tnamaste\n\tonly_target\nonly_source\t\nbye\talvida\n")
        self.assertEqual(tq.read_pairs(p), [("hello", "namaste"), ("bye", "alvida")])

    def test_limit_applies(self):
        p = self._write("a\t1\nb\t2\nc\t3\n")
        self.assertEqual(len(tq.read_pairs(p, limit=2)), 2)

    def test_empty_file_exits_rather_than_training_on_nothing(self):
        p = self._write("\n\n")
        with self.assertRaises(SystemExit):
            tq.read_pairs(p)


class LabelMaskingTest(unittest.TestCase):

    def setUp(self):
        self.tok = FakeTokenizer()

    def test_prompt_tokens_are_masked_and_completion_is_not(self):
        ex = tq.build_example(self.tok, "irrelevant", "abc", max_len=512)
        # 10 prompt tokens, then "abc" plus the eos token
        self.assertEqual(len(ex["input_ids"]), 14)
        self.assertEqual(ex["labels"][:10], [-100] * 10)
        self.assertEqual(ex["labels"][10:], [ord("a"), ord("b"), ord("c"), 99])

    def test_labels_and_inputs_stay_the_same_length(self):
        ex = tq.build_example(self.tok, "x", "hello there", max_len=512)
        self.assertEqual(len(ex["input_ids"]), len(ex["labels"]))

    def test_eos_is_appended_so_generation_can_stop(self):
        ex = tq.build_example(self.tok, "x", "hi", max_len=512)
        self.assertEqual(ex["input_ids"][-1], FakeTokenizer.eos_token_id)

    def test_truncation_keeps_the_completion_not_the_prompt(self):
        """Truncating from the right would drop the only tokens carrying loss."""
        ex = tq.build_example(self.tok, "x", "abcde", max_len=6)
        self.assertEqual(len(ex["input_ids"]), 6)
        unmasked = [l for l in ex["labels"] if l != -100]
        self.assertTrue(unmasked, "truncation left nothing to compute loss on")
        self.assertEqual(ex["input_ids"][-1], FakeTokenizer.eos_token_id)


class CollatorTest(unittest.TestCase):

    def test_pads_inputs_and_keeps_label_padding_masked(self):
        try:
            import torch  # noqa: F401
        except ImportError:
            self.skipTest("torch not installed")
        collate = tq.Collator(pad_id=0)
        batch = collate([
            {"input_ids": [1, 2, 3], "labels": [-100, 2, 3]},
            {"input_ids": [4, 5], "labels": [-100, 5]},
        ])
        self.assertEqual(batch["input_ids"].shape, (2, 3))
        # the padded position must stay masked, or the model learns to emit padding
        self.assertEqual(int(batch["labels"][1][-1]), -100)
        self.assertEqual(int(batch["attention_mask"][1][-1]), 0)


class RecipeTest(unittest.TestCase):

    def test_adapter_targets_every_linear_projection(self):
        """Attention-only adapters underperform, and the arm exists to be compared with
        M3 under a held-constant recipe."""
        self.assertEqual(
            set(tq.TARGET_MODULES),
            {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"},
        )

    def test_system_prompt_matches_the_generation_script(self):
        """Training and inference must frame the task identically."""
        sys.path.insert(0, str(REPO_ROOT / "models"))
        import generate_zeroshot as gz
        self.assertEqual(tq.SYSTEM_PROMPT, gz.SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
