# data/ — AI4Mars gold test set (MSL Navcam)

Source: Swan, Ono, Atha et al., *AI4Mars: A Dataset for Terrain-Aware Autonomous
Driving on Mars*, Zenodo v0.6 (2022), doi:10.5281/zenodo.15995036, licence
**CC BY 4.0**. Cite doi:10.1109/CVPRW53098.2021.00226.

Only the members below were fetched (HTTP range reads of the 16.2 GB zip's
central directory, then of each member; the archive itself was never
downloaded), PI permission 2026-10-30 "test set only":
- `msl/ncam/labels/test/masked-gold-min3-100agree/*_merged.png` (322 labels)
- matching `msl/ncam/images/edr/*.JPG`, `images/mxy/*.png` (rover mask),
  `images/rng-30m/*.png` (beyond-30 m mask)

Not committed to git (size); re-fetch list = `all_test_scenes.txt`.
