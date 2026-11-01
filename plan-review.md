# PLAN REVIEW — exp1 (adversarial, 2026-10-30)

*Persona: a planetary-robotics reviewer who has sat on AutoNav reviews and a
formal-methods reviewer who has seen too many "verified" tools validate
themselves. Each objection is answered in the plan or the plan changes.*

**R1 — "Your grid is not the ground."** Image-space bands are not metres; a
"k = 8 step" horizon means eight range bands, and far bands are wider than
near ones. *Resolution:* accepted as the abstraction and named everywhere as
"range bands"; no metric claim (no "metres", no "m/s"). The check is about
the probability structure of an arc over classified terrain, not about
distances. A DEM-based ground grid is future work.

**R2 — "SAM 2 does not know what sand is."** SAM 2 returns class-agnostic
masks. Somebody has to label them, and if the gold labels do it the
perception arm is fake. *Change:* class assignment = a **linear probe on SAM
2's own image-encoder features**, average-pooled per SAM mask, trained on
the gold labels of the test images that are **not** evaluation scenes. The
20 evaluation scenes are fixed now, before any segmentation runs (seed 20261030,
`exp1/eval_scenes.txt`), and never touch the probe. Segment-level accuracy of
the probe on the 20 scenes is reported as an input condition. When the Meta
Model API key arrives, Muse Spark is run as a zero-shot labeller on the same
masks and compared; the probe stays as the baseline. No extra model download
beyond SAM 2.1 (PI permission covered SAM 2).

**R3 — "Two encodings that share code are one encoding."** *Requirement:*
`gen_rover.py` (Python → PRISM text) and the C builder (front end B) share
only the map file and the parameter CSV. Neither imports the other. A
reviewer can diff them.

**R4 — "Front end A tests nothing."** It tests the engine on PRISM's own
state space: 300 values across MDPs and turn-based games. That is the claim
it supports and no more. Translation correctness is KT1b's job.

**R5 — "θ = 0.05 was chosen to make vetoes happen."** Fixed here, before
any scene is checked, and also reported at θ ∈ {0.01, 0.10} as a sweep, so a
reader can see the veto fraction is not an artefact of one threshold.

**R6 — "Background QoS is not a flight CPU."** Correct; it is the PI's
stand-in, named as such. The paper reports the measured slowdown factor
(background vs P-core) so the reader can scale. No sentence says RAD750.

**R7 — "The models are tiny; of course it is fast."** The scene grids are
small by construction (that is what a Navcam frame gives at this
resolution). H3's scale sweep to 128 × 128 and k = 64 is the answer; the
paper reports where the deadline breaks, if it does.

**R8 — "Assumed slip numbers make P(fail) meaningless."** The absolute
values are conditional on `terrain_params.csv`, printed as `assumed` in every
table. KT4 compares the planner and the checker *on the same parameters*, so
the veto fraction is a statement about the planner's cost function versus
the probability it ignores — that comparison survives a change of numbers,
which H5 (stretch) would quantify.

**R9 — "Leaving the image counts as a crash?"** Conservative, and it biases
arcs at the image edge toward veto. Reported as its own tier (`blind`)
inside the collision value so a reader can subtract it.

**Verdict:** plan APPROVED with changes R2 (probe + held-out scenes), R3
(independence of encodings), R5 (threshold sweep), R9 (blind tier reported).
