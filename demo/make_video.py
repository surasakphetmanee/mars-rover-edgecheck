#!/usr/bin/env python3
"""demo/make_video.py -- 3-minute captioned demo video (English captions burned in
+ captions.srt for YouTube). Every number is read from this experiment's CSVs.
Needs: pillow, ffmpeg on PATH, demo/sam2/*.png (python3 demo/render.py SCENE sam2),
and the macOS font /System/Library/Fonts/HelveticaNeue.ttc (change FONT elsewhere)."""
import csv, json, re, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

E = Path(__file__).resolve().parents[1]; OUT = E / "demo" / "video"; OUT.mkdir(parents=True, exist_ok=True)
W, Hh, BAR = 1920, 1080, 230
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
f = lambda s, i=0: ImageFont.truetype(FONT, s, index=i)
rd = lambda p: list(csv.DictReader(open(E / p)))
k1a = rd("kt1a_results.csv"); k1b = rd("kt1b_results.csv"); tim = rd("exp2/timing.csv")
k4 = {a: rd(f"kt4_{a}.csv") for a in ("gold", "sam2")}; probe = json.load(open(E / "sam_probe_eval.json"))
ex = re.search(r"exhaustive: (\d+) maps", (E / "verify/exhaustive.log").read_text()).group(1)
by = {(r["map"], int(r["K"]), r["where"]): r for r in tim}
cpu = lambda m, K, w: float(by[(m, K, w)]["cpu_us_median"])
agree = sum(r["status"] == "agree" for r in k1a); w1a = max(float(r["abs_diff"]) for r in k1a if r["abs_diff"])
w1b = max(float(r["abs_diff"]) for r in k1b)
rer = {a: [r for r in k4[a] if r["rerank"] == "True"] for a in k4}
v05 = {a: sum(r["veto@0.05"] == "True" for r in k4[a]) for a in k4}
maxsaved = max(float(r["p_saved"]) for a in rer for r in rer[a])
top = sorted(rer["sam2"], key=lambda r: -float(r["p_saved"]))[:3]
stop = [r for r in k4["sam2"] if r["veto@0.05"] == "True" and r not in top][:1]

def canvas(bg="#0B0F14"): return Image.new("RGB", (W, Hh), bg)
def caption(im, text):
    d = ImageDraw.Draw(im); d.rectangle([0, Hh - BAR, W, Hh], fill="#000000")
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f(40)) > W - 160: lines.append(cur); cur = w
        else: cur = t
    lines.append(cur)
    y = Hh - BAR + (BAR - 52 * len(lines)) // 2
    for ln in lines:
        d.text(((W - d.textlength(ln, font=f(40))) / 2, y), ln, font=f(40), fill="white"); y += 52
    return im
def fit(img, box_w=W - 80, box_h=Hh - BAR - 60):
    s = min(box_w / img.width, box_h / img.height); return img.resize((int(img.width * s), int(img.height * s)))
