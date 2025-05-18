import os
import logging
from datetime import timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel
from prompt_setup import register_prompts_once
from utils import clone_repo, list_files
from optimizers import optimise_with_guardrails



# ─── logging ───────────────────────────────────
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger("api")

app = FastAPI(title="Code Optimizer API")

register_prompts_once()
# ─── CORS ────────────────────────────────────────────────────────────────
# Since the SPA now always hits the API at the *same* origin (via /api),
# you can safely allow all origins or remove this middleware altogether.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # proxy avoids any real cross-site
    allow_credentials=True,       # cookies are included
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── session via cookie ─────────────────────────
_SIGNER = URLSafeTimedSerializer(os.getenv("SESSION_SECRET","dev-secret"))
_SESSION_LIFE = timedelta(hours=8)



def get_session_token(req: Request) -> str:
    t = req.cookies.get("session")
    if not t: raise HTTPException(401, "No session")
    try:
        return _SIGNER.loads(t, max_age=_SESSION_LIFE.total_seconds())
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "Invalid session")


def set_session_cookie(resp: Response):
    token = _SIGNER.dumps("ok")
    secure = os.getenv("COOKIE_SECURE","false").lower() in ("1","true")
    resp.set_cookie(
        "session", token,
        max_age=int(_SESSION_LIFE.total_seconds()),
        httponly=True,
        samesite="lax",   # same-origin fetch works fine
        secure=secure,    # only True in HTTPS/Azure
        path="/",
    )

# ─── in-memory per-session state ────────────────
STATE: dict[str,dict] = {}

def _state(sid:str) -> dict:
    return STATE.setdefault(sid, {"repo_path":None, "feedback": []})

# ─── Schemas ───────────────────────────────────
class CloneReq(BaseModel):
    repo_url: str

class OptimiseReq(BaseModel):
    code: str
    feedback: str | None = None



# ─── Endpoints ───────────────────────────────────────────────────────────
@app.post("/session")
def create_session(response: Response):
    set_session_cookie(response)
    return {"ok": True}

@app.post("/clone")
def clone_ep(req: CloneReq, sid: str = Depends(get_session_token)):
    path = clone_repo(req.repo_url, Path("clone_folder"))
    _state(sid)["repo_path"] = path
    return {"files": list_files(path)}

@app.get("/file")
def file_ep(relative_path: str, sid: str = Depends(get_session_token)):
    repo = _state(sid)["repo_path"] or HTTPException(400, "No repo")
    p = repo / relative_path
    if not p.exists(): raise HTTPException(404, "Not found")
    return FileResponse(p)

@app.post("/optimise")
def optimise_ep(req: OptimiseReq, session_id: str = Depends(get_session_token)):
    st = _state(session_id)
    if req.feedback:
        st["feedback"].append(req.feedback)
    new_code = optimise_with_guardrails(req.code, st["feedback"])
    return {"optimised": new_code, "feedback_history": st["feedback"]}
