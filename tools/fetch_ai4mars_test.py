#!/usr/bin/env python3
"""Fetch only the AI4Mars MSL Navcam gold test set (322 scenes, ~107 MB) out of the
16.2 GB Zenodo archive, using HTTP range reads of the zip's central directory and
of each member. The archive itself is never downloaded.

  python -I tools/fetch_ai4mars_test.py      -> data/ai4mars_test/ai4mars-dataset-merged-0.6/...

Dataset: Swan, Ono, Atha et al., AI4Mars, Zenodo v0.6, doi:10.5281/zenodo.15995036,
licence CC BY 4.0; cite doi:10.1109/CVPRW53098.2021.00226.
"""
import io, sys, urllib.request, zipfile
from pathlib import Path

URL = "https://zenodo.org/records/15995036/files/ai4mars-dataset-merged-0.6.zip?download=1"
ROOT = Path(__file__).resolve().parents[1]
R = "ai4mars-dataset-merged-0.6/msl/ncam"

class HttpFile(io.RawIOBase):
    def __init__(self, url):
        self.url, self.pos = url, 0
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as r:
            self.size = int(r.headers["Content-Length"])
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off); return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0 or self.pos >= self.size: return b""
        end = min(self.size, self.pos + n) - 1
        with urllib.request.urlopen(urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})) as r:
            d = r.read()
        self.pos += len(d); return d
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

def main():
    scenes = (ROOT / "all_test_scenes.txt").read_text().split()
    z = zipfile.ZipFile(io.BufferedReader(HttpFile(URL), buffer_size=1 << 17))
    names = set(z.namelist())
    want = []
    for s in scenes:
        for n in (f"{R}/labels/test/masked-gold-min3-100agree/{s}_merged.png", f"{R}/images/edr/{s}.JPG",
                  f"{R}/images/mxy/{s.replace('EDR', 'MXY')}.png", f"{R}/images/rng-30m/{s.replace('EDR', 'RNG')}.png"):
            if n in names: want.append(n)
    dest = ROOT / "data/ai4mars_test"
    for i, n in enumerate(want):
        if not (dest / n).exists(): z.extract(n, dest)
        if i % 100 == 0: print(f"{i}/{len(want)}", file=sys.stderr, flush=True)
    print(f"extracted {len(want)} members for {len(scenes)} scenes into {dest}")

if __name__ == "__main__":
    main()
