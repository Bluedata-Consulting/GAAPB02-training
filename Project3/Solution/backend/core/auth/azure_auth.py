import json
import logging
import os
from typing import Optional
from azure.identity import ClientSecretCredential, DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
from config.settings import settings

logger = logging.getLogger(__name__)

class AzureAuthManager:
    """Manages Azure authentication and Key Vault access"""
    
    def __init__(self):
        self.vault_url = f"https://{settings.KEY_VAULT_NAME}.vault.azure.net"
        self._secret_client = None
        self._credential = None
        
    def _get_credential(self):
        """Get Azure credential using multiple authentication methods"""
        if self._credential:
            return self._credential
            
        try:
            # Method 1: Try Service Principal from environment
            if all([settings.AZURE_CLIENT_ID, settings.AZURE_CLIENT_SECRET, settings.AZURE_TENANT_ID]):
                logger.info("Using Service Principal authentication")
                self._credential = ClientSecretCredential(
                    tenant_id=settings.AZURE_TENANT_ID,
                    client_id=settings.AZURE_CLIENT_ID,
                    client_secret=settings.AZURE_CLIENT_SECRET
                )
                return self._credential
            
            # Method 2: Try Service Principal from azure_auth.json
            if os.path.exists('azure_auth.json'):
                logger.info("Using Service Principal from azure_auth.json")
                with open('azure_auth.json') as f:
                    creds = json.load(f)
                
                self._credential = ClientSecretCredential(
                    tenant_id=creds['tenant'],
                    client_id=creds['appId'],
                    client_secret=creds['password']
                )
                return self._credential
            
            # Method 3: Try Managed Identity
            logger.info("Trying Managed Identity authentication")
            self._credential = ManagedIdentityCredential()
            # Test the credential
            token = self._credential.get_token("https://vault.azure.net/.default")
            if token:
                return self._credential
                
        except Exception as e:
            logger.warning(f"Managed Identity failed: {e}")
        
        # Method 4: Fallback to DefaultAzureCredential
        logger.info("Using DefaultAzureCredential as fallback")
        self._credential = DefaultAzureCredential()
        return self._credential
    
    def get_secret(self, secret_name: str) -> str:
        """Retrieve secret from Azure Key Vault"""
        try:
            if not self._secret_client:
                credential = self._get_credential()
                self._secret_client = SecretClient(
                    vault_url=self.vault_url, 
                    credential=credential
                )
            
            retrieved_secret = self._secret_client.get_secret(secret_name)
            logger.info(f"Successfully retrieved secret: {secret_name}")
            return retrieved_secret.value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            # Fallback to environment variable
            env_name = secret_name.replace('-', '_').upper()
            fallback_value = os.getenv(env_name, "")
            if fallback_value:
                logger.info(f"Using environment variable fallback for {secret_name}")
            return fallback_value