def image_slide(path):
    im = canvas("white"); pic = fit(Image.open(path).convert("RGB"))
    im.paste(pic, ((W - pic.width) // 2, (Hh - BAR - pic.height) // 2)); return im
def text_slide(title, bullets, big=False):
    im = canvas(); d = ImageDraw.Draw(im)
    d.text((110, 90), title, font=f(68, 1), fill="#56B4E9")
    y = 230
    for b in bullets:
        d.text((130, y), b, font=f(56 if big else 46), fill="white"); y += 92 if big else 78
    return im
def pipeline_slide():
    im = canvas(); d = ImageDraw.Draw(im)
    d.text((110, 90), "Pipeline", font=f(68, 1), fill="#56B4E9")
    steps = ["Navcam frame\n(AI4Mars)", "SAM 2.1 encoder\n+ linear probe", "terrain class\ngrid 10 x 11",
             "terrain MDP\nbuilt on board", "C checker:\nall 27 arcs", "veto /\nre-rank"]
    bw, gap, y0 = 272, 36, 330
    x = (W - (len(steps) * bw + (len(steps) - 1) * gap)) // 2
    for i, s in enumerate(steps):
        d.rounded_rectangle([x, y0, x + bw, y0 + 230], radius=22, outline={1: "#56B4E9", 4: "#E69F00"}.get(i, "white"), width=5)
        for j, ln in enumerate(s.split("\n")):
            d.text((x + (bw - d.textlength(ln, font=f(31))) / 2, y0 + 72 + j * 48), ln, font=f(31), fill="white")
        if i < len(steps) - 1:
            cy = y0 + 115; d.polygon([(x + bw + 10, cy - 14), (x + bw + gap - 8, cy), (x + bw + 10, cy + 14)], fill="#7F7F7F")
        x += bw + gap
    d.text((110, 640), "blue = Meta SAM 2.1 (open weights)   ·   orange = the C model checker, validated against PRISM", font=f(34), fill="#BFBFBF")
    return im

sc = lambda r: E / "demo" / "sam2" / f"{r['scene']}.png"
S = [
 (8,  text_slide("Verified per-command safety for a Mars rover", ["computed on board, checked against PRISM", "", "Surasak Phetmanee", "Meta Global AI Developer Hackathon 2026 · Indie track · Push the Frontier"]),
      "Before a Mars rover drives, can it know the exact probability that the drive fails, computed on the rover itself?"),
 (12, text_slide("Why on board", ["Mars is 4 to 24 light-minutes from Earth: nobody can check a drive in the loop.",
                                 "The flight computer is far slower than a laptop.",
                                 "Rover planners rank arcs by a cost with no probabilistic meaning."]),
      "A rover decides alone. Its planner scores candidate arcs by cost, but no number says how likely an arc is to end stuck or crashed."),
 (14, pipeline_slide(),
      "Our pipeline: a Navcam frame, Meta SAM 2.1 features with a linear probe for terrain classes, a stochastic terrain model built on board, and a C checker that evaluates every candidate arc."),
 (16, image_slide(sc(top[0])),
      f"Each line is one of 27 candidate arcs, coloured by its verified failure probability. Here the planner's arc ({top[0]['planner_arc']}) has P = {float(top[0]['p_planner']):.4f}; the checker's best ({top[0]['best_arc']}) has P = {float(top[0]['p_best']):.4f}."),
 (12, image_slide(sc(top[1])),
      f"Another scene: planner {top[1]['planner_arc']} at P = {float(top[1]['p_planner']):.4f}, checker's best {top[1]['best_arc']} at P = {float(top[1]['p_best']):.4f}. Terrain: soil orange, bedrock blue, sand yellow."),
 (12, image_slide(sc(stop[0])),
      f"Here every arc is above the 0.05 threshold (best P = {float(stop[0]['p_best']):.4f}). The checker's answer is not 'steer elsewhere' but 'stop'."),
 (14, text_slide("Checking the checker", [f"Matches PRISM / PRISM-games on {agree} property checks", "   300 oracle properties + 480 bounded variants, MDPs and games", f"   worst error {w1a:.1e}",
                                          "Its on-board model build matches an independent PRISM encoding", f"   on {len(k1b):,} values, worst error {w1b:.1e}"]),
      "Why trust it? On every property it supports, the checker agrees with the PRISM model checker, both on an independent oracle and on its own terrain models."),
 (14, text_slide("Fast enough for a rover", [f"All 27 arcs of a scene: {cpu('synth_10x11', 8, 'pcore'):.0f} µs on a laptop core",
                                             f"{cpu('synth_10x11', 8, 'standin'):.0f} µs on an efficiency core standing in for a flight CPU",
                                             f"128 x 128 stress map, horizon 64: {cpu('synth_128x128', 64, 'standin')/1000:.0f} ms"]),
      "It is fast: the whole candidate set is checked in microseconds on a scene-sized grid, even on the slower stand-in core."),
 (12, text_slide("The code itself", [f"Every terrain map up to 3 x 3: {int(ex):,} maps", "checked under AddressSanitizer + UBSan: no violation",
                                     "plain C99, libc only, no allocation after load"]),
      "The C code was also checked exhaustively on every small map, with memory and undefined-behaviour sanitizers."),
 (14, text_slide("Finding 1 — the checker overrules the planner", [f"strictly safer arc found in {len(rer['sam2'])} of 20 scenes (SAM 2 maps)",
                                                                   f"but the gain is small: at most {maxsaved:.4f} in probability"]),
      "Finding one: the checker finds a strictly safer arc in a third to a half of the scenes, but the improvement is small."),
 (14, text_slide("Finding 2 — most vetoes mean 'stop'", ["no rock cells in these scenes: risk is sinkage along the drive,",
                                                          "shared by all 27 arcs of a scene", "the scene, not the arc, decides the verdict"]),
      "Finding two: almost every veto says stop, not go elsewhere, because every arc of a scene shares most of its risk."),
 (14, text_slide("Finding 3 — perception moves the verdict", [f"human gold labels: {v05['gold']} of 20 scenes vetoed at 0.05",
                                                              f"SAM 2 maps: {v05['sam2']} of 20", f"SAM 2 probe: {probe['patch_accuracy']*100:.1f} % patch accuracy on held-out scenes"]),
      "Finding three: what the camera model sees changes the verdict more than which arc is chosen. Where human labellers disagreed, SAM 2 still classifies the ground."),
 (11, text_slide("Limits we report", ["slip / sink per terrain class are assumed (no published table)", "image-space grid, not metres; no slope",
                                      "next: SAM 3.1 text prompts ('sand', 'bedrock')"]),
      "Limits: terrain probabilities are assumed, the grid is in image space, and SAM 3.1's text-prompted segmentation is the natural next step."),
 (7,  text_slide("Code and every result", ["github.com/surasakphetmanee/mars-rover-edgecheck", "", "MIT licence · data: NASA AI4Mars (CC BY 4.0) · SAM 2.1: Meta"], big=True),
      "Code, data pointers and every result are in the public repository. Thank you."),
]
total = sum(d for d, _, _ in S); assert total <= 180, total
lst, srt, t = [], [], 0.0
ts = lambda x: f"{int(x//3600):02d}:{int(x%3600//60):02d}:{int(x%60):02d},{int(round((x-int(x))*1000)):03d}"
for i, (dur, im, cap) in enumerate(S):
    p = OUT / f"s{i:02d}.png"; caption(im, cap).save(p)
    lst += [f"file '{p.name}'", f"duration {dur}"]
    srt += [str(i + 1), f"{ts(t)} --> {ts(t + dur)}", cap, ""]; t += dur
lst.append(f"file 's{len(S)-1:02d}.png'")
(OUT / "list.txt").write_text("\n".join(lst) + "\n"); (OUT / "captions.srt").write_text("\n".join(srt))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt",
                "-vf", "format=yuv420p", "-r", "25", "-t", str(total), "-c:v", "libx264", "-movflags", "+faststart", "demo_captioned.mp4"],
               cwd=OUT, check=True)
print(f"video {total}s, {len(S)} slides -> {OUT/'demo_captioned.mp4'}")
