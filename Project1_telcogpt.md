# TelcoGPT – Prompt‑Only Telecom Q\&A Assistant

> **Version 1.0** · MAY 2025

> Lean Flask application that wraps an Azure OpenAI GPT‑4o deployment and responds in telecom‑specific “card” layouts.

---

## 1 Project Overview

TelcoGPT delivers instant, domain‑accurate answers for network engineers and support teams without maintaining an external knowledge base. It relies purely on **prompt engineering**, three fixed answer templates (Definition / Troubleshooting / Design Recommendation), and a minimal Python Flask backend.

* **Language model:** *Azure OpenAI GPT‑4o mini* (2024‑07‑18).
* **Backend:** Flask 3.x with Redis (optional, for chat history).
* **Frontend:** Single‑page Bootstrap chat UI.

---

## 2 Prerequisites

| Requirement            | Notes                                                |
| ---------------------- | ---------------------------------------------------- |
| **Azure subscription** | Contributor rights to create Cognitive resources.    |
| **Local tooling**      | `az CLI`, `git`, `python 3.11+`, `pip`, `jq`.        |
| **OS**                 | Linux, macOS, or Windows 10+ with WSL‑2 recommended. |

---

## 3 Provision Azure OpenAI Resources

Execute the following **once**; substitute your own names where indicated:

```bash
# ✧ Login ✧
az login                       # interactive browser auth

# ✧ Create the Cognitive account ✧
az cognitiveservices account create \
    --name <myResourceName> \
    --resource-group Tredence-Batch2 \
    --location eastus \
    --kind OpenAI \
    --sku s0

# ✧ Fetch the endpoint URL ✧
az cognitiveservices account show \
    --name <myResourceName> \
    --resource-group Tredence-Batch2 \
  | jq -r .properties.endpoint

# ✧ Fetch the primary key ✧
az cognitiveservices account keys list \
    --name <myResourceName> \
    --resource-group Tredence-Batch2 \
  | jq -r .key1

# ✧ Deploy the GPT‑4o mini model ✧
az cognitiveservices account deployment create \
    --name <myResourceName> \
    --resource-group Tredence_Batch2 \
    --deployment-name telcogpt \
    --model-name gpt-4o-mini \
    --model-version "2024-07-18" \
    --model-format OpenAI \
    --sku-capacity 1 \
    --sku-name Standard
```

> **Considerations**
>
> * **Quota:** A Standard SKU provides 1 compute unit; API requests above the quota will be throttled.
> * **Naming rules:** Resource names must be globally unique and 2–24 characters.
> * **Azure CLI vs PowerShell:** The above commands run in Bash or PowerShell Core. Ensure `jq` is installed for JSON parsing.

---

## 4 Local Environment Setup

```bash
# 1 Navigate (example path)
cd ~/Desktop/TelcoGPT

# 2 Create a Python virtual‑env
python -m venv gen-ai && source gen-ai/bin/activate

# 3 Create folders & install deps
mkdir -p app/static app/templates prompts
pip install flask redis openai pytest

# 4 Create placeholder source files
 touch app/__init__.py app/routes.py app/cards.py \
       app/prompt_builder.py app/validator.py

# 5 Create the system prompt
 touch prompts/system_prompt.txt           # note: correct folder spelling!
```

Paste the code snippets from the *docs* section into the corresponding files (or clone the repo if you already pushed it to GitHub).

### Environment Variables

Create a `.env` or export the following before running Flask:

```bash
export AZURE_OPENAI_ENDPOINT="https://<myResourceName>.openai.azure.com/"
export AZURE_OPENAI_API_KEY="<primary‑key>"
export OPENAI_DEPLOYMENT="telcogpt"            # deployment name above
# (Optional) Redis
export REDIS_URL="redis://localhost:6379"
```

---

## 5 Running the App Locally

```bash
flask --app app run               # defaults to http://127.0.0.1:5000
```

Visit [http://127.0.0.1:5000/](http://127.0.0.1:5000/) to open the chat UI. Test with:

```bash
curl -s http://127.0.0.1:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"error code P0610 on eNB 410"}' | jq .
```

Expected JSON response contains five numbered bullets under the *Troubleshooting* card layout.

---

## 6 Running the Test Suite

```bash
pytest -q               # filesystem + mocked OpenAI tests
pytest -q -m live       # optional: hits the real endpoint
```

---

## 7 Next Steps

* **Dockerise** the app using the provided `Dockerfile` (`docker build -t telcogpt:latest .`).
* **Deploy** to an Azure VM or App Service.
* **Hard‑code** your prompt templates or move to a prompt‑registry for multi‑persona support.

---

## 8 Troubleshooting

| Symptom                             | Likely Cause & Fix                                                                         |
| ----------------------------------- | ------------------------------------------------------------------------------------------ |
| `UnicodeDecodeError` reading prompt | Save `prompts/system_prompt.txt` with UTF‑8 and specify `encoding="utf-8"` in loader.      |
| `TemplateNotFound: chat.html`       | Ensure `chat.html` lives in `app/templates/` *or* pass the correct `template_folder=` arg. |
| 403 / throttling errors from OpenAI | Deployment not in *East US* or quota exhausted; check Azure portal usage graphs.           |

---

© 2025 Blue Data Consulting – All rights reserved.
