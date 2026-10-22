Strategy Autoresearch — the judge is the product, not the agent

Self-rewriting loops (Karpathy-style autoresearch, bilevel coach loops, Microsoft SkillOpt) keep any edit that beats a benchmark.
What a pro adds: A quant researcher would build and validate the judge before letting any agent search, using planted-signal and pure-noise datasets to measure its false-positive and false-negative rates.
Proof it worked: Pure-noise falsifier: 200 GBM and 200 shuffled-return datasets run through the full search; the judge passes at most 5% (target under 1%)…
Biggest trap: Judge gamed by search volume. Fix: N from the full trials table, rerun the noise falsifier.

Save this for when you build it. The carousel is the map; the guide has every prompt.

Built on posts by @marc.kaz @quant.dhawan @raycfu @nateherkai @charliemungerhub @avi_mukesh
Full guide + prompts: dejaviewed.dev/guides/overfit-proof-autoresearch

#ai #claudecode #aiagents #claude #python #codex #skillopt #claudex #openai #llm #agents #backtesting #algorithmictrading #montecarlo #workflowautomation #benchmarkgatededits #promptengineering #aitools
