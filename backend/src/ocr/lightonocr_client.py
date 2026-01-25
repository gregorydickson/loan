"""LightOnOCR GPU service client.

LOCR-06: LightOnOCRClient in backend communicates with GPU service via HTTP
"""

import base64
import logging
from typing import Literal

import httpx
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2 import id_token

logger = logging.getLogger(__name__)


class LightOnOCRError(Exception):
    """Base exception for LightOnOCR client errors."""

    pass


class LightOnOCRClient:
    """Client for LightOnOCR GPU service using vLLM OpenAI-compatible API.

    LOCR-06: LightOnOCRClient in backend communicates with GPU service via HTTP
    LOCR-07: GPU service requires internal-only authentication (service account)

    Example:
        client = LightOnOCRClient(service_url="https://lightonocr-gpu-xxx.run.app")
        text = await client.extract_text(image_bytes)
    """

    MODEL_ID = "lightonai/LightOnOCR-2-1B"
    DEFAULT_TIMEOUT = 120.0  # 2 minutes for cold start + processing
    DEFAULT_MAX_TOKENS = 4096

    def __init__(
        self,
        service_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """Initialize LightOnOCR client.

        Args:
            service_url: Cloud Run GPU service URL (e.g., https://lightonocr-gpu-xxx.run.app)
            timeout: Request timeout in seconds (default 120s for cold starts)
            max_tokens: Max tokens for OCR output (default 4096)
        """
        self.service_url = service_url.rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self._id_token_cache: str | None = None

    def _get_id_token(self) -> str:
        """Get OIDC ID token for Cloud Run authentication.

        Uses google-auth library to fetch ID token for service-to-service auth.
        Token is cached but refreshed on each request for simplicity (POC).

        Returns:
            ID token string for Authorization header
        """
        return id_token.fetch_id_token(AuthRequest(), self.service_url)

    def _detect_content_type(self, image_bytes: bytes) -> Literal["image/png", "image/jpeg"]:
        """Detect image content type from magic bytes.

        Args:
            image_bytes: Raw image bytes

        Returns:
            MIME type string
        """
        if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if image_bytes[:2] == b"\xff\xd8":
            return "image/jpeg"
        # Default to JPEG for unknown formats
        return "image/jpeg"

    async def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image using LightOnOCR GPU service.

        LOCR-06: Communicates with GPU service via HTTP

        Args:
            image_bytes: PNG or JPEG image bytes

        Returns:
            Extracted text from the image

        Raises:
            LightOnOCRError: If extraction fails
        """
        if not image_bytes:
            raise LightOnOCRError("Empty image bytes provided")

        # Encode image as base64 data URI
        content_type = self._detect_content_type(image_bytes)
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{content_type};base64,{base64_image}"

        # Build vLLM OpenAI-compatible request
        payload = {
            "model": self.MODEL_ID,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        }
                    ],
                }
            ],
            "max_tokens": self.max_tokens,
        }

        # Get auth token
        try:
            token = self._get_id_token()
        except Exception as e:
            logger.error("Failed to get ID token: %s", str(e))
            raise LightOnOCRError(f"Authentication failed: {str(e)}") from e

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Make request to vLLM chat completions endpoint
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )

                if response.status_code != 200:
                    error_text = response.text[:500]  # Truncate for logging
                    logger.error(
                        "LightOnOCR request failed: status=%d, body=%s",
                        response.status_code,
                        error_text,
                    )
                    raise LightOnOCRError(
                        f"Request failed with status {response.status_code}: {error_text}"
                    )

                result = response.json()

        except httpx.TimeoutException as e:
            logger.error("LightOnOCR request timed out: %s", str(e))
            raise LightOnOCRError(f"Request timed out after {self.timeout}s") from e
        except httpx.RequestError as e:
            logger.error("LightOnOCR request error: %s", str(e))
            raise LightOnOCRError(f"Request failed: {str(e)}") from e

        # Extract text from vLLM response
        try:
            text = result["choices"][0]["message"]["content"]
            logger.info(
                "LightOnOCR extracted %d characters from image",
                len(text),
            )
            return text
        except (KeyError, IndexError) as e:
            logger.error("Unexpected response format: %s", result)
            raise LightOnOCRError(f"Invalid response format: {str(e)}") from e

    async def health_check(self) -> bool:
        """Check if GPU service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            token = self._get_id_token()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.service_url}/health",
                    headers={"Authorization": f"Bearer {token}"},
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning("Health check failed: %s", str(e))
            return False
