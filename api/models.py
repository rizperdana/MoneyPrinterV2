"""Pydantic request/response models for the API."""

from pydantic import BaseModel, ConfigDict


class GenerateRequest(BaseModel):
    account: str
    niche: str
    locale: str = "en-US"
    for_kids: bool = False
    auto_upload: bool = False


class JobResponse(BaseModel):
    job_id: str
    status: str


class AccountCreate(BaseModel):
    platform: str
    username: str
    nickname: str | None = None
    topic: str | None = None
    topics: str | None = None
    locale: str = "en-US"
    audience: str = "general"  # ADD THIS


class AccountUpdate(BaseModel):
    platform: str | None = None
    username: str | None = None
    nickname: str | None = None
    topic: str | None = None
    topics: str | None = None
    locale: str | None = None
    audience: str | None = None  # ADD THIS


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")

    llm_base_url: str | None = None
    llm_model: str | None = None
    tts_voice: str | None = None
    headless: bool | None = None
    firefox_profile: str | None = None
    imagemagick_path: str | None = None
    is_for_kids: bool | None = None
    threads: int | None = None
    verbose: bool | None = None
    script_sentence_length: int | None = None
