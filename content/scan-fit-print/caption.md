Scan, Fit, Print — agents that design parts around real objects

Open-source scanners (a smartphone Orbiter rig, a Raspberry Pi handheld LiDAR, LingBot-Map's video-to-3D) now produce a usable mesh of the thing you need to fit.
What a pro adds: A mechanical design engineer would start with an error budget, not a scan: scanner accuracy, mesh-to-primitive fitting error, printer dimensional error, and the clearance they want, each measured.
Proof it worked: The physical fit on each real object, judged against a go/no-go criterion written before printing.
Biggest trap: Unscaled scan: photogrammetry mesh is uniformly 2% off. Fix: scale from the ChArUco board or a reference cube in frame.

Save this for when you build it. The carousel is the map; the guide has every prompt.

Built on posts by @itsnicconley @rawmechatronics @nateherkai @catlabs @jg.engineers @plumsojuyang
Full guide + prompts: dejaviewed.dev/guides/scan-fit-print

#ai #claudecode #aiagents #moonshine #raspberrypi5 #aftereffects #blender #claude #ffmpeg #huggingface #orbiter #3d #llm #uiux #apiintegration #ondeviceinference #promptengineering #aitools
