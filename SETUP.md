# Setup: running the C++ extension on Claude Code

This is the exact sequence to get Claude Code building and extending the C++ Shepherding Library.
Recommended path is your local Ubuntu machine (headless build). A Windows path is at the end.

Repo: https://github.com/Hebaelfiqi/Shepherding

---

## A. Install Claude Code (once)

Claude Code runs on macOS, Linux, and Windows and needs a paid Claude (Pro or Max) plan or API
credits. Two install methods; the native installer needs no Node.js.

Native installer (recommended), on Ubuntu:
```
curl -fsSL https://claude.ai/install.sh | bash
```
or the npm method (requires Node.js 18 or newer, never use sudo):
```
npm install -g @anthropic-ai/claude-code
```
Verify and authenticate:
```
claude --version
claude            # first launch opens a browser login; or: export ANTHROPIC_API_KEY=sk-ant-...
```

## B. Install the C++ toolchain (once, Ubuntu)
```
sudo apt update
sudo apt install -y build-essential cmake git
```
SDL2 is not needed for the headless build. Only add `libsdl2-dev libsdl2-image-dev libsdl2-ttf-dev`
if you later want the on-screen visualisation.

## C. Get the code and drop in the task files
```
git clone https://github.com/Hebaelfiqi/Shepherding.git
cd Shepherding
```
Copy these four files from this bundle into the repository root:
- `REQUIREMENTS.md`  (the full task and equations)
- `CLAUDE.md`        (standing context Claude Code reads automatically)
- `CMakeLists.txt`   (starter headless build)
- `SETUP.md`         (this file, optional to keep)

`CLAUDE.md` is picked up automatically by Claude Code from the working directory, so its rules and
the do-not-touch list apply to every session in this repo.

## D. Launch Claude Code in the repo
```
claude
```
Give it this first prompt (it maps to Milestones M0 and M0.5 in REQUIREMENTS.md):

> Read REQUIREMENTS.md and CLAUDE.md in full. We are on Linux, so do Milestone M0 then M0.5 only:
> detect the build system, then port to a headless CMake build. Specifically: guard the Windows
> includes in stdafx.h and pch.h under `#ifdef _WIN32`; vendor tinyxml2 under third_party/ and
> replace the MSXML6 COM config loader in ShepherdingSimC_V1.cpp with a tinyxml2 loader that fills
> the exact same globals; add ShepherdingSimC_V1/main_headless.cpp that loads the config, runs the
> Sim loop, and writes per-step CSV with no SDL and no COM; finish wiring CMakeLists.txt. Then build
> and run InputFiles/Config.xml headless and show me the first rows of CSV output. Do not start any
> adversarial changes yet, and do not modify the base physics. Commit M0.5 on its own branch.

Review the result. When the baseline runs headless, continue:

> Good. Now proceed through Milestones M1 to M7 in REQUIREMENTS.md, one at a time, pausing after each
> for me to review. Keep every new feature behind the AdversarialMode config flags so the default
> config still reproduces the original library. Add the unit tests as you go.

## E. Permissions and long runs
- Claude Code will ask before running shell commands (apt, cmake, git). Approve the build and test
  commands. If you want fewer prompts for a trusted session you can start it in an accept-edits mode,
  but for a first run, approving each step is safer.
- The 27 x 200 experiment is light (seconds to a couple of minutes once compiled). No GPU is needed.

---

## Windows alternative (most faithful, no porting)
If you have a Windows machine with Visual Studio and want to avoid the Linux port entirely:
1. Install Claude Code on Windows (PowerShell): `irm https://claude.ai/install.ps1 | iex`.
2. Open the repo, copy in `REQUIREMENTS.md` and `CLAUDE.md`.
3. Start Claude Code and tell it to build `ClassLibraryProjects.sln` with MSBuild, run
   `ShepherdingSimC_V1.exe ../InputFiles/Config.xml` as the baseline, then proceed from Milestone M1
   (skip M0.5; no porting needed on Windows). The `CMakeLists.txt` is not used on this path.

---

## Why local, not the Anthropic cloud sandbox
This whole reproduction started in an ephemeral cloud sandbox, which is exactly why it ended up as a
separate Python port: that environment resets between sessions, is headless, and could not build the
Visual Studio plus SDL2 project. Extending the real C++ library wants the opposite: a persistent
checkout and build directory, full control to install g++, cmake and gdb, results that stick around
across sessions, and Claude Code operating on the repo in place. Local Ubuntu gives all of that. A
cloud environment is only worth it later for firing off many parallel parameter sweeps once the
headless build is stable.
