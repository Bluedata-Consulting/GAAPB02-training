#!/bin/bash
export AZURE_OPENAI_API_KEY=$(az keyvault secret show --name AZURE-OPENAI-API-KEY --vault-name $KV_NAME --query value -o tsv)
export AZURE_OPENAI_ENDPOINT=$(az keyvault secret show --name AZURE-OPENAI-ENDPOINT --vault-name $KV_NAME --query value -o tsv)
exec /weaviate
