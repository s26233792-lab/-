# Contributing

Keep the skill portable and the workflow observable. Changes should state the concrete user request they improve, the expected output and a reproducible check.

```sh
python -m pip install -e ".[render]"
python -m unittest discover -s tests -v
```

For renderer changes, also install FFmpeg/ffprobe and run `tools/smoke_demo.py` in a new private output directory. Inspect the actual encoded previews and PNGs. The demo intentionally stops before review/export; only record checks actually performed. Do not add fabricated passing review records to production automation.

Do not commit source media, credentials, cookies, local workspaces, absolute personal paths or private voice samples. Use self-authored/explicitly licensed fixtures. Third-party code needs its exact upstream license and notice.

Keep instructions in the self-contained skill. Root docs link to the maintained reference rather than duplicating material contracts. Feature additions should not make collection automatically download/render, or turn a single requested target into a full unsolicited package.
