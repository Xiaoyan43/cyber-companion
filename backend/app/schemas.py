from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ChatMessageSchema(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompleteRequest(BaseModel):
    messages: list[ChatMessageSchema] = Field(min_length=1)
    provider: str | None = None
    max_output_tokens: int = Field(default=2400, ge=1, le=4000)


class TokenUsageSchema(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class CostEstimateSchema(BaseModel):
    input_usd: float
    output_usd: float
    total_usd: float
    pricing_source: str


class ChatCompleteResponse(BaseModel):
    provider: str
    model: str
    content: str
    usage: TokenUsageSchema
    cost: CostEstimateSchema
    mock: bool = False
    avatar_state: str = "talking"
    decision: str = "reply"
    should_call_llm: bool = True


class BehaviorDecisionSchema(BaseModel):
    decision: str
    avatar_state: str
    should_call_llm: bool
    reason: str
    local_response: str | None = None
    tone_mode: str = "normal"
    saved_message_id: int | None = None


class BehaviorEvaluateRequest(BaseModel):
    user_input: str = ""
    event_type: Literal["user_message", "proactive_check", "idle_tick"] = "user_message"
    force_proactive: bool = False


class ProviderStatusSchema(BaseModel):
    name: str
    enabled: bool
    model: str
    configured: bool
    api_key_present: bool
    placeholder: bool = False


class ProvidersStatusResponse(BaseModel):
    default_provider: str
    force_mock: bool
    providers: list[ProviderStatusSchema]


class ErrorResponse(BaseModel):
    error: str
    provider: str | None = None


class StoredMessageSchema(BaseModel):
    id: int
    created_at: str
    role: str
    content: str
    source: str
    metadata: dict


class MessageListResponse(BaseModel):
    messages: list[StoredMessageSchema]


class MemoryCreateRequest(BaseModel):
    type: str
    content: str
    tags: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    expires_at: str | None = None
    source_message_id: int | None = None
    metadata: dict = Field(default_factory=dict)


class MemoryUpdateRequest(BaseModel):
    content: str | None = None
    tags: list[str] | None = None
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    expires_at: str | None = None
    metadata: dict | None = None


class MemorySchema(BaseModel):
    id: int
    created_at: str
    updated_at: str
    type: str
    content: str
    tags: list[str]
    importance: float
    confidence: float
    expires_at: str | None
    source_message_id: int | None
    metadata: dict


class MemoryListResponse(BaseModel):
    memories: list[MemorySchema]


class MemoryLinkSchema(BaseModel):
    id: int
    memory_id: int
    related_memory_id: int
    relation: str
    created_at: str
    memory_type: str
    memory_content: str
    related_type: str
    related_content: str


class MemoryLinkListResponse(BaseModel):
    links: list[MemoryLinkSchema]


class MoodStateSchema(BaseModel):
    updated_at: str
    mood: str
    energy: float
    annoyance: float
    boredom: float
    worry: float
    trust: float
    loneliness: float
    metadata: dict


class MoodStateUpdateRequest(BaseModel):
    mood: str | None = None
    energy: float | None = Field(default=None, ge=0.0, le=1.0)
    annoyance: float | None = Field(default=None, ge=0.0, le=1.0)
    boredom: float | None = Field(default=None, ge=0.0, le=1.0)
    worry: float | None = Field(default=None, ge=0.0, le=1.0)
    trust: float | None = Field(default=None, ge=0.0, le=1.0)
    loneliness: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict | None = None


class RelationshipStateSchema(BaseModel):
    updated_at: str
    trust: float
    closeness: float
    familiarity: float
    tension: float
    last_meaningful_interaction_at: str | None
    metadata: dict


class ContextPreviewResponse(BaseModel):
    estimated_input_tokens: int
    included_memory_ids: list[int]
    included_message_ids: list[int]
    summary_used: str | None
    truncated: bool
    total_stored_messages: int
    message_count_sent: int
    messages: list[ChatMessageSchema]


class AllowedFolderSchema(BaseModel):
    path: str
    read: bool
    write: bool
    resolved_path: str


class FilePermissionsStatusResponse(BaseModel):
    allowed_folders: list[AllowedFolderSchema]
    deny_shell_execution: bool
    log_file_access: bool


class FileAccessCheckRequest(BaseModel):
    path: str
    operation: Literal["read", "write"] = "read"


class FileAccessCheckResponse(BaseModel):
    allowed: bool
    operation: str
    requested_path: str
    resolved_path: str
    reason: str
    matched_folder: str | None = None


class FileAccessLogSchema(BaseModel):
    id: int
    created_at: str
    operation: str
    requested_path: str
    resolved_path: str
    allowed: bool
    reason: str


class FileAccessLogListResponse(BaseModel):
    logs: list[FileAccessLogSchema]


class STTProviderStatusSchema(BaseModel):
    name: str
    enabled: bool
    model: str
    configured: bool
    api_key_present: bool
    placeholder: bool = False
    cloud: bool = False


class STTStatusResponse(BaseModel):
    enabled: bool
    default_provider: str
    force_mock: bool
    allow_cloud_stt: bool
    providers: list[STTProviderStatusSchema]


class STTTranscribeResponse(BaseModel):
    provider: str
    model: str
    text: str
    mock: bool = False
    language: str | None = None


class TTSProviderStatusSchema(BaseModel):
    name: str
    enabled: bool
    model: str
    configured: bool
    api_key_present: bool
    placeholder: bool = False
    cloud: bool = False


class TTSStatusResponse(BaseModel):
    enabled: bool
    default_provider: str
    force_mock: bool
    allow_cloud_tts: bool
    max_speech_chars: int
    speak_decisions: list[str]
    providers: list[TTSProviderStatusSchema]


class TTSEvaluateRequest(BaseModel):
    text: str
    decision: str | None = None
    avatar_state: str | None = None
    force: bool = False


class TTSEvaluateResponse(BaseModel):
    should_speak: bool
    reason: str


class TTSSynthesizeRequest(BaseModel):
    text: str
    decision: str | None = None
    avatar_state: str | None = None
    force: bool = False
    provider: str | None = None


class TTSSynthesizeResponse(BaseModel):
    spoken: bool
    reason: str
    provider: str | None = None
    model: str | None = None
    mime_type: str | None = None
    audio_base64: str | None = None
    duration_ms: int | None = None
    mock: bool = False


RtcModeSchema = Literal["pure", "hybrid"]


class RtcStatusResponse(BaseModel):
    base_configured: bool
    pure_ready: bool
    hybrid_ready: bool
    missing_pure: list[str] = Field(default_factory=list)
    missing_hybrid: list[str] = Field(default_factory=list)
    viking_memory_enabled: bool = False
    viking_memory_write_ready: bool = False
    sqlite_memory_ready: bool = False
    default_user_id: str = "boxi_user"


class RtcMemorySubtitleItem(BaseModel):
    speaker: Literal["user", "boxi"]
    text: str = ""


class RtcMemorySessionRequest(BaseModel):
    room_id: str = ""
    user_id: str
    bot_user_id: str = ""
    subtitles: list[RtcMemorySubtitleItem] = Field(default_factory=list)


class RtcMemorySessionResponse(BaseModel):
    saved: bool
    session_id: str
    message_count: int


class RtcPrepareRequest(BaseModel):
    mode: RtcModeSchema = "pure"
    room_id: str = ""
    user_id: str = ""


class RtcPrepareResponse(BaseModel):
    mode: RtcModeSchema
    output_mode: int
    app_id: str
    room_id: str
    user_id: str
    token: str
    bot_user_id: str
    task_id: str
    welcome_message: str


class RtcAgentStartRequest(BaseModel):
    mode: RtcModeSchema = "pure"
    room_id: str
    user_id: str


class RtcStopRequest(BaseModel):
    mode: RtcModeSchema = "pure"
    room_id: str


class RtcStopResponse(BaseModel):
    stopped: bool
    mode: RtcModeSchema
    room_id: str


class RtcTurnRequest(BaseModel):
    room_id: str
    user_id: str
    user_text: str
    bot_text: str


class RtcTurnResponse(BaseModel):
    status: str = "ok"

