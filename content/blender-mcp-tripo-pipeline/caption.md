Reference Image to Rendered Scene, Driven by Claude

Blender MCP is a Model Context Protocol server that exposes Blender as a set of tools an LLM can call.
What a pro adds: A 3D generalist would match the camera first: recover focal length and camera pose from the reference photo with fSpy, set real-world units…
Proof it worked: Blender 4.2 LTS headless: blender -b scene.blend -f 1 completes with no errors or missing-file warnings after packing resources.
Biggest trap: Wrong provider assumption. Fix: read server.py, then use the right key or a Tripo helper.

Save this for when you build it. The carousel is the map; the guide has every prompt.

Built on posts by @bilawal.ai
Full guide + prompts: dejaviewed.dev/guides/blender-mcp-tripo-pipeline

#ai #claudecode #aiagents #blender #mcp #tripo #unity #unrealengine #3d #agents #llm #claude #promptengineering #aitools #generativeai #anthropic #automation #agenticai
