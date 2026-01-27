"""LightOnOCR GPU service client.

LOCR-06: LightOnOCRClient in backend communicates with GPU service via HTTP
"""

import base64
import logging
from typing import Literal, cast

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
    DEFAULT_MAX_TOKENS = 3072  # Model context is 4096 total; leave ~1024 for input

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
        # google.oauth2.id_token.fetch_id_token returns str but lacks type stubs
        return cast(str, id_token.fetch_id_token(AuthRequest(), self.service_url))

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
            text: str = result["choices"][0]["message"]["content"]
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

        Uses vLLM's /v1/models endpoint to verify service availability.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            token = self._get_id_token()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.service_url}/v1/models",
                    headers={"Authorization": f"Bearer {token}"},
                )
                # Check if response is 200 and contains models
                if response.status_code == 200:
                    data = response.json()
                    # Verify our model is in the list
                    models = data.get("data", [])
                    return any(m.get("id") == self.MODEL_ID for m in models)
                return False
        except Exception as e:
            logger.warning("Health check failed: %s", str(e))
            return False

    async def health_check_with_retry(
        self, max_wait_seconds: int = 60, initial_delay: float = 1.0
    ) -> bool:
        """Check GPU service health with exponential backoff retry.

        Handles cold starts where GPU service takes ~30 seconds to initialize.
        Uses exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s up to max_wait_seconds.

        Args:
            max_wait_seconds: Maximum total time to wait for service (default 60s)
            initial_delay: Initial retry delay in seconds (default 1s)

        Returns:
            True if service becomes healthy within timeout, False otherwise
        """
        import asyncio

        delay = initial_delay
        total_waited = 0.0
        attempt = 0

        while total_waited < max_wait_seconds:
            attempt += 1
            is_healthy = await self.health_check()

            if is_healthy:
                if attempt > 1:
                    logger.info(
                        "GPU service became healthy after %d attempts (%.1fs)",
                        attempt,
                        total_waited,
                    )
                return True

            # Calculate next delay with exponential backoff
            wait_time = min(delay, max_wait_seconds - total_waited)
            if wait_time <= 0:
                break

            logger.info(
                "GPU service not ready (attempt %d), retrying in %.1fs (total waited: %.1fs/%.0fs)",
                attempt,
                wait_time,
                total_waited,
                max_wait_seconds,
            )

            await asyncio.sleep(wait_time)
            total_waited += wait_time
            delay *= 2  # Exponential backoff

        logger.warning(
            "GPU service did not become healthy after %.1fs (%d attempts)",
            total_waited,
            attempt,
        )
        return False
