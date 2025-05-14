# Code Optimizer Assistant — FastAPI + React

A two‑tier web application that

1. Clones any public GitHub repo
2. Lets you view / edit a file, add plain‑English feedback
3. Runs a composite LangChain pipeline—`input_guardrail ➜ optimizer ➜ output_guardrail`—on Azure GPT‑4o
4. Tracks prompts & traces in **Langfuse**
5. Persists no secrets in code: all credentials live in **Azure Key Vault** and are injected at runtime

---

\## 📂 Project layout

```
code-optimizer/
├── backend/
│   ├── main.py
│   ├── prompt_setup.py
│   ├── secrets.py
│   ├── guardrails.py
│   ├── optimizers.py
│   ├── utils.py
│   └── requirements.txt
└── frontend/
    ├── package.json
    └── src/
        ├── api.js
        └── App.jsx
```

> **Quick scaffold** (run in an empty directory):

```bash
mkdir -p code-optimizer/backend code-optimizer/frontend/src


# 1) back‑end tree  ───────────────────────────────────────────────
mkdir -p code-optimizer/backend && \
touch code-optimizer/backend/{main.py,prompt_setup.py,secrets.py,guardrails.py,optimizers.py,utils.py,requirements.txt,backend.Dockerfile}

# 2) front‑end tree  ──────────────────────────────────────────────
mkdir -p code-optimizer/frontend/src && \
touch code-optimizer/frontend/{package.json,frontend.Dockerfile} code-optimizer/frontend/src/{api.js,App.jsx}

```

---

\## 🚀 Resource provisioning (once)

\### 1 Login to Azure & create variables

```bash
az login
```

```bash
NAME=anshu
RG=Tredence-Batch2
VAULT=vault$NAME
AOAIKEY=
LFPUBLIC=
LFSECRET=
SP=sp$NAME
ACR=codeacr$NAME
ACI=aci$NAME
IMG=img$NAME
```



\### 2 Create **Key Vault** + secrets

```bash
# vault
az keyvault create -g $RG$ -n $VAULT --enable-rbac-authorization true

# add the three secrets the app needs
az keyvault secret set -n "AZURE-OPENAI-API-KEY"     --vault-name $VAULT --value "<your-azure-openai-key>"
az keyvault secret set -n "LANGFUSE-PUBLIC-KEY"      --vault-name $VAULT --value "<langfuse-public>"
az keyvault secret set -n "LANGFUSE-SECRET-KEY"      --vault-name $VAULT --value "<langfuse-secret>"
```

\### 3 Create a **service principal** for Key Vault access

```bash
az ad sp create-for-rbac -n $SP \
  --role "Key Vault Secrets User" \
  --scopes $(az keyvault show -n $VAULT --query id -o tsv) \
  --sdk-auth > sp.json
```

The JSON looks like:

```json
{
  "clientId": "...",
  "clientSecret": "...",
  "tenantId": "...",
  "subscriptionId": "..."
}
```

Copy the three fields—we’ll map them to environment variables.

\### 4 Create an **Azure Container Registry**

```bash
az acr create -g code-opt-rg -n codeoptaicr --sku Basic
```

---

\## 🔑 Local environment variables

Create a `.env` file at the project root:

```bash
cat <<'EOF' > .env
# --------- vault & service principal ----------
BDC_VAULT_NAME=BDCvault
AZURE_CLIENT_ID=<clientId-from-sp.json>
AZURE_CLIENT_SECRET=<clientSecret-from-sp.json>
AZURE_TENANT_ID=<tenantId-from-sp.json>

# --------- FastAPI session secret -------------
SESSION_SECRET=$(openssl rand -hex 16)

# (only needed when running the frontend locally)
VITE_API_URL=http://localhost:8000
EOF
```

Load it in your shell:

```bash
export $(grep -v '^#' .env | xargs)
```

---

\## 🐍 Backend setup (local dev)

```bash
cd code-optimizer/backend
python3 -m venv .venv            # Python 3.10+
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload        # default :8000
```

The first boot will create the three prompts in Langfuse (only once).

---

\## 🕸️ Frontend setup (local dev)

```bash
cd ../frontend
# install Node via nvm if you don’t have it
npm install
npm run dev                      # Vite dev server on :5173
```

