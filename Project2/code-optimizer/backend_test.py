#!/usr/bin/env python
"""
backend_test.py
Run a quick smoke-test against the Code-Optimizer backend.

Usage examples:
---------------

# 1) Local uvicorn instance
python backend_test.py --repo https://github.com/pallets/flask.git

# 2) Backend in a local Docker container mapped to host:8000
python backend_test.py --target docker --repo https://github.com/psf/requests.git

# 3) Backend deployed as Azure Container Instance
python backend_test.py --target aci \
       --aci-fqdn your-aci-backend.eastus2.azurecontainer.io \
       --repo https://github.com/tiangolo/fastapi.git

How it works
- Uses requests.Session to persist the session cookie set by /session.
- Times every call; prints when --verbose is given.
- Reads the first file path the backend returns; no need for manual input.
- Aborts immediately (raise_for_status) on any non-2xx HTTP code.

It performs the full happy-path:

    POST /session → stores cookie
    POST /clone (repo URL arg)
    GET /file (first file in list)
    POST /optimise (same code, “add docstring” feedback)
    Prints round-trip times and key JSON snippets

"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

TARGETS = {
    "local": "http://localhost:8000",
    "docker": "http://localhost:8000",
    "aci": None,  # filled from --aci-fqdn
}


def die(msg: str):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=TARGETS, default="local",
                    help="Which backend location to hit")
    ap.add_argument("--aci-fqdn", help="Required if --target aci")
    ap.add_argument("--repo", required=True,
                    help="Public Git repo URL to clone in the test")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    base_url = TARGETS[args.target]
    if args.target == "aci":
        if not args.aci_fqdn:
            die("--aci-fqdn required with --target aci")
        base_url = f"http://{args.aci_fqdn}:8000"

    sess = requests.Session()

    def post(path, **kw):
        t0 = time.perf_counter()
        r = sess.post(f"{base_url}{path}", timeout=120, **kw)
        dt = (time.perf_counter() - t0) * 1000
        if args.verbose:
            print(f"POST {path} {r.status_code} {dt:0.1f} ms")
        r.raise_for_status()
        return r.json()

    def get(path, **kw):
        t0 = time.perf_counter()
        r = sess.get(f"{base_url}{path}", timeout=120, **kw)
        dt = (time.perf_counter() - t0) * 1000
        if args.verbose:
            print(f"GET  {path} {r.status_code} {dt:0.1f} ms")
        r.raise_for_status()
        return r.text

    # 1) session
    post("/session")
    print("✔ /session OK")

    # 2) clone
    clone_resp = post("/clone", json={"repo_url": args.repo})
    files = clone_resp["files"]
    if not files:
        die("Repository returned an empty file list")
    first_file = files[0]
    print(f"✔ /clone OK – {len(files)} files, using '{first_file}'")

    # 3) file
    code = get("/file", params={"relative_path": first_file})
    print(f"✔ /file OK – {len(code)} chars")

    # 4) optimise
    optim_resp = post("/optimise", json={"code": code, "feedback": "add docstring"})
    snippet = (optim_resp["optimised"] or "")[:300]
    print("✔ /optimise OK – first 300 chars:")
    print("-" * 60)
    print(snippet)
    print("-" * 60)

    # Summary
    print("🎉  Smoke-test finished without errors")


if __name__ == "__main__":
    main()
