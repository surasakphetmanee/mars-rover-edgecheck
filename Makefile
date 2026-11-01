CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra
PY ?= python3

all: checker/edgecheck

checker/edgecheck: checker/edgecheck.c
	$(CC) $(CFLAGS) -o $@ $< -lm

# PRISM-free: replays every map, K and blind setting of kt1b_results.csv and
# kt1b_d9_results.csv through the checker and compares with the stored checker AND
# PRISM values; plus a hand-written explicit model with known values.
test: checker/edgecheck
	$(PY) -I tests/test_checker.py

clean:
	rm -f checker/edgecheck
	rm -rf checker/edgecheck.dSYM

.PHONY: all test clean
