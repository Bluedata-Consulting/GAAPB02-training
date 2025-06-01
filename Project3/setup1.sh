#!/bin/bash

# Variables
NAME=anshu
RG=Tredence-Batch2
LOCATION=eastus2
AZURE_OPENAI_RESOURCE="$NAME-openai"
AZURE_OPENAI_MODEL="text-embedding-ada-002"
KV_NAME="$NAME-kv"
ACI_NAME="$NAME-weaviate"
IDENTITY_NAME="$NAME-weaviate-identity"
ACR_NAME="$NAME-acr"
CONTAINER_IMAGE="$ACR_NAME.azurecr.io/weaviate-custom"

# Create Azure OpenAI resource
echo "Creating Azure OpenAI resource..."
az cognitiveservices account create \
  --name $AZURE_OPENAI_RESOURCE \
  --resource-group $RG \
  --kind OpenAI \
  --sku S0 \
  --location $LOCATION \
  --yes

# Deploy embedding model
echo "Deploying embedding model..."
az cognitiveservices account deployment create \
  --resource-group $RG \
  --name $AZURE_OPENAI_RESOURCE \
  --deployment-name $AZURE_OPENAI_MODEL \
  --model-name text-embedding-ada-002 \
  --model-version 2 \
  --model-format OpenAI \
  --sku-name Standard \
  --scale-type Standard

# Get OpenAI endpoint and key
ENDPOINT=$(az cognitiveservices account show --name $AZURE_OPENAI_RESOURCE --resource-group $RG --query "properties.endpoint" -o tsv)
API_KEY=$(az cognitiveservices account keys list --name $AZURE_OPENAI_RESOURCE --resource-group $RG --query key1 -o tsv)

# Create Key Vault
echo "Creating Key Vault..."
az keyvault create --name $KV_NAME --resource-group $RG --location $LOCATION
az keyvault secret set --vault-name $KV_NAME --name "AZURE-OPENAI-ENDPOINT" --value "$ENDPOINT"
az keyvault secret set --vault-name $KV_NAME --name "AZURE-OPENAI-API-KEY" --value "$API_KEY"

# Create ACR
echo "Creating Azure Container Registry (ACR)..."
az acr create --resource-group $RG --name $ACR_NAME --sku Basic --location $LOCATION
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --resource-group $RG --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --resource-group $RG --query "passwords[0].value" -o tsv)
echo "$ACR_PASSWORD" | docker login "$ACR_NAME.azurecr.io" --username "$ACR_USERNAME" --password-stdin


# Create managed identity for ACI
echo "Creating managed identity..."
az identity create --name $IDENTITY_NAME --resource-group $RG --location $LOCATION
IDENTITY_PRINCIPAL_ID=$(az identity show --name $IDENTITY_NAME --resource-group $RG --query 'principalId' -o tsv)
IDENTITY_ID=$(az identity show --name $IDENTITY_NAME --resource-group $RG --query 'id' -o tsv)

# Set Key Vault policy to allow identity to access secrets
az keyvault set-policy --name $KV_NAME --object-id $IDENTITY_PRINCIPAL_ID --secret-permissions get list

# Create Dockerfile
echo "Creating Dockerfile..."
cat <<EOF > Dockerfile
FROM weaviate/weaviate:latest
RUN apt-get update && apt-get install -y curl apt-transport-https lsb-release gnupg && \
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
EOF

# Create entrypoint.sh
echo "Creating entrypoint.sh..."
cat <<'EOF' > entrypoint.sh
#!/bin/bash
export AZURE_OPENAI_API_KEY=$(az keyvault secret show --name AZURE-OPENAI-API-KEY --vault-name $KV_NAME --query value -o tsv)
export AZURE_OPENAI_ENDPOINT=$(az keyvault secret show --name AZURE-OPENAI-ENDPOINT --vault-name $KV_NAME --query value -o tsv)
exec /weaviate
EOF

# Build Docker image
echo "Building Docker image..."
docker build -t $CONTAINER_IMAGE .

# Push Docker image to ACR
echo "Pushing Docker image to ACR..."
docker push $CONTAINER_IMAGE

# Deploy ACI
echo "Deploying ACI with Weaviate..."
az container create \
  --resource-group $RG \
  --name $ACI_NAME \
  --image $CONTAINER_IMAGE \
  --location $LOCATION \
  --assign-identity $IDENTITY_ID \
  --cpu 2 --memory 4 \
  --ports 8080 80 \
  --restart-policy Always \
  --environment-variables KV_NAME=$KV_NAME
