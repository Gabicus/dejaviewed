Onyx — Self-Hosted Open-Source ChatGPT / Claude Replacement

Stand up Onyx (formerly Danswer, github.com/onyx-dot-app/onyx) as a self-hosted knowledge layer over everything that is not code: project notes, MEMORY.md files, guides, GitHub repos, optionally Gmail and Drive.
What a pro adds: Build the evaluation before tuning anything: a golden set of 30 real questions whose answers live in known documents, scored on citation correctness, so every change to chunking, embeddings…
Proof it worked: eval_onyx.py on the 10 held-out golden questions: citation hit at 80% or better, with 10 rows hand-checked by opening the cited file.
Biggest trap: Vespa or the model server is OOM-killed during first indexing. Fix: lower INDEX_BATCH_SIZE, switch to Lite, or add swap; re-measure.

Save this for when you build it. The carousel is the map; the guide has every prompt.

Built on posts by @marc.kaz
Full guide + prompts: dejaviewed.dev/guides/onyx-self-hosted-ai

#ai #claudecode #aiagents #onyx #onyxdotapponyx #rag #agents #llm #opensource #claude #promptengineering #aitools #generativeai #anthropic #automation #agenticai #aiworkflow #buildinpublic
