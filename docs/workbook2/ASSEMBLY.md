# Assembling T2.A6.docx

Linear **298-71**. Owner: Savalia. This file is a working note and is not part of the document.

```bash
pip install -r requirements-report.txt
python scripts/build_workbook2.py            # draft, lists everything still open
python scripts/build_workbook2.py --final    # refuses to write while anything is open
```

A section lands by committing `docs/workbook2/section_N_M.md`. `section_3_1_3_2.md` covers both
sections. Each file must name who wrote it, for example `Written by Savalia, Jenil.`

## Before upload

1. **Check against Template 5.** The template file was not available when this was built. The
   structure comes from the requirements quoted in the briefs, so section order, the position of the
   carry-forward table, and the cover need comparing against it.
2. **Fill the five checklist rows** in `submission_checklist.md` from the template. Their wording was
   deliberately not guessed.
3. **Confirm the new references have been read.** Section 1.5 commits to citing only works a member
   has read. Delete the citation and the entry for any that nobody can confirm:
   Csaki et al. (2023), Husain et al. (2024), Poplack (1980), Pratapa et al. (2018), Ramesh et al.
   (2022), Rizvi et al. (2021), Roark et al. (2020), Sennrich et al. (2016), Yamaguchi et al. (2026).
4. **Re-sort the references** after adding sources from the other sections, and recount the journal
   or conference share in `self_assessment.md` and `carry_forward.md`.
5. **Re-rate** every `[PENDING: not on main]` row against the rubric wording when its section lands.
6. **Walk the sections** for the checklist row "every claim links to a commit, run, dataset version
   or Linear issue".
7. **Record the compute decision** in `carry_forward.md`.
8. **Confirm rubric line 4.5.** The rubric's 4.5 Data Pipeline Demo (2 points) is presented live on
   12 November, and the brief says Template 5's sections 4.5 and 4.6 stay bare headings, so
   `section_4_5_pipeline_demo.md` is not assembled. Check that nothing else is expected in the file.

## After upload

Keep 298-71 open until the submission is confirmed. The closing evidence is the Canvas receipt.
