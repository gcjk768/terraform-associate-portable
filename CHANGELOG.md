# Changelog

- 2026-10-16 — first version for exam version 004 (Terraform 1.12, eight objectives): bot cloned from the AIP-C01 bot with Terraform prompts, bank from HashiCorp samples, PatrickWiloak (CC BY), sailor.sh, Whizlabs, examcert and certland samples plus MCQs generated from 354 flashcards (bradmccoydev MIT, allister-grange Anki), study cards from the same flashcards, served by exam-portal.
- 2026-10-17 — 338 generated questions from the flashcards: bank 406.
- 2026-11-14 — generated questions are checked by a blind solver (`python build_mcq.py --verify`): a second model call answers from the stem and options only; questions where it disagrees or finds more than one defensible answer stay out of the bank and are listed in `sources/mcq/review.md`.
