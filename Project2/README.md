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
export AOAIKEY=b249ff7055e349c19b9665ff4df191ec   # leave empty to auto‑retrieve later
export LFPUBLIC=pk-lf-172affbb-515f-425c-81b4-ad99d3586f71
export LFSECRET=sk-lf-8f5062a3-4c73-46b8-81a7-a784c561916e
export AZURE_DEPLOYMENT=telcogpt2
export LANGFUSE_HOST=https://cloud.langfuse.com
export AZURE_OPENAI_ENDPOINT=https://swedencentral.api.cognitive.microsoft.com/
export FD=codeopt-fd-$NAME             # must be globally unique
export REGION=centralindia             # adjust if you deployed ACIs elsewhere
export FD_FQDN=${FD}.azurefd.net       # default hostname Front Door will give you

BACKEND_LABEL=codeopt-backend-$NAME
FRONT_LABEL=codeopt-frontend-$NAME
REGION=centralindia
BACKEND_FQDN=${BACKEND_LABEL}.${REGION}.azurecontainer.io
FRONT_FQDN=${FRONT_LABEL}.${REGION}.azurecontainer.io

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
export AZURE_CLIENT_SECRET=Y.k8Q~Dz5nanYAZg7jqzKbOj_VU9T2KEqfP4Bdrh
export AZURE_CLIENT_ID=cc8f42c4-5f99-417b-b833-3bc39649cf4a
export AZURE_TENANT_ID=0d2a6053-e113-42e7-9169-f5cbed7a941f
export AZURE_DEPLOYMENT=telcogpt2
export LANGFUSE_HOST=https://cloud.langfuse.com
export AZURE_OPENAI_ENDPOINT=https://swedencentral.api.cognitive.microsoft.com/
# Cookie signing secret
#export SESSION_SECRET=$(openssl rand -hex 16)
# Local React app points to the backend
export VITE_API_URL=http://localhost:8000
```

#### Backend: FastAPI ServerLaunch the backend service
```bash
# Launch the backend service
cd code-optimizer/backend
export $(grep -v '^#' .env | xargs)
  uvicorn main:app --reload --port 8000

```

# testing the backend

1. Navigate to http:127.0.0.1:8000/docs
2. this launches swagger test interface to test each API, fill the input argument accordingly to test each service

Docs:


#### Frontend: React-Vite dev server

Open **another terminal** (leave the backend running):

```bash
cd code-optimizer/frontend
sudo apt install nodejs npm  # enter the user VM password (Cloud.....)
npm install          # first time only
npm run dev          # Vite dev server → http://localhost:5173
```

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
sudo docker run -d -p 8000:8000 -e AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET -e VAULT_NAME=$VAULT_NAME -e AZURE_CLIENT_ID=$AZURE_CLIENT_ID -e AZURE_TENANT_ID=$AZURE_TENANT_ID -e SESSION_SECRET=$(openssl rand -hex 16) -e AZURE_DEPLOYMENT=$AZURE_DEPLOYMENT -e LANGFUSE_HOST=$LANGFUSE_HOST -e AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT -e COOKIE_SECURE=false -e ALLOWED_ORIGINS=http://localhost:8080 $IMG-backend:latest 

# Test the backend using swagger by navigating to http:!27.0.0.1:8000/docs

sudo docker tag $IMG-backend:latest $ACR.azurecr.io/$IMG-backend:latest
sudo docker push $ACR.azurecr.io/$IMG-backend:latest

# FRONTEND
# make sure to navigate to code-optimizer folder 
sudo docker build -f frontend.Dockerfile \
  --build-arg BACKEND_HOST=localhost \
  -t $IMG-frontend:latest .


sudo docker run -d -p 8080:80 $IMG-frontend:latest

```



