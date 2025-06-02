#!/bin/bash
# Quick Weaviate Web App for Containers Setup

# Variables - CHANGE THESE
NAME="anshu"
RG="Tredence-Batch2"
LOCATION="eastus2"

# Derived names
AZURE_OPENAI_RESOURCE="$NAME-openai"
APP_SERVICE_PLAN="$NAME-asp"
WEB_APP_NAME="$NAME-weaviate-app"
STORAGE_ACCOUNT="$NAME$(date +%s)st"  # Short name for storage

echo "🚀 Starting Weaviate Web App deployment..."

# 1. Create Azure OpenAI
echo "Creating Azure OpenAI..."
az cognitiveservices account create \
  --name $AZURE_OPENAI_RESOURCE \
  --resource-group $RG \
  --kind OpenAI \
  --sku S0 \
  --location $LOCATION \
  --yes

az cognitiveservices account deployment create \
  --resource-group $RG \
  --name $AZURE_OPENAI_RESOURCE \
  --deployment-name "text-embedding-ada-002" \
  --model-name text-embedding-ada-002 \
  --model-version 2 \
  --model-format OpenAI \
  --sku-name Standard \
  --scale-type Standard

# Get credentials
OPENAI_ENDPOINT=$(az cognitiveservices account show --name $AZURE_OPENAI_RESOURCE --resource-group $RG --query "properties.endpoint" -o tsv)
OPENAI_API_KEY=$(az cognitiveservices account keys list --name $AZURE_OPENAI_RESOURCE --resource-group $RG --query key1 -o tsv)

# 2. Create Storage for persistence
echo "Creating Storage Account..."
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RG \
  --location $LOCATION \
  --sku Standard_LRS

STORAGE_KEY=$(az storage account keys list --resource-group $RG --account-name $STORAGE_ACCOUNT --query '[0].value' -o tsv)

az storage share create \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY \
  --name "weaviatedata"

# 3. Create App Service Plan
echo "Creating App Service Plan..."
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RG \
  --location $LOCATION \
  --is-linux \
  --sku B2

# 4. Create docker-compose.yml
echo "Creating Docker Compose file..."
cat > docker-compose.yml << EOF
version: '3.8'
services:
  weaviate:
    image: cr.weaviate.io/semitechnologies/weaviate:1.30.6
    ports:
      - "8080:8080"
    volumes:
      - weaviate_data:/var/lib/weaviate
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'text2vec-openai'
      ENABLE_MODULES: 'text2vec-openai,generative-openai'
      CLUSTER_HOSTNAME: 'node1'
    restart: on-failure:0
    command:
      - --host
      - 0.0.0.0
      - --port
      - '8080'
      - --scheme
      - http

volumes:
  weaviate_data:
EOF

# 5. Create Web App
echo "Creating Web App..."
az webapp create \
  --resource-group $RG \
  --plan $APP_SERVICE_PLAN \
  --name $WEB_APP_NAME \
  --multicontainer-config-type compose \
  --multicontainer-config-file docker-compose.yml

# 6. Configure environment and storage
echo "Configuring Web App..."
az webapp config appsettings set \
  --resource-group $RG \
  --name $WEB_APP_NAME \
  --settings \
    AZURE_APIKEY="$OPENAI_API_KEY" \
    WEBSITES_PORT=8080 \
    WEBSITES_CONTAINER_START_TIME_LIMIT=600

az webapp config storage-account add \
  --resource-group $RG \
  --name $WEB_APP_NAME \
  --custom-id weaviate_data \
  --storage-type AzureFiles \
  --share-name "weaviatedata" \
  --account-name $STORAGE_ACCOUNT \
  --access-key $STORAGE_KEY \
  --mount-path /var/lib/weaviate

# 7. Start and test
echo "Starting Web App..."
az webapp start --resource-group $RG --name $WEB_APP_NAME

echo "🎉 Deployment complete!"
echo ""
echo "📋 IMPORTANT DETAILS:"
echo "Web App URL: https://$WEB_APP_NAME.azurewebsites.net"
echo "Health Check: https://$WEB_APP_NAME.azurewebsites.net/v1/.well-known/ready"
echo "OpenAI Endpoint: $OPENAI_ENDPOINT"
echo "OpenAI API Key: $OPENAI_API_KEY"
echo ""
echo "⏰ Wait 5-10 minutes for deployment to complete, then test the health check URL"

# Test connectivity (optional)
echo "Testing connectivity in 60 seconds..."
sleep 60
curl -s "https://$WEB_APP_NAME.azurewebsites.net/v1/.well-known/ready" && echo "✅ Weaviate is ready!" || echo "⏳ Still starting up..."