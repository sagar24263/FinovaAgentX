import json
import os

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.utils.api_client import make_sync_get_request
from app.utils.logger import get_logger

logger = get_logger("secret_manager")


class SecretManager:
    def __init__(self):
        self.region_name = os.getenv("AWS_REGION", "ap-south-1")
        self.secret_name = os.getenv("AWS_SECRET_NAME", "QA_Investment")
        self.local_aws_token = os.getenv("LOCAL_AWS_TOKEN", "")
        self.env = os.getenv("ENV", "dev")
        self.client = self._initialize_client()
        self._secret_cache: dict | None = None

    def _initialize_client(self):
        try:
            if self.env == "dev":
                credentials = self._get_temporary_credentials()
                session = boto3.Session(
                    aws_access_key_id=credentials["accessKeyId"],
                    aws_secret_access_key=credentials["secretAccessKey"],
                    aws_session_token=credentials["token"],
                    region_name=self.region_name,
                )
                client = session.client("secretsmanager")
            else:
                client = boto3.client(
                    service_name="secretsmanager",
                    region_name=self.region_name,
                )
            logger.info(f"AWS Secret Manager client initialized for region: {self.region_name}")
            return client
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS Secret Manager client: {e}")
            raise

    def _get_temporary_credentials(self) -> dict:
        try:
            response = make_sync_get_request(
                url="https://qasavingsapi.policybazaar.com/AwsToken/api/GetToken",
                headers={"token": self.local_aws_token},
            )
            if "error" in response:
                raise Exception(f"API request failed: {response['error']}")
            return response
        except Exception as e:
            logger.error(f"Error fetching AWS credentials: {e}")
            raise

    def get_secret(self, secret_name: str | None = None) -> dict:
        """Retrieve the entire secret from AWS Secret Manager (cached after first call)."""
        if secret_name is None:
            secret_name = self.secret_name

        if self._secret_cache is not None:
            logger.info(f"Retrieved secret from cache: {secret_name}")
            return self._secret_cache

        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            parsed_secret = json.loads(response["SecretString"])
            self._secret_cache = parsed_secret
            return parsed_secret
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                logger.error(f"Secret not found: {secret_name}")
            else:
                logger.error(f"AWS error [{error_code}]: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secret as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving secret: {e}")
            raise

    def get_secret_value(self, key: str, secret_name: str | None = None) -> str:
        """Get a specific value from the secret by key."""
        try:
            secrets = self.get_secret(secret_name)
            if key not in secrets:
                raise ValueError(f"Key '{key}' not found in secret '{secret_name or self.secret_name}'")
            return secrets[key]
        except Exception as e:
            logger.error(f"Failed to get secret value for key '{key}': {e}")
            raise

    def clear_cache(self):
        """Clear the cached secret."""
        self._secret_cache = None
        logger.info("Secret cache cleared")

    def is_cached(self) -> bool:
        """Check if the secret is currently cached."""
        return self._secret_cache is not None


# Singleton instance
_secret_manager: SecretManager | None = None


def get_secret_manager() -> SecretManager:
    """Get singleton instance of SecretManager."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager
