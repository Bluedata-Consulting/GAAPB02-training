# Code Optimizer Assistant — FastAPI + React

A two‑tier web application that

1. Clones any public GitHub repo
2. Lets you view / edit a file, add plain‑English feedback
3. Runs a composite LangChain pipeline—`input_guardrail ➜ optimizer ➜ output_guardrail`—on Azure GPT‑4o
4. Tracks prompts & traces in **Langfuse**
5. Persists no secrets in code: all credentials live in **Azure Key Vault** and are injected at runtime

---

<img src=".\figures\Project21.png" alt="Project 2" width="900"/>
<img src=".\figures\Project22.png" alt="Project 2" width="900"/>


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
touch code-optimizer/backend/{main.py,prompt_setup.py,kvsecrets.py,guardrails.py,optimizers.py,utils.py,requirements.txt,backend.Dockerfile}

# 2) front‑end tree  ──────────────────────────────────────────────
mkdir -p code-optimizer/frontend/src && \
touch code-optimizer/frontend/{package.json,frontend.Dockerfile} code-optimizer/frontend/src/{api.js,App.jsx}

```

---

\## 🚀 Resource provisioning (once)

\### 0 Login to Azure & create variables

```bash
az login
```

```bash

# personalise
export NAME=anshu
export RG=Tredence-Batch2
export LOC=eastus2              # choose any supported region

export VAULT=vault$NAME
export SP=sp$NAME
export ACR=codeacr$NAME
export ACI=aci$NAME
export IMG=img$NAME

export AOAI=${NAME}aoai         # Azure OpenAI resource name

# (OPTIONAL) if you already have the keys:
export AOAIKEY=b249ff7055e349c19b9665ff4df191ec   # leave empty to auto‑retrieve later
export LFPUBLIC=pk-lf-172affbb-515f-425c-81b4-ad99d3586f71
export LFSECRET=sk-lf-8f5062a3-4c73-46b8-81a7-a784c561916e
export AZURE_DEPLOYMENT=telcogpt2
export LANGFUSE_HOST=https://cloud.langfuse.com
export AZURE_OPENAI_ENDPOINT=https://swedencentral.api.cognitive.microsoft.com/
```



---

\## 1 Key Vault + secrets

```bash
az keyvault create -g $RG -n $VAULT --enable-rbac-authorization true

# place Langfuse keys now so later code can start up immediately
az keyvault secret set -n LANGFUSE-PUBLIC-KEY --vault-name $VAULT --value $LFPUBLIC
az keyvault secret set -n LANGFUSE-SECRET-KEY --vault-name $VAULT --value $LFSECRET
az keyvault secret set -n AZURE-OPENAI-API-KEY --vault-name $VAULT --value $AOAIKEY

```

---

\## 2 Service principal (Key Vault → Secrets User)

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


---
\## 3 Test the applicaiton locally

```bash
#export following env variables
export VAULT_NAME=$VAULT
export AZURE_CLIENT_SECRET=Bbw8Q~rOIZ4UlfPzXaOsiYa1Z1GY1kYSm-niodq5
export AZURE_CLIENT_ID=cc8f42c4-5f99-417b-b833-3bc39649cf4a
export AZURE_TENANT_ID=0d2a6053-e113-42e7-9169-f5cbed7a941f
export SESSION_SECRET=$(openssl rand -hex 16)
export AZURE_DEPLOYMENT=telcogpt2
export LANGFUSE_HOST=https://cloud.langfuse.com
export AZURE_OPENAI_ENDPOINT=https://swedencentral.api.cognitive.microsoft.com/

  uvicorn main:app --reload --port 8000

Below is the quickest repeatable way to spin up **both tiers on your laptop** (Ubuntu 20 / 22; similar on macOS).

```
code-optimizer/
│
├── backend/               # FastAPI sources + requirements.txt
└── frontend/              # React-Vite sources + package.json
```