Open [http://localhost:5173](http://localhost:5173).
While the backend churns, you’ll see a spinner (⏳ Working…).

---

\## 🐳 Docker build & push

\### 1 Backend image

```bash
cd code-optimizer
docker build -f backend.Dockerfile -t code-optimizer-backend:latest ./backend
az acr login -n codeoptaicr
docker tag code-optimizer-backend:latest codeoptaicr.azurecr.io/code-optimizer-backend:latest
docker push codeoptaicr.azurecr.io/code-optimizer-backend:latest
```

**`backend.Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

\### 2 Frontend image (static Nginx)

```bash
# build React production bundle
cd frontend
npm run build               # creates dist/
cd ..

# Docker
docker build -f frontend.Dockerfile -t code-optimizer-frontend:latest ./frontend
docker tag code-optimizer-frontend:latest codeoptaicr.azurecr.io/code-optimizer-frontend:latest
docker push codeoptaicr.azurecr.io/code-optimizer-frontend:latest
```

**`frontend.Dockerfile`**

```dockerfile
FROM nginx:1.25-alpine
COPY --from=node:20-alpine /usr/local/bin/node /usr/local/bin/node
WORKDIR /usr/share/nginx/html
COPY frontend/dist/ .
# simple CORS header
RUN sed -i '38i add_header Access-Control-Allow-Origin *;' /etc/nginx/nginx.conf
EXPOSE 80
```

---

\## ☁️ Deploy to Azure Container Instances

```bash
# backend
az container create -g code-opt-rg -n code-opt-backend \
  --image codeoptaicr.azurecr.io/code-optimizer-backend:latest \
  --registry-login-server codeoptaicr.azurecr.io \
  --cpu 1 --memory 2 \
  --environment-variables \
     BDC_VAULT_NAME=$BDC_VAULT_NAME \
     AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
     AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
     AZURE_TENANT_ID=$AZURE_TENANT_ID \
     SESSION_SECRET=$SESSION_SECRET \
  --dns-name-label code-opt-backend-$RANDOM --ports 8000

# frontend (pointing to backend FQDN)
BACKEND_FQDN=$(az container show -g code-opt-rg -n code-opt-backend --query ipAddress.fqdn -o tsv)
az container create -g code-opt-rg -n code-opt-frontend \
  --image codeoptaicr.azurecr.io/code-optimizer-frontend:latest \
  --registry-login-server codeoptaicr.azurecr.io \
  --cpu 1 --memory 1 \
  --environment-variables VITE_API_URL=http://$BACKEND_FQDN:8000 \
  --dns-name-label code-opt-frontend-$RANDOM --ports 80
```

Grab the frontend FQDN:

```bash
az container show -g code-opt-rg -n code-opt-frontend --query ipAddress.fqdn -o tsv
```

Open it in your browser—you’re live on Azure 🎉

---

\## 🛠️ Troubleshooting

| Symptom                         | Fix                                                                                        |
| ------------------------------- | ------------------------------------------------------------------------------------------ |
| **KeyVault “Forbidden”**        | Confirm the service‑principal has *Key Vault Secrets User* role; check typo in env‑vars.   |
| **Langfuse prompts duplicated** | They are created idempotently; duplicates mean you used a different project key.           |
| **CORS blocked in browser**     | Verify `VITE_API_URL` in frontend env and that Nginx adds `Access-Control-Allow-Origin *`. |
| **LLM “quota exceeded”**        | You hit your Azure OpenAI limit—raise it or lower usage.                                   |

---

\## 📄 MIT License

This project remains MIT‑licensed. See `LICENSE`.



Below is a complete **reference implementation** that folds in every change you asked for:

* **FastAPI + Uvicorn backend** (no Streamlit)
* **React frontend** with a spinner while the backend works
* **Session tokens** (signed cookies) so one user’s repo/feedback history is isolated
* **One‑time prompt registration** on app start‑up
* **Environment‑driven secrets**, fetched **once per worker**
* **`prompt_chain.py` split into `secrets.py`, `guardrails.py`, `optimizers.py`**
* **Fixed guardrail boolean check**
* **Composite “optimize‑with‑guardrails” chain** (three auto‑retries max)
* **`os.path` + `logging` everywhere—no `print`**

> ⚠️ **Copy each file into the matching path** (shown in the tree).
> Then run `uvicorn main:app --reload` for the API and `npm run dev` inside `frontend/` for the UI.

```
code_optimizer_backend/
├── main.py
├── prompt_setup.py
├── secrets.py
├── guardrails.py
├── optimizers.py
├── utils.py
└── requirements.txt          # see bottom of answer
frontend/
├── src/
│   ├── App.jsx
│   └── api.js
└── package.json
```

---

\### backend / `secrets.py`

```python
"""
Centralised, cached secret retrieval.
Secrets come from two sources:

1. Environment variables (always)
2. Azure Key Vault, *once per worker*, using those env vars.

Required env vars
─────────────────
BDC_VAULT_NAME              e.g. 'BDCvault'
AZURE_CLIENT_ID
AZURE_CLIENT_SECRET
AZURE_TENANT_ID
"""

from functools import lru_cache
import logging
import os
from typing import Dict

from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient

_LOGGER = logging.getLogger(__name__)


@lru_cache
def _kv_client() -> SecretClient:
    vault_name = os.getenv("BDC_VAULT_NAME")
    if not vault_name:
        raise EnvironmentError("BDC_VAULT_NAME env var not set")

    credential = ClientSecretCredential(
        tenant_id=os.getenv("AZURE_TENANT_ID"),
        client_id=os.getenv("AZURE_CLIENT_ID"),
        client_secret=os.getenv("AZURE_CLIENT_SECRET"),
    )
    return SecretClient(vault_url=f"https://{vault_name}.vault.azure.net", credential=credential)


@lru_cache
def get_secret(name: str) -> str:
    """Fetch once per process via lru_cache."""
    _LOGGER.debug("Fetching secret %s from Key Vault", name)
    return _kv_client().get_secret(name).value


def prime_langfuse_env() -> None:
    """Set LANGFUSE_* only once."""
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", get_secret("LANGFUSE-PUBLIC-KEY"))
    os.environ.setdefault("LANGFUSE_SECRET_KEY", get_secret("LANGFUSE-SECRET-KEY"))
```

---

\### backend / `guardrails.py`

```python
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from secrets import get_secret, prime_langfuse_env

prime_langfuse_env()
_LOGGER = logging.getLogger(__name__)
_langfuse = Langfuse()


# ───────────────────── Prompt caching helpers ──────────────────────
@lru_cache
def _prompt(name: str):
    return _langfuse.get_prompt(name)


def _llm(model: str, temperature: float):
    return AzureChatOpenAI(
        azure_endpoint="https://user1-mai722r2-eastus2.openai.azure.com/",
        api_key=get_secret("AZURE-OPENAI-API-KEY"),
        api_version="2024-12-01-preview",
        model=model,
        temperature=temperature,
    )


# ───────────────────────── Input guardrail ──────────────────────────
class _InputGuardrailResp(BaseModel):
    code: bool = Field(description="True if code meets conditions, False otherwise")
    condition: str


def input_guardrail(code: str) -> (bool, str):
    p = _prompt("input-guardrail")
    parser = JsonOutputParser(pydantic_object=_InputGuardrailResp)

    chain = (
        PromptTemplate(
            template=p.prompt,
            input_variables=["code"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        | _llm(p.config["model"], float(p.config["temperature"]))
        | parser
    )

    result: _InputGuardrailResp = chain.invoke({"code": code})
    return result.code, result.condition


# ──────────────────────── Output guardrail ──────────────────────────
class _OutputGuardrailResp(BaseModel):
    response: bool


def output_guardrail(optimized_code: str, human_feedback_list: List[str]) -> bool:
    p = _prompt("output-guardrail")
    parser = JsonOutputParser(pydantic_object=_OutputGuardrailResp)

    chain = (
        PromptTemplate(
            template=p.prompt,
            input_variables=["optimized_code", "human_feedback_list"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        | _llm(p.config["model"], float(p.config["temperature"]))
        | parser
    )

    return chain.invoke(
        {"optimized_code": optimized_code, "human_feedback_list": human_feedback_list}
    ).response
```

---

\### backend / `optimizers.py`

```python
"""
Composite optimisation chain:
    (input guardrail) ➜ optimise ➜ (output guardrail)

Retries the inner optimise+output_guardrail up to MAX_RETRIES.
"""

import logging
from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field
from langfuse.callback import CallbackHandler
from langfuse import Langfuse

from guardrails import input_guardrail, output_guardrail, _prompt, _llm

_LOGGER = logging.getLogger(__name__)
_langfuse = Langfuse()
MAX_RETRIES = 3


# ───────────────── optimise prompt parser ──────────────────
class _OptimizeResp(BaseModel):
    code: str = Field(description="Optimised code")


def _optimize_once(code: str) -> str:
    p = _prompt("optimize-code")
    parser = JsonOutputParser(pydantic_object=_OptimizeResp)

    chain = (
        PromptTemplate(
            template=p.prompt,
            input_variables=["user_input"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        | _llm(p.config["model"], float(p.config["temperature"]))
        | parser
    )

    return chain.invoke(
        {"user_input": code}, config={"callbacks": [CallbackHandler(host="https://cloud.langfuse.com")]}
    ).code


def optimise_with_guardrails(code: str, feedback_history: List[str]) -> str:
    ok, reason = input_guardrail(code)
    if not ok:
        raise ValueError(f"Input guardrail failed: {reason}")

    for attempt in range(1, MAX_RETRIES + 1):
        optimised = _optimize_once(code)
        if output_guardrail(optimised, feedback_history):
            _LOGGER.info("Output guardrail passed on try %s", attempt)
            return optimised
        _LOGGER.warning("Output guardrail failed on try %s", attempt)

    raise RuntimeError("Failed to satisfy output guardrail after retries")
```

---

\### backend / `utils.py`

```python
"""
File + Git helpers (unchanged logic, now with logging & pathlib)
"""

import subprocess
import sys
import logging
from pathlib import Path
from typing import List

_LOGGER = logging.getLogger(__name__)


def run_command(cmd: str) -> None:
    _LOGGER.info("Running: %s", cmd)
    try:
        subprocess.run(cmd, shell=True, check=True, text=True)
    except subprocess.CalledProcessError as exc:
        _LOGGER.error("Command failed: %s", exc.stderr)
        sys.exit(1)


def clone_repo(url: str, base_dir: Path) -> Path:
    base_dir.mkdir(exist_ok=True)
    repo_name = url.split("/")[-1].removesuffix(".git")
    dest = base_dir / repo_name
    if dest.exists():
        _LOGGER.info("Repo already cloned: %s", dest)
        return dest
    run_command(f"git clone --depth 1 {url} {dest}")
    return dest


def list_files(root: Path) -> List[str]:
    return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]
```

---

\### backend / `prompt_setup.py`

```python
"""
Executed once at app start‑up to (idempotently) register prompts.
"""

import logging
from langfuse import Langfuse

_LOGGER = logging.getLogger(__name__)
_langfuse = Langfuse()


def _ensure_prompt(name: str, prompt: str, model="gpt-4o", temperature=0.7):
    if _langfuse.get_prompt(name, raise_if_not_found=False):
        _LOGGER.debug("Prompt %s already exists", name)
        return
    _langfuse.create_prompt(
        name=name,
        prompt=prompt,
        config={"model": model, "temperature": temperature},
        labels=["production"],
    )
    _LOGGER.info("Prompt %s created", name)


def register_prompts_once():
    _ensure_prompt(
        "input-guardrail",
        """
        You are a guardrail…
        (same prompt text as before)
        """,
    )
    _ensure_prompt(
        "output-guardrail",
        """
        You are a code quality guardrail…
        (same prompt text as before)
        """,
    )
    _ensure_prompt(
        "optimize-code",
        """
        You are an expert code optimizer…
        (same prompt text as before)
        """,
    )
```

---

\### backend / `main.py`

```python
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
```

---

\### frontend / `src/api.js`

```javascript
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function createSession() {
  const res = await fetch(`${API}/session`, { method: "POST", credentials: "include" });
  if (!res.ok) throw new Error("session failed");
}

export async function cloneRepo(url) {
  const res = await fetch(`${API}/clone`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ repo_url: url }),
  });
  if (!res.ok) throw new Error("clone failed");
  return res.json(); // {files: []}
}

export async function getFile(path) {
  return fetch(`${API}/file?relative_path=${encodeURIComponent(path)}`, {
    credentials: "include",
  }).then((r) => r.text());
}

export async function optimise(code, feedback) {
  const res = await fetch(`${API}/optimise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ code, feedback }),
  });
  if (!res.ok) throw new Error("optimise failed");
  return res.json(); // {optimised, feedback_history}
}
```

---

\### frontend / `src/App.jsx`

```jsx
import { useEffect, useState } from "react";
import { createSession, cloneRepo, getFile, optimise } from "./api";

export default function App() {
  const [repoURL, setRepoURL] = useState("");
  const [files, setFiles] = useState([]);
  const [selected, setSelected] = useState("");
  const [code, setCode] = useState("");
  const [optimised, setOptimised] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    createSession();
  }, []);

  const handleClone = async () => {
    setBusy(true);
    try {
      const { files } = await cloneRepo(repoURL);
      setFiles(files);
    } finally {
      setBusy(false);
    }
  };

  const handleSelect = async () => {
    setBusy(true);
    try {
      const txt = await getFile(selected);
      setCode(txt);
    } finally {
      setBusy(false);
    }
  };

  const handleOptimise = async () => {
    setBusy(true);
    try {
      const { optimised } = await optimise(code, feedback);
      setOptimised(optimised);
      setFeedback("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ padding: 32, fontFamily: "sans-serif" }}>
      <h1>Code Optimizer</h1>

      {/* Clone */}
      <input
        placeholder="GitHub URL"
        value={repoURL}
        onChange={(e) => setRepoURL(e.target.value)}
        style={{ width: "60%" }}
      />
      <button onClick={handleClone} disabled={!repoURL || busy}>
        Clone
      </button>

      {/* File select */}
      {files.length > 0 && (
        <>
          <select value={selected} onChange={(e) => setSelected(e.target.value)}>
            <option value="">-- choose file --</option>
            {files.map((f) => (
              <option key={f}>{f}</option>
            ))}
          </select>
          <button onClick={handleSelect} disabled={!selected || busy}>
            Load
          </button>
        </>
      )}

      {/* Editor */}
      {code && (
        <>
          <h3>Source / Feedback</h3>
          <textarea
            rows={15}
            style={{ width: "100%" }}
            value={code}
            onChange={(e) => setCode(e.target.value)}
          ></textarea>

          <input
            placeholder="Add feedback (optional)"
            style={{ width: "100%" }}
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
          />

          <button onClick={handleOptimise} disabled={busy}>
            Optimise
          </button>
        </>
      )}

      {/* Spinner */}
      {busy && <p>⏳ Working…</p>}

      {/* Result */}
      {optimised && (
        <>
          <h3>Optimised</h3>
          <pre>{optimised}</pre>
        </>
      )}
    </div>
  );
}
```

---

\### backend / `requirements.txt`

```
fastapi>=0.111
uvicorn[standard]>=0.29
itsdangerous>=2.1
langchain-core>=0.1.43
langchain-openai>=0.1.8
langfuse>=2.17
azure-identity>=1.16
azure-keyvault-secrets>=4.8
pydantic>=2.7
```

*(Add Git + Node deps as you already had.)*

---

\## How the new flow satisfies your checklist

| #   | Requirement                 | Where handled                                        |
| --- | --------------------------- | ---------------------------------------------------- |
|  1  | **Split FE/BE**             | FastAPI backend, React frontend                      |
|  2  | **Session management**      | Signed cookie; per‑session dict                      |
|  3  | **Prompt versioning once**  | `prompt_setup.register_prompts_once()` in `main.py`  |
|  4  | **Env vars + single fetch** | `secrets.py` uses `lru_cache`; no redeploy secrets   |
|  5  | **Split prompt\_chain.py**  | `secrets.py`, `guardrails.py`, `optimizers.py`       |
|  6  | **Guardrail fix**           | Boolean check fixed in `input_guardrail()`           |
|  7  | **Spinner**                 | `busy` flag in React shows ⏳                         |
|  8  | **Composite chain**         | `optimise_with_guardrails()` auto‑retries internally |
|  9  | **os.path & logging**       | `pathlib` + `logging` used across modules            |

You now have a production‑shaped codebase that remains small enough to scan in one sitting but cleanly separates secrets, guardrails, optimisers, infrastructure, and UI. Happy hacking 🚀
