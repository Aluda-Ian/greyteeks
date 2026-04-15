import random
from django.conf import settings

try:
    import openai
except ImportError:
    openai = None

def get_ai_campaign_suggestion(prompt):
    # This will be used later for the "Generate with AI" button
    fallback_suggestions = [
        f"Spark urgency with a limited-time offer for {prompt}. Drive immediate responses with a clear call to action.",
        f"Share a polished {prompt} message that highlights value, trust, and a strong next step for your audience.",
        f"Deliver a concise, professional {prompt} message that feels personal, benefit-driven, and easy to act on."
    ]

    if not settings.OPENAI_API_KEY or openai is None:
        return random.choice(fallback_suggestions)

    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Draft a professional {prompt} campaign message."}]
        )
        return response.choices[0].message.content
    except Exception:
        return random.choice(fallback_suggestions)
