import json
import re

from django.conf import settings
from groq import APIConnectionError, APIStatusError, APITimeoutError, Groq, RateLimitError

from .prompts import RESUME_ANALYSIS_SYSTEM_PROMPT
from .validators import ANALYSIS_JSON_SCHEMA, InvalidAnalysisData, validate_analysis_data


MAX_RESUME_ANALYSIS_CHARS = 50000


class ResumeAnalysisError(Exception):
    pass


class AIServiceNotConfigured(ResumeAnalysisError):
    pass


class ResumeTextTooLarge(ResumeAnalysisError):
    pass


class AIAnalysisTimedOut(ResumeAnalysisError):
    pass


class AIRateLimited(ResumeAnalysisError):
    pass


class InvalidAIResponse(ResumeAnalysisError):
    pass


class GroqServiceUnavailable(ResumeAnalysisError):
    pass


def normalize_resume_text(resume_text):
    normalized = re.sub(r'[ \t]+', ' ', resume_text)
    normalized = re.sub(r' *\n *', '\n', normalized)
    normalized = re.sub(r'\n{3,}', '\n\n', normalized).strip()
    if len(normalized) > MAX_RESUME_ANALYSIS_CHARS:
        raise ResumeTextTooLarge
    if not normalized:
        raise ResumeAnalysisError('The resume text is empty.')
    return normalized


class GroqResumeAnalyzer:
    def analyze_resume(self, resume_text):
        normalized_text = normalize_resume_text(resume_text)
        api_key = getattr(settings, 'GROQ_API_KEY', '')
        if not api_key:
            raise AIServiceNotConfigured

        client = Groq(api_key=api_key, timeout=30.0)
        try:
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {'role': 'system', 'content': RESUME_ANALYSIS_SYSTEM_PROMPT},
                    {'role': 'user', 'content': normalized_text},
                ],
                response_format={
                    'type': 'json_schema',
                    'json_schema': {
                        'name': 'resume_analysis',
                        'strict': True,
                        'schema': ANALYSIS_JSON_SCHEMA,
                    },
                },
                temperature=0,
                max_completion_tokens=4096,
            )
        except APITimeoutError as error:
            raise AIAnalysisTimedOut from error
        except RateLimitError as error:
            raise AIRateLimited from error
        except (APIConnectionError, APIStatusError) as error:
            raise GroqServiceUnavailable from error

        try:
            content = response.choices[0].message.content
            if not isinstance(content, str):
                raise InvalidAnalysisData('The response content is not text.')
            data = json.loads(content)
            return validate_analysis_data(data)
        except (IndexError, AttributeError, TypeError, json.JSONDecodeError, InvalidAnalysisData) as error:
            raise InvalidAIResponse from error