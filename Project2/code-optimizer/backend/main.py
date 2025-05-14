import logging
import os
from datetime import timedelta
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel

from prompt_setup import register_prompts_once
from secrets import get_secret
from utils import clone_repo, list_files
from optimizers import optimise_with_guardrails

# ───────────── logging config ─────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s | %(name)s: %(message)s",
)
_LOGGER = logging.getLogger("api")

# ───────────── FastAPI setup ──────────────
app = FastAPI(title="Code Optimizer API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # front‑end dev only; tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ───────────── prompt registration once ───
register_prompts_once()

# ───────────── session utilities ──────────
_SIGNER = URLSafeTimedSerializer(os.getenv("SESSION_SECRET", "dev‑secret"))
_SESSION_LIFETIME = timedelta(hours=8)


def get_session_token(request: Request) -> str:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="No session")
    try:
        return _SIGNER.loads(token, max_age=_SESSION_LIFETIME.total_seconds())
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Invalid session")


def set_session_cookie(resp: Response) -> str:
    token = _SIGNER.dumps("ok")
    resp.set_cookie("session", token, max_age=_SESSION_LIFETIME.total_seconds(), httponly=True, samesite="lax")
    return token


# ───────────── in‑memory per‑session state ─────────────
STATE = {}  # session_id -> dict


def _state(session_id: str) -> dict:
    return STATE.setdefault(session_id, {"repo_path": None, "feedback": []})


# ───────────── Schemas ─────────────
class CloneReq(BaseModel):
    repo_url: str


class SelectFileReq(BaseModel):
    relative_path: str


class OptimiseReq(BaseModel):
    code: str
    feedback: str | None = None  # optional free‑text feedback


# ───────────── Endpoints ────────────
@app.post("/session")
def create_session(response: Response):
    sid = set_session_cookie(response)
    return {"session": sid}


@app.post("/clone")
def clone_repo_ep(req: CloneReq, session_id: str = Depends(get_session_token)):
    repo_path = clone_repo(req.repo_url, Path("clone_folder"))
    _state(session_id)["repo_path"] = repo_path
    files = list_files(repo_path)
    return {"files": files}


@app.get("/file")
def get_file(relative_path: str, session_id: str = Depends(get_session_token)):
    repo = _state(session_id).get("repo_path")
    if not repo:
        raise HTTPException(400, "Repo not cloned")
    abs_path = repo / relative_path
    if not abs_path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(abs_path)


@app.post("/optimise")
def optimise(req: OptimiseReq, session_id: str = Depends(get_session_token)):
    st = _state(session_id)
    feedback_hist: List[str] = st["feedback"]
    if req.feedback:
        feedback_hist.append(req.feedback)

    try:
        new_code = optimise_with_guardrails(req.code, feedback_hist)
    except ValueError as ve:
        raise HTTPException(400, str(ve))
    except RuntimeError as re:
        raise HTTPException(500, str(re))

    return {"optimised": new_code, "feedback_history": feedback_hist}
