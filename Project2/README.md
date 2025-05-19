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
export VAULT=vault$NAME
export SP=sp$NAME
export ACR=codeacr$NAME
export ACI=aci$NAME
export IMG=img$NAME

# (OPTIONAL) if you already have the keys:
export AOAIKEY=xxxxxxxxxxxxxxxx
export LFPUBLIC=pxxxxxxxxxxx
export LFSECRET=sxxxxxxxxxxxxxxxxxxxx
export AZURE_DEPLOYMENT=telcogpt2
export LANGFUSE_HOST=https://cloud.langfuse.com
export AZURE_OPENAI_ENDPOINT=https://swedencentral.api.cognitive.microsoft.com/
export REGION=centralindia
export SESSION_SECRET=$(openssl rand -base64 32)
export RUNNING_IN_AZURE=False
export COOKIE_SECURE=False

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

Above command exports a json file sp.json. The JSON looks like:

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
export AZURE_CLIENT_SECRET=xxxxxxxxxxxxxxx
export AZURE_CLIENT_ID=xxxxxxxxxxxxxx
export AZURE_TENANT_ID=xxxxxxxxxxxxxx
# Cookie signing secret
#export SESSION_SECRET=$(openssl rand -hex 16)
# Local React app points to the backend
export VITE_API_URL=http://localhost:8000
```

#### Backend: FastAPI ServerLaunch the backend service
```bash
# Launch the backend service locally
cd Project2/code-optimizer/backend
uvicorn main:app --reload --port 8000

```

# testing the backend

1. Navigate to http:127.0.0.1:8000/docs
2. this launches swagger test interface to test each API, fill the input argument accordingly to test each service

Docs:


#### Frontend: React-Vite dev server

Open **another terminal** (leave the backend running):

```bash
cd Project2/code-optimizer/frontend
sudo apt install nodejs npm  # enter the user VM password (Cloud.....)
# delete the folder frontend/node_modules
npm install          # first time only
npm run dev          # Vite dev server → http://localhost:5173
```
demo repo for test : https://github.com/anshupandey/mlops-ey25
Vite prints something like:

```
> Local: http://localhost:5173/
```

---


Navigate to **[http://localhost:5173](http://localhost:5173)** in a browser:

1. Paste a public GitHub repo URL → **Clone** 
2. Choose a file → **Load**
3. Click **Optimise** to hit the backend at `http://localhost:8000`.

⚠️  If you get CORS errors in the browser console, verify:

* Backend is reachable at the URL in `VITE_API_URL`.
* React dev server and backend run on different ports (5173 vs 8000).

---

### Quick sanity checks

| URL                                             | Expect                       |
| ----------------------------------------------- | ---------------------------- |
| `http://localhost:8000/docs`                    | FastAPI Swagger UI           |
| `curl -X POST http://localhost:8000/session`    | 200 with `Set-Cookie` header |
| `npm run test` (if you saved `backend_test.py`) | All ✅                        |

You now have the **backend and frontend running locally** with hot-reload; edit any Python or React file and the browser refreshes automatically.


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
# BACKEND: build the docker image
# make sure to run this command from code-optimizer directory
sudo docker build -f backend.Dockerfile \
  -t $IMG-backend:latest .

# optional: Run the docker containerr locally
sudo docker run -d -p 8000:8000 -e AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET -e VAULT_NAME=$VAULT_NAME -e AZURE_CLIENT_ID=$AZURE_CLIENT_ID -e AZURE_TENANT_ID=$AZURE_TENANT_ID -e SESSION_SECRET=$(openssl rand -hex 16) -e AZURE_DEPLOYMENT=$AZURE_DEPLOYMENT -e RUNNING_IN_AZURE=$RUNNING_IN_AZURE -e LANGFUSE_HOST=$LANGFUSE_HOST -e AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT -e COOKIE_SECURE=false -e ALLOWED_ORIGINS=http://localhost:8080 $IMG-backend:latest

# Test the backend using swagger by navigating to http:!27.0.0.1:8000/docs

sudo docker tag $IMG-backend:latest $ACR.azurecr.io/$IMG-backend:latest
sudo docker push $ACR.azurecr.io/$IMG-backend:latest

# FRONTEND
# make sure to navigate to code-optimizer folder 
sudo docker build -f frontend.Dockerfile \
  --build-arg BACKEND_HOST=localhost \
  -t $IMG-frontend:latest .


sudo docker run -d -p 8080:80 --add-host=host.docker.internal:host-gateway \
-e BACKEND_URL=http://host.docker.internal:8000 \
 $IMG-frontend:latest


sudo docker tag $IMG-frontend:latest $ACR.azurecr.io/$IMG-frontend:latest
sudo docker push $ACR.azurecr.io/$IMG-frontend:latest

```



```bash

ACR_USERNAME=$(az acr credential show --name $ACR$ --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR$ --query "passwords[0].value" -o tsv)
export SESSION_SECRET=$(openssl rand -base64 32)
export RUNNING_IN_AZURE=True
export COOKIE_SECURE=True
export TAG=latest
export DNS_LABEL=codeopt-app
export LOCATION=centralindia
export ALLOWED_ORIGINS=http://$DNS_LABEL.$LOCATION.azurecontainer.io,http://localhost

# Generate aci config file: contianer-group.yaml
# navigate to the project2 directory
python generate-aci-config.py

az container create -g $RG --file container-group.yaml

# check list of containers
az container list -g $RG -o table


# check FQDN and ensure it is same as BACKEND_FQDN
az container show -g $RG -n ${ACI}-group \
  --query "ipAddress.{fqdn:fqdn,ip:ip,ports:ports}" -o table


```
# ------------------------------------------------------------------
# 7.  Delete and Clean the deployments 
# ------------------------------------------------------------------

# delete the container instance
az container delete -g $RG -n ${ACI}-group --yes

# delete the container registry
az acr delete -g $RG -n $ACR --yes

# delete the key vault
az keyvault delete --name $VAULT_NAME -g $RG

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
