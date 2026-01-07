"""
Voice processing endpoints for speech-to-text and text-to-speech.
"""
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel, Field
import base64
import logging
import httpx

from app.db.models import User
from app.core.auth import get_current_active_user
from app.config import settings
from app.core.exceptions import ExternalServiceError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class TranscribeResponse(BaseModel):
    """Response model for transcription."""

    transcript: str
    confidence: Optional[float] = None
    duration_seconds: Optional[float] = None
    language: Optional[str] = None


class SynthesizeRequest(BaseModel):
    """Request model for TTS synthesis."""

    text: str = Field(..., description="Text to synthesize", max_length=5000)
    voice_id: Optional[str] = Field(None, description="Voice ID for synthesis")
    model_id: Optional[str] = Field("eleven_turbo_v2", description="TTS model")
    voice_settings: Optional[dict] = Field(None, description="Voice settings")


class SynthesizeResponse(BaseModel):
    """Response model for TTS synthesis."""

    audio_base64: str = Field(..., description="Base64 encoded audio")
    audio_format: str = Field("mp3", description="Audio format")
    duration_seconds: Optional[float] = None


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form("en", description="Language code"),
    model: Optional[str] = Form("nova-2-general", description="Deepgram model"),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """
    Transcribe audio file to text using Deepgram.

    This is a fallback endpoint for when real-time streaming isn't available.
    The mobile app should prefer using Deepgram's WebSocket API directly.
    """
    # Validate file size (max 25MB)
    max_size = 25 * 1024 * 1024  # 25MB
    contents = await audio_file.read()

    if len(contents) > max_size:
        raise ValidationError("Audio file too large (max 25MB)")

    # Check if using user's API key or managed key
    deepgram_key = None
    if current_user and current_user.api_keys:
        # TODO: Decrypt user's Deepgram key
        pass

    if not deepgram_key:
        deepgram_key = settings.DEEPGRAM_API_KEY

    if not deepgram_key:
        raise ExternalServiceError("Deepgram", "API key not configured")

    try:
        async with httpx.AsyncClient() as client:
            # Prepare Deepgram API request
            response = await client.post(
                f"https://api.deepgram.com/v1/listen",
                params={
                    "model": model,
                    "language": language,
                    "punctuate": "true",
                    "smart_format": "true",
                    "utterances": "true",
                },
                headers={
                    "Authorization": f"Token {deepgram_key}",
                    "Content-Type": audio_file.content_type or "audio/wav",
                },
                content=contents,
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Deepgram error: {response.text}")
                raise ExternalServiceError("Deepgram", f"API error: {response.status_code}")

            result = response.json()

            # Extract transcript
            if "results" in result and result["results"]["channels"]:
                channel = result["results"]["channels"][0]
                if channel["alternatives"]:
                    transcript = channel["alternatives"][0]["transcript"]
                    confidence = channel["alternatives"][0].get("confidence")

                    return TranscribeResponse(
                        transcript=transcript,
                        confidence=confidence,
                        duration_seconds=result.get("metadata", {}).get("duration"),
                        language=result.get("metadata", {}).get("language"),
                    )

            raise ExternalServiceError("Deepgram", "No transcript in response")

    except httpx.RequestError as e:
        logger.error(f"Deepgram request error: {e}")
        raise ExternalServiceError("Deepgram", str(e))


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_speech(
    request: SynthesizeRequest,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """
    Synthesize text to speech using ElevenLabs.

    Returns audio as base64 encoded data. For real-time streaming,
    the mobile app should use ElevenLabs WebSocket API directly.
    """
    # Check if using user's API key or managed key
    elevenlabs_key = None
    if current_user and current_user.api_keys:
        # TODO: Decrypt user's ElevenLabs key
        pass

    if not elevenlabs_key:
        elevenlabs_key = settings.ELEVENLABS_API_KEY

    if not elevenlabs_key:
        raise ExternalServiceError("ElevenLabs", "API key not configured")

    # Default voice if not specified
    voice_id = request.voice_id or "21m00Tcm4TlvDq8ikWAM"  # Rachel voice

    # Default voice settings
    voice_settings = request.voice_settings or {
        "stability": 0.5,
        "similarity_boost": 0.75,
    }

    try:
        async with httpx.AsyncClient() as client:
            # ElevenLabs TTS API
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "Accept": "audio/mpeg",
                    "xi-api-key": elevenlabs_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": request.text,
                    "model_id": request.model_id,
                    "voice_settings": voice_settings,
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"ElevenLabs error: {response.text}")
                raise ExternalServiceError("ElevenLabs", f"API error: {response.status_code}")

            # Convert audio to base64
            audio_bytes = response.content
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            return SynthesizeResponse(
                audio_base64=audio_base64,
                audio_format="mp3",
                duration_seconds=None,  # ElevenLabs doesn't return duration
            )

    except httpx.RequestError as e:
        logger.error(f"ElevenLabs request error: {e}")
        raise ExternalServiceError("ElevenLabs", str(e))


@router.get("/voices")
async def list_available_voices(
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """
    List available TTS voices from ElevenLabs.
    """
    # Check if using user's API key or managed key
    elevenlabs_key = None
    if current_user and current_user.api_keys:
        # TODO: Decrypt user's ElevenLabs key
        pass

    if not elevenlabs_key:
        elevenlabs_key = settings.ELEVENLABS_API_KEY

    if not elevenlabs_key:
        # Return default voices if no API key
        return {
            "voices": [
                {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel"},
                {"voice_id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi"},
                {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella"},
            ]
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": elevenlabs_key},
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get voices: {response.status_code}")
                # Return default voices on error
                return {
                    "voices": [
                        {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel"},
                    ]
                }

    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        return {
            "voices": [
                {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel"},
            ]
        }