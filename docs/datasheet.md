# Datasheet — data sources for this project

Owner: Yash. Covers the four sources scoped to the data/splits issue:
HinGE, the IIT Bombay English–Hindi Parallel Corpus, Samanantar, and
Dakshina. Written before ingestion (CLAUDE.md section 4/9: licence text
for every source is recorded in the datasheet before ingestion).

Out of scope here: the MixMT 2022 Subtask-1 test set (baseline
reproduction, owned separately) and the team-authored 800-item eval set
(released by us, not sourced externally). Both still need an entry in
this datasheet from whoever owns them.

## 1. HinGE

- **Provenance.** Srivastava & Singh, *HinGE: A Dataset for Generation and
  Evaluation of Code-Mixed Hinglish Text*, Eval4NLP 2021 (ACL Anthology
  [2021.eval4nlp-1.20](https://aclanthology.org/2021.eval4nlp-1.20/)).
  Primary release: `HinGE.pkl`, downloaded from
  https://drive.google.com/drive/folders/1sxU4PpFZs86ncad_iak4U6AY_2wOsayj
  (linked from the author's resource page). English/Hindi source pairs
  are drawn from the IIT Bombay parallel corpus.
- **Verified against the actual file** (not taken from secondary
  literature): **1,976 rows**, columns `English, Hindi,
  Human-generated Hinglish (list), WAC, WAC rating1, WAC rating2, PAC,
  PAC rating1, PAC rating2`. Summed human-generated Hinglish references:
  **4,799** (CLAUDE.md's locked fact states 4,803 — four off from what
  we measured directly off the pickle; flagging the discrepancy rather
  than silently matching the expected number. Worth a second person
  re-counting from Table 1 of the paper directly before either number
  goes in the final report). 1,973 of the 1,976 English sources are
  unique — three sentences appear twice in the base file with separate
  annotations.
- **What we use as the primary corpus.** `HinGE.pkl` flattened to one
  row per available Hinglish variant (human refs, WAC, PAC) —
  1,976 × (avg. 2.43 human refs + WAC + PAC) = 8,751 rows in
  `data/raw/hinge_base.tsv` (gitignored, not committed). This, not the
  shared-task CSVs below, is what CLAUDE.md's data table means by
  "primary parallel supervision, 1,976 En–Hi pairs."
- **Licensing — unresolved, flagged for the team.** No licence is
  stated on the download page, in the paper, or in the AI4Bharat
  catalog entry that links it (`AI4Bharat/indicnlp_catalog#213`). The
  readme only asks that the paper be cited. Since the English/Hindi
  pairs are drawn from the IIT Bombay corpus, HinGE at minimum inherits
  that corpus's CC-BY-NC-4.0 non-commercial restriction on those
  columns; the Hinglish/rating columns added by HinGE have no licence
  of their own that we could find. **Treat as CC-BY-NC-4.0-equivalent
  (non-commercial, attribution via citation) until someone confirms
  otherwise with the authors.**
- **Known limitations / the leakage finding.** HinGE itself has no
  released train/dev/test split. What does exist is a *different*,
  downstream release: the INLG 2021/2022 HinglishEval shared-task CSVs
  (2,766 / 395 / 791 rows — English, Hindi, Hinglish, average rating,
  disagreement — reusing HinGE's English sources with different,
  single Hinglish outputs and human quality ratings, hosted at the same
  Drive link). **These are not disjoint**: our audit
  (`python scripts/make_splits.py --audit
  data/raw/hinge_released_train.tsv data/raw/hinge_released_dev.tsv`)
  found 285 of dev's 376 unique English sources (75.8%) also present in
  train. We do not use these released splits anywhere in this project.
- **Split derivation.** See `data/processed/manifests/hinge_split_manifest.json`.
  Our own train/dev/test splits (7004 / 867 / 880 rows over the
  flattened base corpus, seed 42) were derived from the primary HinGE
  corpus, with whole near-duplicate clusters assigned to a single
  split. Near-duplicate grouping uses exact normalised match (NFKC,
  lowercase, punctuation stripped) **and** MinHash/LSH over character
  4-gram shingles (128 permutations, Jaccard threshold 0.7) — exact
  match alone found 1,973 unique English sources; MinHash merged one
  additional pair that exact match missed. Verified disjoint before
  writing.
- **Intended use.** Source of English→Hinglish reference pairs for
  training and evaluating M1–M4, and as the gold set from which the
  team-authored 800-item three-column set is derived.

## 2. IIT Bombay English–Hindi Parallel Corpus

- **Provenance.** Kunchukuttan, Mehta & Bhattacharyya, *The IIT Bombay
  English-Hindi Parallel Corpus*, LREC 2018. Compiled from GNOME, KDE4,
  Tanzil, Tatoeba, OpenSubtitles2013, HindEnCorp, the Hindi-English
  Wordnet Linkage, judicial/administrative/healthcare/tourism domain
  corpora, Indian government websites, TED talks, Wikipedia, BBC news,
  and book translations via the Gyaan-Nidhi corpus.
- **Licensing.** CC-BY-NC-4.0 (non-commercial), per
  https://www.cfilt.iitb.ac.in/iitb_parallel/. Components drawn from
  other sources keep their original licences where stricter — the
  corpus page states this explicitly, so a sub-source could in
  principle be more restrictive than CC-BY-NC-4.0. We have not audited
  every component source individually.
- **Attribution.** Cite Kunchukuttan et al. 2018 (LREC).
- **Known limitations.** Domain mix is heterogeneous (subtitles,
  government prose, religious text, TED transcripts); register varies
  widely within the corpus.
- **Intended use.** Indirect — this is the source corpus behind HinGE's
  English/Hindi columns, not ingested separately by this project.

## 3. Samanantar

- **Provenance.** Ramesh et al., *Samanantar: The Largest Publicly
  Available Parallel Corpora Collection for 11 Indic Languages*, TACL
  2022. 49.6M pairs: existing public parallel corpora (12.4M),
  web-mined content (37.4M), and pairs derived by pivoting through
  English across all 11 languages. Hosted at `ai4bharat/samanantar` on
  Hugging Face and at https://datasets.ai4bharat.org/samanantar/.
- **Licensing — conflicting sources, resolved by team decision.**
  AI4Bharat's own GitHub page
  (`AI4Bharat/indicnlp.ai4bharat.org/.../samanantar.md`) states the
  data *packaging* is released under **CC0** ("we do not own any of
  the text ... we license the actual packaging ... under CC0"). The
  Hugging Face dataset card's licence metadata states
  **CC-BY-NC-4.0**. These two official-looking sources disagree.
  **Team decision (25 Sep 2026): treat Samanantar as CC-BY-NC-4.0**
  — the more restrictive of the two, and the one carried in the
  canonical HF dataset card — until AI4Bharat clarifies. Do not rely
  on the CC0 claim for anything commercial or for redistribution
  without attribution.
- **Attribution.** Cite Ramesh et al. 2022 (TACL).
- **Known limitations.** AI4Bharat does not claim ownership of the
  underlying mined text; per-source rights for the 37.4M web-mined
  pairs are not individually verified by AI4Bharat or by us.
- **Intended use.** Candidate source for the M4 synthetic
  back-translation / code-mixing pipeline — parallel English–Hindi
  data run through the GCM toolkit, sampled by Switch-Point Fraction to
  match HinGE's real distribution, not sampled randomly.

## 4. Dakshina

- **Provenance.** Roark et al., *Processing South Asian Languages
  Written in the Latin Script: the Dakshina Dataset*, LREC 2020.
  12 South Asian languages (Bangla, Gujarati, Hindi, Kannada,
  Malayalam, Marathi, Punjabi, Sindhi, Sinhala, Tamil, Telugu, Urdu):
  native-script Wikipedia text, romanization lexicons, and full
  sentence parallel data in native script and Latin script.
  https://github.com/google-research-datasets/dakshina
- **Licensing.** CC BY-SA 4.0 — **share-alike**. Attribution required;
  any derivative work built from Dakshina data must be released under
  the same licence. This is stricter than the other three sources and
  needs a decision before Dakshina-derived material (e.g. romanization
  lexicon entries) goes into any split or manifest we intend to keep
  under a different licence.
- **Attribution.** Cite Roark et al. 2020 (LREC).
- **Intended use.** Romanization lexicon as a reference for spelling
  variance in Hindi written in Latin script — feeds the
  `spelling_variant_burden` tokenizer-fertility metric (owned
  separately, per CLAUDE.md section 7).

## Summary table

| Dataset | License | Restriction | Status |
|---|---|---|---|
| HinGE | Unstated; inherits IIT Bombay's terms at minimum | Non-commercial (inferred) | Unresolved — confirm with authors |
| IIT Bombay corpus | CC-BY-NC-4.0 | Non-commercial | Confirmed |
| Samanantar | CC-BY-NC-4.0 (team decision; conflicts with AI4Bharat's own CC0 claim) | Non-commercial, attribution | Confirmed by team decision, flagged |
| Dakshina | CC BY-SA 4.0 | Attribution, share-alike | Confirmed |

All four sources restrict at least to non-commercial and/or
attribution/share-alike use. That is consistent with a course research
project; it would block any commercial reuse of the resulting models or
data without separately clearing rights.
