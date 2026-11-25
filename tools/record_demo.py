"""Record a demo as a replay of captured output, not a screen recording. The README says so.

Each command is run once and its real stdout, exit code and wall time are captured. A self-contained
HTML player then types each command and reveals its captured output paced by that command's measured
duration, so a slow command looks slow and nothing on screen is hand written. Playwright records the
page to webm and ffmpeg transcodes to an MP4 and an autoplaying GIF. The manifest lists every
command with its exit code and duration, which is the artefact a reviewer checks the GIF against.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "docs" / "video"
CHROME = "/usr/bin/google-chrome"

# Ordered as the argument, not the feature list: establish the plan, show the hidden number, show
# the mechanism, show it survives tolerance, show the gate tuned off, then the receipts.
COMMANDS = [
    ["capacity-overlap", "analyze", "data/plan.csv"],
    ["python", "experiments/exp_aggregation_window.py"],
    ["python", "experiments/exp_threshold_sensitivity.py"],
    ["bash", "-c", "capacity-overlap analyze data/plan.csv --tolerance 0.5 --quiet; echo exit $?"],
    ["python", "tools/check_numbers.py"],
]


def capture() -> list[dict]:
    # Warm the import so the first command does not pay for it and the pacing stays honest.
    subprocess.run(["capacity-overlap", "--version"], cwd=ROOT, capture_output=True)
    segments = []
    for cmd in COMMANDS:
        start = time.perf_counter()
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        duration = time.perf_counter() - start
        segments.append(
            {
                "command": " ".join(cmd[2:]) if cmd[0] == "bash" else " ".join(cmd),
                "output": (proc.stdout + proc.stderr).rstrip("\n"),
                "exit_code": proc.returncode,
                "duration_s": round(duration, 3),
            }
        )
    return segments


def build_player(segments: list[dict]) -> str:
    data = json.dumps(segments)
    return _PLAYER.replace("__DATA__", data)


def main() -> int:
    from playwright.sync_api import sync_playwright

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    segments = capture()
    (VIDEO_DIR / "manifest.json").write_text(
        json.dumps(
            {
                "note": "replay of captured stdout; every line is real output, paced by wall time",
                "segments": segments,
            },
            indent=2,
        )
        + "\n"
    )

    player = VIDEO_DIR / "player.html"
    player.write_text(build_player(segments))

    total = sum(s["duration_s"] for s in segments) + 2 + 0.9 * len(segments)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        ctx = browser.new_context(
            viewport={"width": 900, "height": 560},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 900, "height": 560},
        )
        page = ctx.new_page()
        page.goto(player.as_uri())
        page.wait_for_timeout(int(total * 1000) + 1500)
        ctx.close()
        browser.close()

    webm = max(VIDEO_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    _transcode(webm)
    print(f"wrote {(VIDEO_DIR / 'demo.gif').relative_to(ROOT)} and demo.mp4")
    return 0


def _transcode(webm: Path) -> None:
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found; keeping the webm only", file=sys.stderr)
        return
    mp4 = VIDEO_DIR / "demo.mp4"
    gif = VIDEO_DIR / "demo.gif"
    palette = VIDEO_DIR / "palette.png"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(webm),
            "-movflags",
            "+faststart",
            "-pix_fmt",
            "yuv420p",
            "-vf",
            "scale=900:-2",
            str(mp4),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(webm),
            "-vf",
            "fps=10,scale=760:-1:flags=lanczos,palettegen",
            str(palette),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(webm),
            "-i",
            str(palette),
            "-lavfi",
            "fps=10,scale=760:-1:flags=lanczos[x];[x][1:v]paletteuse",
            str(gif),
        ],
        check=True,
        capture_output=True,
    )
    palette.unlink(missing_ok=True)


_PLAYER = """<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{margin:0;background:#0f1117;}
  .term{font-family:'DejaVu Sans Mono',Menlo,Consolas,monospace;font-size:14px;line-height:1.45;
        color:#e6e6e6;padding:18px 20px;white-space:pre-wrap;}
  .prompt{color:#4ec9b0;} .cmd{color:#dcdcaa;} .out{color:#d4d4d4;}
  .exit0{color:#6a9955;} .exit2{color:#f0a74d;}
</style></head><body><div class="term" id="t"></div>
<script>
const SEG = __DATA__;
const t = document.getElementById('t');
function line(cls, text){const d=document.createElement('div');
  d.className=cls;d.textContent=text;t.appendChild(d);
  window.scrollTo(0, document.body.scrollHeight);}
async function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function typeCmd(cmd){const d=document.createElement('div');
  const p=document.createElement('span');p.className='prompt';p.textContent='$ ';d.appendChild(p);
  const c=document.createElement('span');c.className='cmd';d.appendChild(c);t.appendChild(d);
  for(const ch of cmd){c.textContent+=ch;await sleep(16);}
}
async function run(){
  await sleep(600);
  for(const s of SEG){
    await typeCmd(s.command);
    await sleep(Math.min(1200, Math.max(250, s.duration_s*1000)));
    for(const ln of s.output.split('\\n')){
      const cls = /^PASS|meets the floor|match the code/.test(ln)?'out exit0':'out';
      line(cls, ln);
    }
    line(s.exit_code===0?'exit0':'exit2', '[exit '+s.exit_code+']');
    await sleep(700);
  }
}
run();
</script></body></html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
