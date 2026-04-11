"""Pydantic request/response models for the API."""

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    account: str
    niche: str
    language: str = "English"
    for_kids: bool = False


class JobResponse(BaseModel):
    job_id: str
    status: str


class AccountCreate(BaseModel):
    platform: str
    username: str
    nickname: str | None = None
    profile_path: str | None = None


class AccountUpdate(BaseModel):
    platform: str | None = None
    username: str | None = None
    nickname: str | None = None
    profile_path: str | None = None


class SettingsUpdate(BaseModel):
    llm_base_url: str | None = None
    llm_model: str | None = None
    nanobanana2_api_key: str | None = None
    nanobanana2_model: str | None = None
    tts_voice: str | None = None
    headless: bool | None = None
    firefox_profile: str | None = None
    imagemagick_path: str | None = None
    is_for_kids: bool | None = None
    threads: int | None = None
    verbose: bool | None = None
    script_sentence_length: int | None = None