```bash
# BACKEND ACI
az container create -g $RG -n ${ACI}-backend \
  --image $ACR.azurecr.io/$IMG-backend:latest \
  --registry-login-server $ACR.azurecr.io \
  --registry-username $(az acr credential show -n $ACR --query username -o tsv) \
  --registry-password $(az acr credential show -n $ACR --query passwords[0].value -o tsv) \
  --cpu 1 --memory 2 --os-type Linux --ip-address public \
  --dns-name-label $BACKEND_LABEL \
  --ports 8000 \
  --environment-variables \
      VAULT_NAME=$VAULT_NAME \
      ALLOWED_ORIGINS=http://$FRONT_FQDN \
      AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
      AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
      AZURE_TENANT_ID=$AZURE_TENANT_ID \
      AZURE_DEPLOYMENT=$AZURE_DEPLOYMENT \
      LANGFUSE_HOST=$LANGFUSE_HOST \
      AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT
      SESSION_SECRET=$(openssl rand -hex 16) \


# check list of containers
az container list -g $RG -o table


# check FQDN and ensure it is same as BACKEND_FQDN
az container show -g $RG -n ${ACI}-backend \
  --query "ipAddress.{fqdn:fqdn,ip:ip,ports:ports}" -o table


# rebuild docker image with new env variable
sudo docker build -f frontend.Dockerfile \
-t $ACR.azurecr.io/$IMG-frontend:latest \
--build-arg API_URL=http://$BACKEND_FQDN:8000 .


sudo docker push $ACR.azurecr.io/$IMG-frontend:latest
# FRONTEND ACI
az container create -g $RG -n ${ACI}-frontend \
  --image $ACR.azurecr.io/$IMG-frontend:latest \
  --registry-login-server $ACR.azurecr.io \
  --registry-username $(az acr credential show -n $ACR --query username -o tsv) \
  --registry-password $(az acr credential show -n $ACR --query passwords[0].value -o tsv) \
  --cpu 1 --memory 2 --os-type Linux --ip-address public \
  --dns-name-label $FRONT_LABEL \
  --ports 80 

```
# check list of containers
az container list -g $RG -o table


# check FQDN and ensure it is same as FRONTEND_FQDN
az container show -g $RG -n ${ACI}-frontend \
  --query "ipAddress.{fqdn:fqdn,ip:ip,ports:ports}" -o table


# ------------------------------------------------------------------
# 7.  Delete and Clean the deployments 
# ------------------------------------------------------------------

# delete the container instance
az container delete -g $RG -n ${ACI}-frontend --yes
az container delete -g $RG -n ${ACI}-backend --yes

# delete the container registry
az acr delete -g $RG -n $ACR --yes


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


FRONT=http://codeopt-frontend-anshu.centralindia.azurecontainer.io
BACK=http://codeopt-backend-anshu.centralindia.azurecontainer.io:8000

# 1) From your laptop check CORS headers
curl -I -X POST $BACK/session -H "Origin: $FRONT"
# Expect:
# HTTP/1.1 200 OK
# access-control-allow-origin: http://codeopt-frontend-anshu.centralindia.azurecontainer.io
# access-control-allow-credentials: true
# set-cookie: session=...

# 2) OPTIONS pre-flight
curl -I -X OPTIONS $BACK/clone -H "Origin: $FRONT" -H "Access-Control-Request-Method: POST"
# Expect 204/200 with the two CORS headers



Below is an **end-to-end “Front Door + cookie” recipe** that brings you back to
the **original cookie workflow** while making it work from *any* browser,
because all traffic now comes from a **single HTTPS origin** served by
**Azure Front Door Standard**.

---


*(keep the generic `@app.options` 204 handler you added earlier)*

Re-build & push the backend image (`backend:v-cookie`) and redeploy the ACI:

```bash
az container delete -g $RG -n $BACK_LABEL --yes
az container create -g $RG -n $BACK_LABEL \
  --image $ACR.azurecr.io/$IMG-backend:v-cookie \
  --registry-login-server $ACR.azurecr.io \
  --cpu 1 --memory 2 --ports 8000 \
  --dns-name-label $BACK_LABEL \
  --environment-variables \
     ALLOWED_ORIGINS=https://$FD_FQDN \
     BDC_VAULT_NAME=$VAULT \
     AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
     AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
     AZURE_TENANT_ID=$AZURE_TENANT_ID \
     SESSION_SECRET=$SESSION_SECRET
```

---

## 2  Restore the **frontend** to cookie calls

`src/api.js` (original style)

```js
const API = import.meta.env.VITE_API_URL || "/api";   // ← we’ll proxy /api

export async function createSession() {
  await fetch(`${API}/session`, { method: "POST", credentials: "include" });
}

export async function cloneRepo(url) {
  const res = await fetch(`${API}/clone`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ repo_url: url }),
  });
  if (!res.ok) throw new Error("clone failed");
  return res.json();
}

/* getFile and optimise identical, keep credentials:"include" */
```

