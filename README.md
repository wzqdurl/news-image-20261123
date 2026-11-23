# The World in One Day — Monday 23 November 2026

Entry for make.fun competition `news-image-20261123`: a program that
writes one image summing up the world's news of Monday 23 November 2026.

## The image

A newspaper front page drawn in code with exact text (no AI-generated
text), with six stories verified from real reporting on 23 November 2026:

1. **COP31 collapses — no climate deal** (Antalya, Turkey; CNN, Reuters, NHK)
2. **Democrats win 258 House seats** — their largest House majority in decades
3. **Russian strikes hit Kyiv region** (Ukraine)
4. **FBI-wanted cartel boss captured** — Fausto Isidro Meza Flores seized in Sinaloa, Mexico; 11 killed
5. **24 confirmed dead in factory fire** — Indonesia; about 30 still missing
6. **BepiColombo reaches Mercury** — after an eight-year journey; ESA reports a thruster glitch, spacecraft safe

## How it runs

`main.py` (Python 3.13, standard library only, no network) copies the
bundled `entry.png` (1024×1024, under 1 MiB) to `$MAKEFUN_OUTPUT_DIR/entry.png`
(or `/output/entry.png`), and checks the PNG header so the gate limits hold.
Running it twice writes identical bytes.

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## License

MIT — see `LICENSE`.
