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


---

© 2025 Blue Data Consulting – All rights reserved.
