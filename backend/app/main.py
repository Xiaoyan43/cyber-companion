from contextlib import asynccontextmanager
import base64
import json
from collections.abc import Iterator

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from starlette.responses import Response

from backend.app.behavior.completion import build_budget_block_completion, build_local_completion
from backend.app.behavior.engine import evaluate_behavior
from backend.app.behavior.idle_experience import resolve_idle_experience_write
from backend.app.behavior.proactive_opener import resolve_proactive_opener
from backend.app.behavior.kernel import apply_signals_to_kernel
from backend.app.behavior.parser import SignalStreamFilter, parse_structured_assistant_response
from backend.app.behavior.tone import (
    contains_tone_marker_tag,
    performative_active_from_metadata,
    project_tone,
    register_intensity,
    tts_emotion_directive,
)
from backend.app.behavior.types import BehaviorEvent
from backend.app.cors import load_cors_origins
from backend.app.files.config import load_permissions_config
from backend.app.files.gateway import get_file_gateway, reset_file_gateway
from backend.app.memory.budget import load_budget_config
from backend.app.memory.context_builder import build_provider_context, extract_latest_user_input
from backend.app.memory.chat_persistence import (
    persist_chat_turn,
    persist_local_behavior_line,
    should_persist_local_behavior_line,
)
from backend.app.memory.summary_policy import maybe_update_conversation_summary
from backend.app.reflection.runner import run_reflection_if_due
from backend.app.memory.write_policy import maybe_write_memories_from_turn, record_turn_memories
from backend.app.memory.usage_guard import evaluate_llm_budget_gate
from backend.app.memory.database import (
    MemoryLinkRecord,
    MemoryRecord,
    MessageRecord,
    MoodStateRecord,
    RelationshipStateRecord,
)
from backend.app.memory.store import get_memory_store, reset_memory_store
from backend.app.stt.exceptions import STTError
from backend.app.stt.router import get_stt_router, reset_stt_router
from backend.app.stt.types import TranscriptionRequest
from backend.app.tts.exceptions import TTSError
from backend.app.tts.expression_tagger import apply_expression_tags
from backend.app.tts.router import get_tts_router, reset_tts_router
from backend.app.tts.types import SynthesisRequest
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.router import get_provider_router, reset_provider_router
from backend.app.providers.cost import estimate_cost
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, ChatMessage
from backend.app.rtc.routes import router as rtc_router
from backend.realtime.pipeline_router import router as pipecat_router
from backend.app.schemas import (
    BehaviorDecisionSchema,
    BehaviorEvaluateRequest,
    ChatCompleteRequest,
    ChatCompleteResponse,
    ChatMessageSchema,
    CostEstimateSchema,
    ErrorResponse,
    HealthResponse,
    MemoryCreateRequest,
    MemoryLinkListResponse,
    MemoryLinkSchema,
    MemoryListResponse,
    MemorySchema,
    MemoryUpdateRequest,
    MessageListResponse,
    MoodStateSchema,
    MoodStateUpdateRequest,
    RelationshipStateSchema,
    ProviderStatusSchema,
    ProvidersStatusResponse,
    StoredMessageSchema,
    TokenUsageSchema,
    ContextPreviewResponse,
    AllowedFolderSchema,
    FileAccessCheckRequest,
    FileAccessCheckResponse,
    FileAccessLogListResponse,
    FileAccessLogSchema,
    FilePermissionsStatusResponse,
    STTProviderStatusSchema,
    STTStatusResponse,
    STTTranscribeResponse,
    TTSEvaluateRequest,
    TTSEvaluateResponse,
    TTSProviderStatusSchema,
    TTSSynthesizeRequest,
    TTSSynthesizeResponse,
    TTSStatusResponse,
)

APP_VERSION = "0.1.0"


def _message_to_schema(message: MessageRecord) -> StoredMessageSchema:
    return StoredMessageSchema(
        id=message.id,
        created_at=message.created_at,
        role=message.role,
        content=message.content,
        source=message.source,
        metadata=message.metadata,
    )


