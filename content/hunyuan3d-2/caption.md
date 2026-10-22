Hunyuan3D-2 — Tencent's Open Image-to-3D Mesh Generator

Hunyuan3D-2 is Tencent's open-source two-stage 3D asset generator.
What a pro adds: A technical artist or 3D ML engineer would read the Hunyuan3D 2.0 technical report and the 2.1 release before installing anything, pin the exact model revisions…
Proof it worked: Khronos glTF-Validator CLI reports zero errors on every GLB from the recommended variant.
Biggest trap: Rasterizer build fails. Fix: match torch CUDA to nvcc, set CUDA_HOME and TORCH_CUDA_ARCH_LIST, use a matching gcc.

Save this for when you build it. The carousel is the map; the guide has every prompt.

Built on posts by @nick_saraev
Full guide + prompts: dejaviewed.dev/guides/hunyuan3d-2

#ai #claudecode #aiagents #hunyuan3d #hunyuan3d2 #tencent #3d #art #design #claude #promptengineering #aitools #generativeai #llm #anthropic #automation #agenticai #aiworkflow