---

## 1 Prereqs

| Layer        | Tool version (min) | Install (Ubuntu)                                                                             |                                               |
| ------------ | ------------------ | -------------------------------------------------------------------------------------------- | --------------------------------------------- |
| **Backend**  | Python 3.10+       | `sudo apt install python3.10 python3.10-venv`                                                |                                               |
| **Frontend** | Node 18+ & npm     | \`curl -fsSL [https://deb.nodesource.com/setup\_18.x](https://deb.nodesource.com/setup_18.x) | sudo -E bash -`<br>`sudo apt install nodejs\` |

---

## 2 Environment variables

Create a **`.env`** file in the project root (never commit it):

```bash
# Key Vault lookup for creds
BDC_VAULT_NAME=BDCvault

# Service-principal creds (from sp.json)
AZURE_CLIENT_ID=xxxxxxxx-...
AZURE_CLIENT_SECRET=xxxxxxxx-...
AZURE_TENANT_ID=xxxxxxxx-...

# Cookie signing secret
SESSION_SECRET=$(openssl rand -hex 16)

# Local React app points to the backend
VITE_API_URL=http://localhost:8000
```

Load it in every new shell:

```bash
export $(grep -v '^#' .env | xargs)
```

*(a helper like `direnv` or `dotenv-linter` can automate this)*

---

## 3 Backend: FastAPI + Uvicorn

```bash
cd code-optimizer/backend

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# run
uvicorn main:app --reload --port 8000
```

* `--reload` auto-restarts on file changes.
* The startup log should show “Application startup complete.” and no Key Vault errors.

---

## 4 Frontend: React-Vite dev server

Open **another terminal** (leave the backend running):

```bash
cd code-optimizer/frontend
sudo apt install npm  # enter the user VM password (Cloud.....)
npm install          # first time only
npm run dev          # Vite dev server → http://localhost:5173
```

Vite prints something like:

```
> Local: http://localhost:5173/
```

---

## 5 Open the app

Navigate to **[http://localhost:5173](http://localhost:5173)** in a browser:

1. Paste a public GitHub repo URL → **Clone**
2. Choose a file → **Load**
3. Click **Optimise** to hit the backend at `http://localhost:8000`.

⚠️  If you get CORS errors in the browser console, verify:

* Backend is reachable at the URL in `VITE_API_URL`.
* React dev server and backend run on different ports (5173 vs 8000).

---

## 6 Optional: run both in one command

If you like a single process, install the **`task`** runner or **`concurrently`**:

```bash
# root/package.json (add dev script)
{
  "scripts": {
    "dev": "concurrently \"npm --prefix frontend run dev\" \"bash -c 'cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000'\""
  },
  "devDependencies": { "concurrently": "^8.2.0" }
}

npm install --save-dev concurrently
npm run dev      # starts both servers together
```

---

### Quick sanity checks

| URL                                             | Expect                       |
| ----------------------------------------------- | ---------------------------- |
| `http://localhost:8000/docs`                    | FastAPI Swagger UI           |
| `curl -X POST http://localhost:8000/session`    | 200 with `Set-Cookie` header |
| `npm run test` (if you saved `backend_test.py`) | All ✅                        |

You now have the **backend and frontend running locally** with hot-reload; edit any Python or React file and the browser refreshes automatically.

```

---

\## 4 Container Registry

```bash
az acr create -g $RG -n $ACR --sku Basic
az acr update -n $ACR --admin-enabled true
sudo az acr login -n $ACR -u $(az acr credential show -n $ACR --query username -o tsv) \
  -p $(az acr credential show -n $ACR --query passwords[0].value -o tsv)


# if asked for password for user, enter the VM password
```

---

\## 5 Docker build & push

```bash
# BACKEND
docker build -f backend.Dockerfile \
  -t $IMG-backend:latest ./code-optimizer/backend