def _memory_to_schema(memory: MemoryRecord) -> MemorySchema:
    return MemorySchema(
        id=memory.id,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
        type=memory.type,
        content=memory.content,
        tags=memory.tags,
        importance=memory.importance,
        confidence=memory.confidence,
        expires_at=memory.expires_at,
        source_message_id=memory.source_message_id,
        metadata=memory.metadata,
    )


def _memory_link_to_schema(link: MemoryLinkRecord) -> MemoryLinkSchema:
    return MemoryLinkSchema(
        id=link.id,
        memory_id=link.memory_id,
        related_memory_id=link.related_memory_id,
        relation=link.relation,
        created_at=link.created_at,
        memory_type=link.memory_type,
        memory_content=link.memory_content,
        related_type=link.related_type,
        related_content=link.related_content,
    )


def _relationship_to_schema(rel: RelationshipStateRecord) -> RelationshipStateSchema:
    return RelationshipStateSchema(
        updated_at=rel.updated_at,
        trust=rel.trust,
        closeness=rel.closeness,
        familiarity=rel.familiarity,
        tension=rel.tension,
        last_meaningful_interaction_at=rel.last_meaningful_interaction_at,
        metadata=rel.metadata,
    )


def _mood_to_schema(mood: MoodStateRecord) -> MoodStateSchema:
    return MoodStateSchema(
        updated_at=mood.updated_at,
        mood=mood.mood,
        energy=mood.energy,
        annoyance=mood.annoyance,
        boredom=mood.boredom,
        worry=mood.worry,
        trust=mood.trust,
        loneliness=mood.loneliness,
        metadata=mood.metadata,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_memory_store()
    yield
    reset_memory_store()
    reset_provider_router()
    reset_file_gateway()
    reset_stt_router()
    reset_tts_router()


app = FastAPI(
    title="Cyber Companion Local API",
    version=APP_VERSION,
    summary="Local API shell for the text-first desktop companion MVP.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=load_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(rtc_router)
app.include_router(pipecat_router)


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="cyber-companion-api",
        version=APP_VERSION,
    )


@app.get("/providers/status", response_model=ProvidersStatusResponse)
def providers_status() -> ProvidersStatusResponse:
    router = get_provider_router()
    return ProvidersStatusResponse(
        default_provider=router.config.default_provider,
        force_mock=router.config.force_mock,
        providers=[
            ProviderStatusSchema(
                name=status.name,
                enabled=status.enabled,
                model=status.model,
                configured=status.configured,
                api_key_present=status.api_key_present,
                placeholder=status.placeholder,
            )
            for status in router.list_status()
        ],
    )


@app.get("/memory/messages", response_model=MessageListResponse)
def list_messages(limit: int = 50) -> MessageListResponse:
    store = get_memory_store()
    messages = store.list_messages(limit=limit)
    return MessageListResponse(messages=[_message_to_schema(message) for message in messages])


@app.post("/memory/memories", response_model=MemorySchema)
def create_memory(request: MemoryCreateRequest) -> MemorySchema:
    store = get_memory_store()
    try:
        memory = store.create_memory(
            type=request.type,
            content=request.content,
            tags=request.tags,
            importance=request.importance,
            confidence=request.confidence,
            expires_at=request.expires_at,
            source_message_id=request.source_message_id,
            metadata=request.metadata,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"error": str(error)}) from error
    return _memory_to_schema(memory)


@app.get("/memory/memories", response_model=MemoryListResponse)
def list_memories(type: str | None = None, limit: int = 50) -> MemoryListResponse:
    store = get_memory_store()
    try:
        memories = store.list_memories(type=type, limit=limit)
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"error": str(error)}) from error
    return MemoryListResponse(memories=[_memory_to_schema(memory) for memory in memories])


@app.get("/memory/memories/{memory_id}", response_model=MemorySchema)
def get_memory(memory_id: int) -> MemorySchema:
    store = get_memory_store()
    memory = store.get_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail={"error": "Memory not found"})
    return _memory_to_schema(memory)


