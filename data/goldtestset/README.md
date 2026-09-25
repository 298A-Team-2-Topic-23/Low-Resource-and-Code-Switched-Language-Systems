# Team-authored gold set

`gold_set.csv` is the canonical three-column data contract for issue 298-21:

- `english_source`: the source sentence;
- `devanagari_hindi`: an independent monolingual Hindi reference;
- `romanized_hinglish`: a natural Latin-script Hinglish reference.

The `needs_review` and `notes` fields support reconciliation and are removed from the released evaluation view only after every flagged item has a recorded decision. Keep one stable `item_id` per source and never sort the file independently of its aligned references.

The committed file currently contains the header only. The repository checkout does not include an approved 800-item English inventory, and writing 800 references without that inventory would create untraceable data. Populate this file only after the 50-item pilot has been independently scored and reconciled under `annotation_guidelines.md`. If the team approves the throughput fallback, freeze a complete 500-item file and record the decision in the project-management plan.

Validate the pre-inventory template with:

```text
python data/goldtestset/validate_gold_set.py data/goldtestset/gold_set.csv --allow-empty
```

Validate a completed release with `--expected-count 800` (or `500` if the throughput fallback is approved). The validator rejects duplicate IDs or sources, missing references, invalid review flags, and flagged rows without reconciliation notes.