docker tag $IMG-backend:latest $ACR.azurecr.io/$IMG-backend:latest
docker push $ACR.azurecr.io/$IMG-backend:latest

# FRONTEND
docker build -f frontend.Dockerfile \
  -t $IMG-frontend:latest ./code-optimizer/frontend
docker tag $IMG-frontend:latest $ACR.azurecr.io/$IMG-frontend:latest
docker push $ACR.azurecr.io/$IMG-frontend:latest
```

---

\## 6 Container Instances

```bash
# BACKEND ACI
az container create -g $RG -n ${ACI}-backend \
  --image $ACR.azurecr.io/$IMG-backend:latest \
  --registry-login-server $ACR.azurecr.io \
  --cpu 1 --memory 2 \
  --environment-variables \
      BDC_VAULT_NAME=$VAULT \
      $(jq -r '"AZURE_CLIENT_ID="+.clientId'       sp.json) \
      $(jq -r '"AZURE_CLIENT_SECRET="+.clientSecret' sp.json) \
      $(jq -r '"AZURE_TENANT_ID="+.tenantId'       sp.json) \
      SESSION_SECRET=$(openssl rand -hex 16) \
  --dns-name-label ${ACI}-backend-$RANDOM \
  --ports 8000

BACKEND_FQDN=$(az container show -g $RG -n ${ACI}-backend \
               --query ipAddress.fqdn -o tsv)

# FRONTEND ACI
az container create -g $RG -n ${ACI}-frontend \
  --image $ACR.azurecr.io/$IMG-frontend:latest \
  --registry-login-server $ACR.azurecr.io \
  --cpu 1 --memory 1 \
  --environment-variables VITE_API_URL=http://$BACKEND_FQDN:8000 \
  --dns-name-label ${ACI}-frontend-$RANDOM \
  --ports 80
```

Retrieve the public URL:

```bash
az container show -g $RG -n ${ACI}-frontend --query ipAddress.fqdn -o tsv
```

---

\## 7 Azure OpenAI resource + model deployment

\### 7.1 Create the AOAI account

```bash
az cognitiveservices account create \
  -g $RG -n $AOAI -l $LOC \
  --kind OpenAI --sku S0 \
  --yes
```

\### 7.2 Get / store the API key

```bash
if [ -z "$AOAIKEY" ]; then
  AOAIKEY=$(az cognitiveservices account keys list -g $RG -n $AOAI --query key1 -o tsv)
fi

az keyvault secret set --vault-name $VAULT -n "AZURE-OPENAI-API-KEY" --value "$AOAIKEY"
```

\### 7.3 Deploy a model (e.g., GPT‑4o with deployment name `gpt4o`)

> **Important:** You must have been granted OpenAI model access in the Azure portal first.

```bash
az cognitiveservices account deployment create \
  -g $RG -n $AOAI \
  --deployment-name gpt4o \
  --model-name gpt-4o \
  --model-version "2024-05-13" \
  --model-format OpenAI \
  --scale-settings scale-type="Standard"
```

After the deployment status shows **succeeded**, the backend can hit:

```
https://$AOAI.openai.azure.com/openai/deployments/gpt4o/chat/completions?api-version=2024-02-15-preview
```

> The backend code already targets that endpoint (`azure_endpoint="https://user1-mai722r2-eastus2.openai.azure.com/"`).
> Replace that string in `guardrails.py` / `optimizers.py` with your newly created endpoint URL (`https://$AOAI.openai.azure.com/`).

---

\## Done 🎉

You now have:

* Key Vault `$VAULT` holding **AOAI key + Langfuse keys**
* Service principal `$SP` with “Secrets User” rights
* Docker images in ACR `$ACR`
* Frontend & backend running as **Azure Container Instances** under the `$ACI-*` names
* **Azure OpenAI** resource `$AOAI` with a GPT‑4o deployment named `gpt4o` ready for low‑latency chat completions.




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