@app.put("/memory/memories/{memory_id}", response_model=MemorySchema)
def update_memory(memory_id: int, request: MemoryUpdateRequest) -> MemorySchema:
    store = get_memory_store()
    memory = store.update_memory(
        memory_id,
        content=request.content,
        tags=request.tags,
        importance=request.importance,
        confidence=request.confidence,
        expires_at=request.expires_at,
        metadata=request.metadata,
    )
    if memory is None:
        raise HTTPException(status_code=404, detail={"error": "Memory not found"})
    return _memory_to_schema(memory)


@app.delete("/memory/memories/{memory_id}")
def delete_memory(memory_id: int) -> dict[str, bool]:
    store = get_memory_store()
    deleted = store.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"error": "Memory not found"})
    return {"deleted": True}


@app.get("/memory/links", response_model=MemoryLinkListResponse)
def list_memory_links(limit: int = 100) -> MemoryLinkListResponse:
    store = get_memory_store()
    links = store.list_memory_links(limit=limit)
    return MemoryLinkListResponse(links=[_memory_link_to_schema(link) for link in links])


@app.get("/memory/mood", response_model=MoodStateSchema)
def get_mood_state() -> MoodStateSchema:
    store = get_memory_store()
    return _mood_to_schema(store.get_mood_state())


@app.get("/memory/relationship", response_model=RelationshipStateSchema)
def get_relationship_state() -> RelationshipStateSchema:
    store = get_memory_store()
    return _relationship_to_schema(store.get_relationship_state())


@app.put("/memory/mood", response_model=MoodStateSchema)
def update_mood_state(request: MoodStateUpdateRequest) -> MoodStateSchema:
    store = get_memory_store()
    mood = store.update_mood_state(
        mood=request.mood,
        energy=request.energy,
        annoyance=request.annoyance,
        boredom=request.boredom,
        worry=request.worry,
        trust=request.trust,
        loneliness=request.loneliness,
        metadata=request.metadata,
    )
    return _mood_to_schema(mood)


@app.get("/stt/status", response_model=STTStatusResponse)
def stt_status() -> STTStatusResponse:
    router = get_stt_router()
    budget = load_budget_config()
    return STTStatusResponse(
        enabled=router.is_enabled(),
        default_provider=router.config.default_provider,
        force_mock=router.config.force_mock,
        allow_cloud_stt=budget.allow_cloud_stt,
        providers=[
            STTProviderStatusSchema(
                name=status.name,
                enabled=status.enabled,
                model=status.model,
                configured=status.configured,
                api_key_present=status.api_key_present,
                placeholder=status.placeholder,
                cloud=status.cloud,
            )
            for status in router.list_status()
        ],
    )


