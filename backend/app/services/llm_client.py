"""
Shared LLM Client for GPT-based generation tasks.
Extracted from GPTContentGenerator pattern in pdf_generator.py.
"""

import os
import json
import time
import requests
from typing import Dict, Any, Optional, Union

from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Shared LLM client for calling OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        api_key: str = None,
        api_endpoint: str = None,
        model: str = "gpt-4o-mini"
    ):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY', '')
        self.api_endpoint = api_endpoint or os.getenv(
            'OPENAI_API_ENDPOINT',
            'https://api.openai.com/v1/chat/completions'
        )
        self.model = model

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        retry_count: int = 3,
        expect_json: bool = False
    ) -> Union[str, dict]:
        """
        Call GPT API with system/user prompts.

        Args:
            system_prompt: System message for the LLM
            user_prompt: User message for the LLM
            retry_count: Number of retries on failure
            expect_json: If True, parse response as JSON

        Returns:
            str or dict depending on expect_json

        Raises:
            RuntimeError on failure after all retries
        """
        if not self.api_key:
            raise RuntimeError(
                'OpenAI API key not configured. '
                'Set OPENAI_API_KEY environment variable or provide api_key parameter.'
            )

        is_reasoning = any(k in self.model.lower() for k in ['gpt-5', 'o1', 'o3'])
        base_timeout = 180 if is_reasoning else 120
        use_json_format = expect_json and not is_reasoning

        last_error = None

        for attempt in range(retry_count):
            # Exponential backoff: 0s, 2s, 4s between retries
            if attempt > 0:
                backoff = 2 ** attempt
                logger.info(f"LLM retry {attempt}/{retry_count}, backing off {backoff}s")
                time.sleep(backoff)

            # Increase timeout on retries to handle transient slowness
            timeout = base_timeout + (attempt * 30)

            try:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }

                payload = {
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt}
                    ]
                }

                if is_reasoning:
                    payload['max_completion_tokens'] = 4000
                else:
                    payload['max_tokens'] = 4000
                    payload['temperature'] = 0.7

                if use_json_format:
                    payload['response_format'] = {'type': 'json_object'}

                response = requests.post(
                    self.api_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content'].strip()

                    if not content or len(content) < 10:
                        last_error = 'LLM returned empty content'
                        continue

                    if expect_json:
                        return self._parse_json(content)

                    return content
                elif response.status_code == 400 and 'response_format' in response.text:
                    # Model doesn't support response_format — disable it and retry immediately
                    logger.warning(
                        f"Model '{self.model}' does not support response_format, "
                        "retrying without it"
                    )
                    use_json_format = False
                    continue
                else:
                    last_error = f'API returned status {response.status_code}: {response.text[:200]}'
                    logger.error(f"LLM API error: {last_error}")

            except requests.exceptions.Timeout:
                last_error = f'Request timed out after {timeout}s'
                logger.error(f"LLM API timeout: {last_error} (attempt {attempt + 1}/{retry_count})")

            except Exception as e:
                last_error = str(e)
                logger.error(f"LLM API exception: {last_error}")

        raise RuntimeError(f'LLM call failed after {retry_count} attempts: {last_error}')

    @staticmethod
    def _parse_json(content: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        cleaned = content.strip()

        # Remove markdown code blocks
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned = '\n'.join(lines).strip()

        return json.loads(cleaned)
