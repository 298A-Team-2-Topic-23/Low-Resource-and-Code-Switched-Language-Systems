"""The spelling-variant lexicon, shared by the generator, the tagger and EDA.

Reads analysis/spelling_variants.tsv -- the same file tokenizer_fertility.py
(298-13) measures spelling_variant_burden from -- so the variance the pipeline
reports and the variance the fertility analysis reports are about the same words.
"""

from collections import OrderedDict
from pathlib import Path

from lrcs import REPO_ROOT

DEFAULT_LEXICON = REPO_ROOT / "analysis" / "spelling_variants.tsv"


def load_variant_groups(path=DEFAULT_LEXICON):
    """label -> list of surface forms (label first). Missing file -> empty."""
    groups = OrderedDict()
    path = Path(path)
    if not path.exists():
        return groups
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = [f.strip().lower() for f in line.split("\t") if f.strip()]
        if len(fields) < 3:
            continue
        label, forms = fields[0], fields[1:]
        ordered = [label] + [f for f in forms if f != label]
        groups[label] = list(OrderedDict.fromkeys(ordered))
    return groups


def form_index(groups):
    """surface form -> group label. First group to claim a form wins."""
    index = {}
    for label, forms in groups.items():
        for form in forms:
            index.setdefault(form, label)
    return index
