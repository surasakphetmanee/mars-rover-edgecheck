# Environment the committed results were produced with

| component | version |
|---|---|
| C compiler | Apple clang 21.0.0 (`cc -std=c99 -O2`); any C99 compiler with libm |
| Python (checker side) | 3.14.8, `requirements.txt` |
| Python (perception arm) | 3.12.15, `requirements-sam2.txt` |
| SAM 2 package | facebookresearch/sam2 commit `2b90b9f5ceec907a1c18123530e92e794ad901a4` |
| SAM 2.1 Hiera-Small checkpoint | `sam2.1_hiera_small.pt`, sha256 `6d1aa6f30de5c92224f8172114de081d104bbd23dd9dc5c58996f0cad5dc4d38` (Meta, Apache 2.0) |
| PRISM | 4.10.1 (`-explicit` engine for every oracle run) |
| PRISM-games | 3.2.4 |
| Storm | 1.14.0 (`--exact`) |
| Dataset | AI4Mars v0.6, Zenodo doi:10.5281/zenodo.15995036, MSL Navcam gold test set only |
| Latency host | Apple M-series laptop; stand-in = one efficiency core via `taskpolicy -c background`, thread CPU time |

`make test` needs only the C compiler and Python 3 (no PRISM, no torch, no dataset): it
replays the 84 maps of `kt1b_results.csv` and `kt1b_d9_results.csv` through the checker
and compares with the stored checker and PRISM values.
