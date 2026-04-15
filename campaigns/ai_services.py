try:
    import google.generativeai as genai
except ImportError:
    genai = None

from providers.models import AIProviderSetting


def _get_gemini_key():
    ai_config = AIProviderSetting.objects.order_by('pk').first()
    if not ai_config or not ai_config.gemini_api_key:
        raise ValueError('AI is not configured.')
    return ai_config.gemini_api_key


def _init_gemini():
    if genai is None:
        raise ImportError('The google-generativeai package is required for AI features. Install it in the project environment.')
    api_key = _get_gemini_key()
    genai.configure(api_key=api_key)
    return genai


def _extract_text(response):
    if hasattr(response, 'candidates') and response.candidates:
        return getattr(response.candidates[0], 'content', '').strip()
    if hasattr(response, 'text'):
        return response.text.strip()
    return str(response).strip()


def generate_campaign_copy(topic, channel):
    if not topic:
        raise ValueError('Topic is required for AI copy generation.')

    genai = _init_gemini()
    prompt = (
        f"You are an expert copywriter. Write a highly converting message for {channel} about {topic}. "
        "If SMS, keep under 160 characters. If WhatsApp, use formatting and emojis. "
        "If Email, use professional persuasive language."
    )
    response = genai.generate(
        model='gemini-1.5-flash',
        prompt=prompt,
        temperature=0.7,
        top_p=0.95,
        max_output_tokens=256,
    )
    return _extract_text(response)


def suggest_inbox_reply(message_history):
    if not message_history:
        raise ValueError('Message history is required for AI reply suggestion.')

    genai = _init_gemini()
    prompt = (
        f"Draft a polite, concise, professional reply from the business owner to the customer based on this chat history: {message_history}."
    )
    response = genai.generate(
        model='gemini-1.5-flash',
        prompt=prompt,
        temperature=0.7,
        top_p=0.95,
        max_output_tokens=256,
    )
    return _extract_text(response)
