"""توفير Dependencies التي تحتاجها Narrative HTTP API.

يقرأ هذا الملف Gemini API Key من متغيرات البيئة，
وينشئ Gemini Client الذي تستخدمه Narrative Endpoint.
"""

import os
from dotenv import load_dotenv
from google import genai
from fastapi import Depends, status, HTTPException

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

def get_gemini_client() -> genai.Client:
    """إنشاء وإرجاع Gemini Client باستخدام مفتاح API من متغيرات البيئة."""
    if not gemini_api_key:
        raise HTTPException(
            # لأن الطلب قد يكون صحيحًا، لكن الـBackend غير جاهز لاستخدام الخدمة الخارجية.
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY غير موجود في متغيرات البيئة.",
        )
    return genai.Client(api_key=gemini_api_key)