@app.post(
    "/stt/transcribe",
    response_model=STTTranscribeResponse,
    responses={
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def stt_transcribe(
    audio: UploadFile = File(...),
    language: str | None = None,
    provider: str | None = None,
) -> STTTranscribeResponse:
    router = get_stt_router()
    payload = await audio.read()

    try:
        result = router.transcribe(
            TranscriptionRequest(
                audio_bytes=payload,
                mime_type=audio.content_type or "application/octet-stream",
                language=language,
            ),
            provider_name=provider,
        )
    except STTError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={"error": error.message, "provider": error.provider},
        ) from error

    return STTTranscribeResponse(
        provider=result.provider,
        model=result.model,
        text=result.text,
        mock=result.mock,
        language=result.language,
    )


@app.get("/tts/status", response_model=TTSStatusResponse)
def tts_status() -> TTSStatusResponse:
    router = get_tts_router()
    budget = load_budget_config()
    return TTSStatusResponse(
        enabled=router.is_enabled(),
        default_provider=router.config.default_provider,
        force_mock=router.config.force_mock,
        allow_cloud_tts=budget.allow_cloud_tts,
        max_speech_chars=router.config.max_speech_chars,
        speak_decisions=list(router.config.speak_decisions),
        providers=[
            TTSProviderStatusSchema(
                name=status.name,
                enabled=status.enabled,
                model=status.model,
                configured=status.configured,
                api_key_present=status.api_key_present,
                placeholder=status.placeholder,
                cloud=status.cloud,
            )
            for status in router.list_status()
        ],
    )


@app.post("/tts/evaluate", response_model=TTSEvaluateResponse)
def tts_evaluate(request: TTSEvaluateRequest) -> TTSEvaluateResponse:
    router = get_tts_router()
    decision = router.evaluate_policy(
        request.text,
        decision=request.decision,
        avatar_state=request.avatar_state,
        force=request.force,
    )
    return TTSEvaluateResponse(
        should_speak=decision.should_speak,
        reason=decision.reason,
    )


@app.post(
    "/tts/synthesize",
    response_model=TTSSynthesizeResponse,
    responses={
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def tts_synthesize(request: TTSSynthesizeRequest) -> TTSSynthesizeResponse:
    router = get_tts_router()
    context_texts: list[str] | None = None

    try:
        provider_name = router.resolve_provider_name(request.provider)
    except Exception:
        provider_name = None

    store = get_memory_store()
    mood = store.get_mood_state()
    relationship = store.get_relationship_state()
    projection = project_tone(
        mood,
        relationship,
        performative_active=performative_active_from_metadata(mood.metadata),
    )
    intensity = register_intensity(mood, relationship, projection)
    # speech_rate is provider-agnostic (doubao + fish_audio both read it); only
    # the doubao-specific context_texts directive phrase stays gated below.
    emotion_context_texts, speech_rate = tts_emotion_directive(
        projection,
        intensity=intensity,
    )
    if contains_tone_marker_tag(request.text):
        # Boxi already wrote an explicit pacing/volume tag — let it drive
        # delivery instead of fighting it with the mood-driven numeric rate.
        speech_rate = 0

    if provider_name == "doubao":
        doubao = router.providers.get("doubao")
        if doubao is not None and doubao.is_configured():
            context_texts = emotion_context_texts

    try:
        policy, result = router.synthesize(
            SynthesisRequest(
                text=request.text,
                decision=request.decision,
                avatar_state=request.avatar_state,
                force=request.force,
                context_texts=context_texts,
                speech_rate=speech_rate,
            ),
            provider_name=request.provider,
        )
    except TTSError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={"error": error.message, "provider": error.provider},
        ) from error

    if result is None:
        return TTSSynthesizeResponse(
            spoken=False,
            reason=policy.reason,
        )

    return TTSSynthesizeResponse(
        spoken=True,
        reason=policy.reason,
        provider=result.provider,
        model=result.model,
        mime_type=result.mime_type,
        audio_base64=base64.b64encode(result.audio_bytes).decode("ascii"),
        duration_ms=result.duration_ms,
        mock=result.mock,
    )


@app.get(
    "/tts/stream",
    response_model=None,
    responses={
        204: {"description": "Speech policy skipped playback."},
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def tts_stream(
    text: str = Query(..., min_length=1),
    decision: str | None = Query(default=None),
    avatar_state: str | None = Query(default=None),
    force: bool = Query(default=False),
    user_message: str | None = Query(default=None),
) -> StreamingResponse | Response:
    router = get_tts_router()
    context_texts: list[str] | None = None

    try:
        provider_name = router.resolve_provider_name(None)
    except Exception:
        provider_name = None

    store = get_memory_store()
    mood = store.get_mood_state()
    relationship = store.get_relationship_state()
    projection = project_tone(
        mood,
        relationship,
        performative_active=performative_active_from_metadata(mood.metadata),
    )
    intensity = register_intensity(mood, relationship, projection)
    # speech_rate is provider-agnostic (doubao + fish_audio both read it); only
    # the doubao-specific context_texts directive phrase stays gated below.
    emotion_context_texts, speech_rate = tts_emotion_directive(
        projection,
        intensity=intensity,
    )
    if contains_tone_marker_tag(text):
        # Boxi already wrote an explicit pacing/volume tag — let it drive
        # delivery instead of fighting it with the mood-driven numeric rate.
        speech_rate = 0

    if provider_name == "doubao":
        doubao = router.providers.get("doubao")
        if doubao is not None and doubao.is_configured():
            if user_message and user_message.strip():
                context_texts = [user_message.strip()]
            else:
                context_texts = emotion_context_texts

    try:
        policy, chunks = router.stream_synthesize(
            SynthesisRequest(
                text=text,
                decision=decision,
                avatar_state=avatar_state,
                force=force,
                context_texts=context_texts,
                speech_rate=speech_rate,
            ),
        )
    except TTSError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={"error": error.message, "provider": error.provider},
        ) from error

    if chunks is None:
        return Response(status_code=204)

    stream_provider = router.providers.get(provider_name) if provider_name else None
    media_type = stream_provider.stream_mime_type() if stream_provider else "audio/mpeg"

    return StreamingResponse(
        chunks,
        media_type=media_type,
        headers={"Cache-Control": "no-store"},
    )


@app.get("/files/permissions/status", response_model=FilePermissionsStatusResponse)
def file_permissions_status() -> FilePermissionsStatusResponse:
    config = load_permissions_config()
    return FilePermissionsStatusResponse(
        allowed_folders=[
            AllowedFolderSchema(
                path=folder.raw_path,
                read=folder.read,
                write=folder.write,
                resolved_path=str(folder.root),
            )
            for folder in config.allowed_folders
        ],
        deny_shell_execution=config.deny_shell_execution,
        log_file_access=config.log_file_access,
    )


@app.post("/files/check", response_model=FileAccessCheckResponse)
def check_file_access(request: FileAccessCheckRequest) -> FileAccessCheckResponse:
    gateway = get_file_gateway()
    result = gateway.check_path(request.path, request.operation)
    return FileAccessCheckResponse(
        allowed=result.allowed,
        operation=result.operation,
        requested_path=result.requested_path,
        resolved_path=result.resolved_path,
        reason=result.reason,
        matched_folder=result.matched_folder,
    )


@app.get("/files/access-log", response_model=FileAccessLogListResponse)
def list_file_access_log(limit: int = 50) -> FileAccessLogListResponse:
    store = get_memory_store()
    logs = store.list_file_access_logs(limit=limit)
    return FileAccessLogListResponse(
        logs=[
            FileAccessLogSchema(
                id=log.id,
                created_at=log.created_at,
                operation=log.operation,
                requested_path=log.requested_path,
                resolved_path=log.resolved_path,
                allowed=log.allowed,
                reason=log.reason,
            )
            for log in logs
        ]
    )


@app.get("/memory/context/preview", response_model=ContextPreviewResponse)
def preview_context(user_input: str) -> ContextPreviewResponse:
    store = get_memory_store()
    budget = load_budget_config()
    built = build_provider_context(store, user_input=user_input, budget=budget)
    return ContextPreviewResponse(
        estimated_input_tokens=built.estimated_input_tokens,
        included_memory_ids=built.included_memory_ids,
        included_message_ids=built.included_message_ids,
        summary_used=built.summary_used,
        truncated=built.truncated,
        total_stored_messages=built.total_stored_messages,
        message_count_sent=len(built.messages),
        messages=[
            ChatMessageSchema(role=message.role, content=message.content)
            for message in built.messages
        ],
    )


def _decision_to_schema(decision, *, saved_message_id: int | None = None) -> BehaviorDecisionSchema:
    return BehaviorDecisionSchema(
        decision=decision.decision,
        avatar_state=decision.avatar_state,
        should_call_llm=decision.should_call_llm,
        reason=decision.reason,
        local_response=decision.local_response,
        tone_mode=decision.tone_mode,
        saved_message_id=saved_message_id,
    )


@app.post("/behavior/evaluate", response_model=BehaviorDecisionSchema)
def evaluate_behavior_route(request: BehaviorEvaluateRequest) -> BehaviorDecisionSchema:
    store = get_memory_store()
    budget = load_budget_config()
    decision = evaluate_behavior(
        store,
        BehaviorEvent(
            event_type=request.event_type,
            user_input=request.user_input,
            metadata={"force_proactive": request.force_proactive},
        ),
        budget=budget,
    )
    if request.event_type == "proactive_check" and decision.decision == "proactive":
        decision = resolve_proactive_opener(
            store,
            decision,
            budget=budget,
            router=get_provider_router(),
        )
    if request.event_type == "idle_tick":
        resolve_idle_experience_write(store, budget=budget, router=get_provider_router())
    saved_message_id: int | None = None
    if request.event_type in {"idle_tick", "proactive_check"} and should_persist_local_behavior_line(
        decision,
    ):
        saved_message_id = persist_local_behavior_line(
            store,
            decision,
            event_type=request.event_type,
        )
        if budget.behavior_tick_retention > 0:
            store.prune_behavior_tick_messages(budget.behavior_tick_retention)
    return _decision_to_schema(decision, saved_message_id=saved_message_id)


@app.post(
    "/chat/complete",
    response_model=ChatCompleteResponse,
    responses={
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def chat_complete(
    request: ChatCompleteRequest,
    background_tasks: BackgroundTasks,
) -> ChatCompleteResponse:
    router = get_provider_router()
    store = get_memory_store()
    budget = load_budget_config()

    try:
        user_input = extract_latest_user_input(
            [ChatMessage(role=message.role, content=message.content) for message in request.messages]
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"error": str(error)}) from error

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="user_message", user_input=user_input),
    )
    final_decision = decision.decision
    called_llm = False
    reply_signals: dict | None = None

    if decision.should_call_llm:
        # Resolve the target model first so the spend brake can also veto pricier
        # reasoning models before any provider call happens.
        try:
            target_model = router.get_provider(request.provider).status().model
        except ProviderError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail={"error": error.message, "provider": error.provider},
            ) from error

        gate = evaluate_llm_budget_gate(store, budget, target_model=target_model)
        if not gate.allowed:
            # Spend brake tripped: answer locally, never touch the provider.
            result = build_budget_block_completion(gate.block_line or "预算用完了，先省着点。")
            avatar_state = "annoyed"
            final_decision = "refuse"
        else:
            built = build_provider_context(
                store,
                user_input=user_input,
                budget=budget,
                behavior=decision,
            )
            completion_request = ChatCompletionRequest(
                messages=built.messages,
                max_output_tokens=budget.max_output_tokens_per_turn,
            )

            try:
                result = router.complete(completion_request, provider_name=request.provider)
            except ProviderError as error:
                raise HTTPException(
                    status_code=error.status_code,
                    detail={"error": error.message, "provider": error.provider},
                ) from error

            parsed = parse_structured_assistant_response(result.content)
            reply_signals = parsed.signals
            avatar_state = parsed.avatar_state or (
                "talking" if decision.decision in {"reply", "interrupt"} else decision.avatar_state
            )
            if parsed.decision:
                final_decision = parsed.decision
            called_llm = True
            try:
                apply_signals_to_kernel(store, parsed.signals)
            except Exception:
                pass
            tagged_content = apply_expression_tags(
                parsed.content,
                store.get_mood_state(),
                router=router,
            )
            result = type(result)(
                provider=result.provider,
                model=result.model,
                content=tagged_content,
                usage=result.usage,
                cost=result.cost,
                mock=result.mock,
            )
    else:
        result = build_local_completion(decision, user_input=user_input)
        avatar_state = decision.avatar_state

    saved_ids = persist_chat_turn(
        store,
        [ChatMessageSchema(role="user", content=user_input)],
        result,
        decision=final_decision,
        avatar_state=avatar_state,
        should_call_llm=called_llm,
    )
    user_message_id = saved_ids[0] if user_input.strip() and saved_ids else None
    try:
        record_turn_memories(
            store,
            user_input=user_input,
            signals=reply_signals,
            source_message_id=user_message_id,
            budget=budget,
        )
    except Exception:
        pass
    maybe_update_conversation_summary(store, budget=budget)

    if called_llm:
        store.note_llm_turn()
        background_tasks.add_task(run_reflection_if_due, store, budget)

    return ChatCompleteResponse(
        provider=result.provider,
        model=result.model,
        content=result.content,
        usage=TokenUsageSchema(
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            total_tokens=result.usage.total_tokens,
        ),
        cost=CostEstimateSchema(
            input_usd=result.cost.input_usd,
            output_usd=result.cost.output_usd,
            total_usd=result.cost.total_usd,
            pricing_source=result.cost.pricing_source,
        ),
        mock=result.mock,
        avatar_state=avatar_state,
        decision=final_decision,
        should_call_llm=called_llm,
    )


def _sse_data(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chat_stream_done_meta(
    result: ChatCompletionResult,
    *,
    avatar_state: str,
    decision: str,
    should_call_llm: bool,
) -> dict[str, object]:
    return {
        "provider": result.provider,
        "model": result.model,
        "content": result.content,
        "decision": decision,
        "avatar_state": avatar_state,
        "should_call_llm": should_call_llm,
        "usage": {
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
            "total_tokens": result.usage.total_tokens,
        },
        "cost": {
            "input_usd": result.cost.input_usd,
            "output_usd": result.cost.output_usd,
            "total_usd": result.cost.total_usd,
            "pricing_source": result.cost.pricing_source,
        },
    }


def _finalize_streamed_turn(
    store,
    budget,
    *,
    user_input: str,
    accumulated_text: str,
    provider_name: str,
    model: str,
    usage,
    mock: bool,
    decision: str,
    avatar_state: str,
    should_call_llm: bool,
) -> ChatCompletionResult:
    cost = estimate_cost(model, usage)
    result = ChatCompletionResult(
        provider=provider_name,
        model=model,
        content=accumulated_text,
        usage=usage,
        cost=cost,
        mock=mock,
    )
    parsed = parse_structured_assistant_response(result.content)
    try:
        apply_signals_to_kernel(store, parsed.signals)
    except Exception:
        pass
    final_avatar_state = parsed.avatar_state or avatar_state
    final_decision = parsed.decision or decision
    final_content = apply_expression_tags(
        parsed.content,
        store.get_mood_state(),
        router=get_provider_router(),
    )
    result = ChatCompletionResult(
        provider=result.provider,
        model=result.model,
        content=final_content,
        usage=result.usage,
        cost=result.cost,
        mock=result.mock,
    )
    saved_ids = persist_chat_turn(
        store,
        [ChatMessageSchema(role="user", content=user_input)],
        result,
        decision=final_decision,
        avatar_state=final_avatar_state,
        should_call_llm=should_call_llm,
    )
    user_message_id = saved_ids[0] if user_input.strip() and saved_ids else None
    try:
        record_turn_memories(
            store,
            user_input=user_input,
            signals=parsed.signals,
            source_message_id=user_message_id,
            budget=budget,
        )
    except Exception:
        pass
    maybe_update_conversation_summary(store, budget=budget)
    return ChatCompletionResult(
        provider=result.provider,
        model=result.model,
        content=result.content,
        usage=result.usage,
        cost=result.cost,
        mock=result.mock,
    )


@app.post(
    "/chat/stream",
    response_model=None,
    responses={
        400: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def chat_stream(request: ChatCompleteRequest) -> StreamingResponse:
    router = get_provider_router()
    store = get_memory_store()
    budget = load_budget_config()

    try:
        user_input = extract_latest_user_input(
            [ChatMessage(role=message.role, content=message.content) for message in request.messages]
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"error": str(error)}) from error

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="user_message", user_input=user_input),
    )

    def event_generator() -> Iterator[str]:
        final_decision = decision.decision
        called_llm = False
        avatar_state = decision.avatar_state
        result: ChatCompletionResult | None = None

        try:
            if decision.should_call_llm:
                try:
                    target_model = router.get_provider(request.provider).status().model
                except ProviderError as error:
                    yield _sse_data({"type": "error", "message": error.message})
                    return

                gate = evaluate_llm_budget_gate(store, budget, target_model=target_model)
                if not gate.allowed:
                    result = build_budget_block_completion(gate.block_line or "预算用完了，先省着点。")
                    avatar_state = "annoyed"
                    final_decision = "refuse"
                    yield _sse_data({"type": "delta", "text": result.content})
                    saved_ids = persist_chat_turn(
                        store,
                        [ChatMessageSchema(role="user", content=user_input)],
                        result,
                        decision=final_decision,
                        avatar_state=avatar_state,
                        should_call_llm=False,
                    )
                    user_message_id = saved_ids[0] if user_input.strip() and saved_ids else None
                    maybe_write_memories_from_turn(
                        store,
                        user_input=user_input,
                        source_message_id=user_message_id,
                        budget=budget,
                    )
                    maybe_update_conversation_summary(store, budget=budget)
                    yield _sse_data(
                        {
                            "type": "done",
                            "meta": _chat_stream_done_meta(
                                result,
                                avatar_state=avatar_state,
                                decision=final_decision,
                                should_call_llm=False,
                            ),
                        },
                    )
                    return

                built = build_provider_context(
                    store,
                    user_input=user_input,
                    budget=budget,
                    behavior=decision,
                )
                completion_request = ChatCompletionRequest(
                    messages=built.messages,
                    max_output_tokens=budget.max_output_tokens_per_turn,
                )

                provider = router.get_provider(request.provider)
                provider_status = provider.status()
                accumulated_parts: list[str] = []
                stream_usage = None
                signal_filter = SignalStreamFilter()
                try:
                    for chunk_kind, chunk_value in router.complete_stream(
                        completion_request,
                        provider_name=request.provider,
                    ):
                        if chunk_kind == "delta":
                            accumulated_parts.append(chunk_value)
                            visible = signal_filter.feed(chunk_value)
                            if visible:
                                yield _sse_data({"type": "delta", "text": visible})
                        elif chunk_kind == "usage":
                            stream_usage = chunk_value
                finally:
                    tail = signal_filter.flush()
                    if tail:
                        yield _sse_data({"type": "delta", "text": tail})

                if stream_usage is None:
                    yield _sse_data({"type": "error", "message": "Provider stream ended without usage."})
                    return

                accumulated_text = "".join(accumulated_parts)
                result = _finalize_streamed_turn(
                    store,
                    budget,
                    user_input=user_input,
                    accumulated_text=accumulated_text,
                    provider_name=provider_status.name,
                    model=provider_status.model,
                    usage=stream_usage,
                    mock=provider_status.name == "mock",
                    decision=decision.decision,
                    avatar_state=(
                        "talking" if decision.decision in {"reply", "interrupt"} else decision.avatar_state
                    ),
                    should_call_llm=True,
                )
                called_llm = True
                store.note_llm_turn()
                parsed = parse_structured_assistant_response(accumulated_text)
                final_decision = parsed.decision or decision.decision
                avatar_state = parsed.avatar_state or (
                    "talking" if decision.decision in {"reply", "interrupt"} else decision.avatar_state
                )
            else:
                result = build_local_completion(decision, user_input=user_input)
                avatar_state = decision.avatar_state
                yield _sse_data({"type": "delta", "text": result.content})
                saved_ids = persist_chat_turn(
                    store,
                    [ChatMessageSchema(role="user", content=user_input)],
                    result,
                    decision=final_decision,
                    avatar_state=avatar_state,
                    should_call_llm=False,
                )
                user_message_id = saved_ids[0] if user_input.strip() and saved_ids else None
                maybe_write_memories_from_turn(
                    store,
                    user_input=user_input,
                    source_message_id=user_message_id,
                    budget=budget,
                )
                maybe_update_conversation_summary(store, budget=budget)

            if result is None:
                yield _sse_data({"type": "error", "message": "No completion result produced."})
                return

            yield _sse_data(
                {
                    "type": "done",
                    "meta": _chat_stream_done_meta(
                        result,
                        avatar_state=avatar_state,
                        decision=final_decision,
                        should_call_llm=called_llm,
                    ),
                },
            )
        except ProviderError as error:
            yield _sse_data({"type": "error", "message": error.message})
            return
        except Exception as error:
            yield _sse_data({"type": "error", "message": str(error)})
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        background=BackgroundTask(run_reflection_if_due, store, budget),
    )
