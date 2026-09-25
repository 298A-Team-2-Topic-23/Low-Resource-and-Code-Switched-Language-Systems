# Annotation Guidelines v1 - English to Romanized Hinglish

## What we are producing

For each English source sentence, produce two references:

1. A monolingual Hindi translation in Devanagari.
2. A Romanized Hinglish translation that a bilingual speaker would naturally type.

The two references are independent. Do not translate the Romanized Hinglish by mechanically transliterating the Devanagari reference.

## Register

Write as you would to a friend on WhatsApp: conversational, direct, and natural. Do not use news-broadcast, bureaucratic, or textbook Hindi unless the English source requires that register.

Example:

- Source: `Come quickly, the movie is starting`
- Wrong: `Jaldi aaiye, chalchitra shuru ho raha hai` (too formal)
- Right: `Jaldi aa jao yaar, movie start ho rahi hai`

Preserve the source meaning, tense, polarity, speaker intent, and important details. Natural wording may reorder words, but it must not add or remove information.

## Orthography: do not normalise

Use the spelling you would naturally type. `nhi`, `nahi`, `nahin`, and similar variants are all valid when they reflect the annotator's natural usage. Do not standardise spelling across items or expand abbreviations solely to make them uniform. Orthographic variation is part of the phenomenon being measured.

Use Latin script for the Romanized Hinglish column. Preserve ordinary punctuation and casing when they support natural messaging, but do not use emojis, decorative formatting, or transliteration markup as a substitute for words.

## Which words stay in English

Keep a word in English when a bilingual speaker would naturally use it in conversation, including common technology and media words (`movie`, `phone`, `laptop`, `online`) and institutional words (`office`, `meeting`, `station`, `ticket`). Do not force-translate familiar loanwords into Sanskritised Hindi.

English words are not required. An entirely Hindi sentence written in Latin script is valid Hinglish when that is the natural choice.

## Named entities and numbers

Leave personal names, place names, organisations, products, and brands in their usual written form in the Romanized Hinglish column. Do not transliterate a named entity into Devanagari in that column. Translate surrounding common nouns normally. Preserve numbers and dates unless the source explicitly spells them out.

## Switch points

Switch languages where it feels natural, not at fixed intervals and not to satisfy a target English-word count. A good translation can have no English words, several English words, or an English phrase embedded in a Hindi sentence. Code-switching must remain compatible with the source meaning and conversational register.

## What to flag

Flag an item instead of guessing when the source is ambiguous, culturally underspecified, malformed, unreadable, or contains an entity that cannot be identified confidently. Record a short reason in the notes field. Do not silently invent context or a guideline.

## Annotation procedure

1. Read the English source once without consulting model output or another reference.
2. Write the Devanagari Hindi reference.
3. Write the Romanized Hinglish reference independently.
4. Check meaning, register, named entities, and orthography.
5. Mark `needs_review` if a decision required an unsupported assumption.

Annotators must not inspect model outputs before completing their own references. Reviewers may discuss disagreements only after all independent annotations are submitted.

## Pilot and reconciliation

All three raters independently score the same 50 pilot items for adequacy and fluency. Use the agreement script in `human_eval/agreement.py` with one CSV per dimension, for example `python human_eval/agreement.py --csv human_eval/pilot/adequacy.csv --rater-cols rater_a rater_b rater_c`. A blank rating means that the rater did not score the item and is excluded from that item's agreement calculation.

- `alpha >= 0.67`: usable; proceed to the full set.
- `0.40 <= alpha < 0.67`: revise the lowest-agreement guideline dimensions and rerun targeted training.
- `alpha < 0.40`: retrain the raters using shared examples before continuing.

Discuss items with a rating spread of two or more at the reconciliation meeting. Update this document with any newly discovered rule before authoring the full set. Do not change the 800-item gold references retroactively without recording the decision and version.