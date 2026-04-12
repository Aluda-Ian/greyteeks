import openai
from django.conf import settings

def get_ai_campaign_suggestion(prompt):
    # This will be used later for the "Generate with AI" button
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Draft a professional {prompt} campaign message."}]
    )
    return response.choices[0].message.content