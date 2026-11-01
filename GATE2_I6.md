# GATE-2 — invariant I6 FAILED as pre-registered (2026-10-30)

**What failed.** I6 (degenerate check, plan.md): "report Pmax[F fail]; if ≈ 1 on
every scene the map is broken". With `blind` (leaving the image sideways)
counted as failure, Pmax[F≤8 fail] = 1.0000 on all 20 gold maps.

**Diagnosis.** Not a broken map and not a broken controller. Leaving the
image is a *deterministic* choice of the driver: from the start column 5 of
an 11-column grid, six consecutive left (or right) steers exit the image,
well inside k = 8. The worst-case driver therefore reaches `blind` with
probability 1 on **any** map — confirmed on a uniform-bedrock map with the real
parameters (Pmax = 1, Pmin = 0). M006's degenerate check was written for a
controller whose worst case should *not* be certain failure; under the blind
tier (plan-review R9, a conservative modelling choice) the worst case is
certain by construction, so I6 as written carries no information.

**Same check without the blind tier** (`--noblind`: leaving the image is not
counted; rock and sink remain): Pmax ∈ [0.0159, 0.1492] — far from 1.

| scene | Pmax (blind=fail) | Pmin (blind=fail) | Pmax (noblind) | Pmin (noblind) |
|---|---|---|---|---|
| NLB_442593301EDR_F0250312NCAM00353M1 | 1.0000 | 0.0159 | 0.0743 | 0.0096 |
| NLB_463107188EDR_F0410748NCAM00274M1 | 1.0000 | 0.1142 | 0.1492 | 0.0859 |
| NLB_443668744EDR_F0251238NCAM00292M1 | 1.0000 | 0.0682 | 0.1185 | 0.0096 |
| NLB_552677513EDR_F0642088NCAM00255M1 | 1.0000 | 0.1492 | 0.1492 | 0.0859 |
| NLB_459291152EDR_F0391552NCAM00252M1 | 1.0000 | 0.0159 | 0.0698 | 0.0096 |
| NLB_439226140EDR_F0240000NCAM00350M1 | 1.0000 | 0.0511 | 0.0743 | 0.0447 |
| NLB_457152554EDR_F0380000NCAM00275M1 | 1.0000 | 0.1492 | 0.1492 | 0.0859 |
| NLB_520359112EDR_F0550940NCAM00654M1 | 1.0000 | 0.0589 | 0.1492 | 0.0588 |
| NLB_613582793EDR_F0760556NCAM00385M1 | 1.0000 | 0.0159 | 0.0357 | 0.0096 |
| NLB_613583763EDR_F0760568NCAM00354M1 | 1.0000 | 0.0159 | 0.0159 | 0.0096 |
| NLB_556756244EDR_F0651642NCAM00285M1 | 1.0000 | 0.1315 | 0.1492 | 0.0797 |
| NLB_574078440EDR_F0681626NCAM00354M1 | 1.0000 | 0.0000 | 0.0775 | 0.0000 |
| NLB_525149717EDR_F0570774NCAM07753M1 | 1.0000 | 0.1142 | 0.1492 | 0.0834 |
| NLB_552682173EDR_F0642088NCAM07753M1 | 1.0000 | 0.1319 | 0.1492 | 0.0859 |
| NLB_443663262EDR_F0251238NCAM00289M1 | 1.0000 | 0.0159 | 0.1031 | 0.0137 |
| NLB_512555120EDR_F0532644NCAM00264M1 | 1.0000 | 0.0906 | 0.1492 | 0.0714 |
| NLB_525149367EDR_F0570774NCAM00654M1 | 1.0000 | 0.0200 | 0.1492 | 0.0200 |
| NLB_543357370EDR_F0613076NCAM00287M1 | 1.0000 | 0.1492 | 0.1492 | 0.0859 |
| NLB_505898434EDR_F0521162NCAM12753M1 | 1.0000 | 0.1492 | 0.1492 | 0.0859 |
| NLB_565373417EDR_F0670650NCAM12753M1 | 1.0000 | 0.0829 | 0.1177 | 0.0774 |

Every other invariant passed on all 20 gold maps: I2 monotone in k, I3
bounded = unbounded at k = R + 1, I5 zero slip/sink → every arc 0, I4 on the
two synthetic maps (`invariants.csv`). I1 (checker = PRISM) is KT1a 780/780
rows and KT1b.

**Proposed resolution — PI verdict needed.** Re-state I6 as "Pmax[F≤8 fail]
with the blind tier excluded must be < 0.99 on at least one scene" (passes:
max 0.1492), and report the blind=fail Pmax = 1 as a
documented property of the conservative tier, not a defect. KT4 (veto study)
uses the planner's arc followed by the *minimising* continuation, where the
deterministic exit is never chosen, so its numbers do not depend on this
verdict — but KT4 is held until the PI decides, per the GATE-2 rule.


**PI verdict 2026-10-31: ตกลง (accepted).** I6 restated as proposed; KT4 released. Verdict log kind=gate-2.
