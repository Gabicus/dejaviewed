The Pipeline That Didn't Exist 6 Months Ago

MCP + Blender + Tripo + Claude Code together create a natural language 3D scene builder — describe what you want, get a full 3D scene. This was impossible before MCP existed.
What a pro adds: A technical artist would first lock the pipeline contract: meters, up-axis, naming, polygon budget per asset, Principled BSDF materials.
Proof it worked: Blender 4.2 LTS: blender --factory-startup -b scenes/<id>/scene.blend -f 1 exits 0 and writes a render for all three scenes.
Biggest trap: Assets arrive at random scale. Fix: rescale every import from a written size table before placement.

Save this for when you build it. The carousel is the map; the guide has every prompt.

Built on posts by @bilawal.ai @nick_saraev @jens.heitmann @neles0n
Full guide + prompts: dejaviewed.dev/guides/natural-language-3d

#ai #claudecode #aiagents #blender #claude #higgsfield #hunyuan3d #hunyuan3d2 #mcp #playwright #3d #llm #vfx #2dto3dpipeline #mcpservers #promptengineering #aitools #generativeai