### Frontend Dockerfile (proxy `/api` → backend)

```dockerfile
# frontend.Dockerfile
FROM node:20-alpine AS build
ARG API_URL=/api                     # placeholder but not used at runtime
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ .
RUN npm run build                    # dist/

FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html

# proxy /api/* to the backend ACI
RUN printf 'location /api/ {\n  proxy_pass http://%s:8000/;\n  proxy_set_header Host $host;\n}\n' ${BACK_FQDN} \
    > /etc/nginx/conf.d/api_proxy.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Build & push:

```bash
docker build -f frontend.Dockerfile \
  -t $ACR.azurecr.io/$IMG-frontend:v-cookie .
docker push $ACR.azurecr.io/$IMG-frontend:v-cookie
```

Redeploy the front-end ACI:

```bash
az container delete -g $RG -n $FRONT_LABEL --yes
az container create -g $RG -n $FRONT_LABEL \
  --image $ACR.azurecr.io/$IMG-frontend:v-cookie \
  --registry-login-server $ACR.azurecr.io \
  --cpu 1 --memory 1 --ports 80 \
  --dns-name-label $FRONT_LABEL
```

---

## 3  Create **Azure Front Door Standard**

```bash
az network front-door profile create -g $RG -n $FD --sku Standard_AzureFrontDoor

# 3.1  origin groups
az network front-door origin-group create -g $RG --profile-name $FD \
  -n spa-group --probe-request-type GET --probe-protocol Http --probe-path /
az network front-door origin-group create -g $RG --profile-name $FD \
  -n api-group --probe-request-type GET --probe-protocol Http --probe-path /session

# 3.2  origins
az network front-door origin create -g $RG --profile-name $FD \
  --origin-group spa-group -n spaOrigin \
  --host-name $FRONT_FQDN --origin-host-header $FRONT_FQDN --priority 1 --weight 100 --http-port 80
az network front-door origin create -g $RG --profile-name $FD \
  --origin-group api-group -n apiOrigin \
  --host-name $BACK_FQDN --origin-host-header $BACK_FQDN --priority 1 --weight 100 --http-port 8000

# 3.3  routes
az network front-door route create -g $RG --profile-name $FD \
  -n spaRoute --endpoint-name default \
  --origin-group spa-group \
  --frontend-endpoints default \
  --https-redirect Enabled \
  --patterns "/" "/*"
az network front-door route create -g $RG --profile-name $FD \
  -n apiRoute --endpoint-name default \
  --origin-group api-group \
  --frontend-endpoints default \
  --https-redirect Enabled \
  --patterns "/api/*"

# Front Door generates an SSL cert automatically for *.azurefd.net
```

**Wait 3-5 min** for Front Door to propagate.

Your public URL is now

```
https://codeopt-fd-anshu.azurefd.net
```

*(You can later add a custom domain + free Front Door cert.)*

---

## 4  Test end-to-end

1. Open **[https://codeopt-fd-anshu.azurefd.net](https://codeopt-fd-anshu.azurefd.net)**
   The SPA loads.

2. Open DevTools ▸ Network

   * `POST https://codeopt-fd-anshu.azurefd.net/api/session` → **200**
     Browser stores **`session=…; SameSite=None; Secure`**
   * `POST https://codeopt-fd-anshu.azurefd.net/api/clone` → **200**
     File list appears.

3. Swagger (optional) — now lives at
   `https://codeopt-fd-anshu.azurefd.net/api/docs`

---

## 5  Cost & cleanup

* **Front Door Standard** – base ≈ ₹2.2 /hour (`$0.032`), plus data.
* **Turn off** ACIs and the FD profile when you finish testing:

```bash
az container delete -g $RG -n $FRONT_LABEL --yes
az container delete -g $RG -n $BACK_LABEL  --yes
az network front-door profile delete -g $RG -n $FD --yes
```

---

### You now have

* One HTTPS origin (`*.azurefd.net`)
* Original cookie-based session (SameSite=None; Secure)
* No CORS headaches (Front Door handles host/port)
* Minimal infra — two ACIs + Front Door

You can roll this pattern into CI/CD or swap ACIs for AKS/Apps later
without touching the cookie logic again.