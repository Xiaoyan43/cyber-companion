from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.app.memory.budget import BudgetConfig, load_budget_config
from backend.app.memory.store import MemoryStore
from backend.app.rtc.client import RtcApiError, start_voice_chat, stop_voice_chat, update_voice_chat
from backend.app.rtc.config import (
    RtcConfig,
    base_rtc_ready,
    load_rtc_config,
    missing_for_mode,
    mode_ready,
    resolve_rtc_user_id,
    viking_memory_enabled,
    viking_memory_write_ready,
)
from backend.app.memory.store import get_memory_store
from backend.app.rtc.sqlite_memory import load_sqlite_memory_context, sqlite_memory_has_content
from backend.app.rtc.state_block import (
    build_rtc_emotion_tag,
    build_rtc_speaking_style,
    build_rtc_state_block,
    build_rtc_welcome_message,
)
from backend.app.rtc.token import mint_rtc_token
from backend.app.rtc.viking_memory import (
    VikingMemoryError,
    add_memory_session,
    format_memories_for_system_role,
    merge_subtitle_turns,
    search_user_memories,
)
from backend.app.rtc.voice_chat import mode_meta
from backend.app.reflection.turn_analyzer import analyze_turn
from backend.app.schemas import (
    RtcAgentStartRequest,
    RtcMemorySessionRequest,
    RtcMemorySessionResponse,
    RtcModeSchema,
    RtcPrepareRequest,
    RtcPrepareResponse,
    RtcStatusResponse,
    RtcStopRequest,
    RtcStopResponse,
    RtcTurnRequest,
    RtcTurnResponse,
)

router = APIRouter(prefix="/rtc", tags=["rtc"])
logger = logging.getLogger(__name__)


def _run_turn_analysis(
    store: MemoryStore,
    *,
    room_id: str,
    user_text: str,
    bot_text: str,
    budget: BudgetConfig,
) -> None:
    try:
        analyze_turn(store, user_text=user_text, bot_text=bot_text, budget=budget)
        emotion_message = build_rtc_emotion_tag(store)
        if emotion_message:
            config = load_rtc_config()
            if mode_ready(config, "pure"):
                try:
                    update_voice_chat(
                        config,
                        mode="pure",
                        room_id=room_id,
                        command="SetTTSContext",
                        message=emotion_message,
                    )
                    logger.info(
                        "RTC SetTTSContext injected room=%s chars=%d",
                        room_id,
                        len(emotion_message),
                    )
                except Exception:
                    logger.exception("RTC SetTTSContext failed for room=%s", room_id)
    finally:
        store.release_turn_analysis(room_id)


def _merge_memory_context(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip())


def _resolve_rtc_welcome_message(config: RtcConfig, mode: RtcModeSchema, store: MemoryStore) -> str:
    _, _, _, default = mode_meta(config, mode)
    if mode != "pure":
        return default
    welcome = build_rtc_welcome_message(store, default=default)
    return welcome


def _load_rtc_memory_context(config: RtcConfig, user_id: str) -> str:
    store = get_memory_store()
    state_block = build_rtc_state_block(store)
    sqlite_context = load_sqlite_memory_context(store)
    if state_block:
        logger.info("RTC state block inject chars=%d", len(state_block))
    if sqlite_context:
        logger.info("SQLite memory inject chars=%d", len(sqlite_context))
    viking_context = _load_viking_memory_context(config, user_id)
    return _merge_memory_context(state_block, sqlite_context, viking_context)


def _load_viking_memory_context(config: RtcConfig, user_id: str) -> str:
    if not viking_memory_write_ready(config):
        return ""
    try:
        hits = search_user_memories(config, user_id)
        context = format_memories_for_system_role(hits)
        logger.info(
            "Viking memory inject user=%s hits=%d chars=%d",
            user_id,
            len(hits),
            len(context),
        )
        return context
    except VikingMemoryError as error:
        logger.warning("Viking memory search failed for user=%s: %s", user_id, error)
        return ""


@router.get("/stance-preview")
def rtc_stance_preview() -> dict[str, str]:
    """Current kernel → join-time inject lines (for E2E weight experiments)."""
    store = get_memory_store()
    config = load_rtc_config()
    _, _, _, default = mode_meta(config, "pure")
    return {
        "default_welcome": default,
        "welcome_message": _resolve_rtc_welcome_message(config, "pure", store),
        "state_block": build_rtc_state_block(store),
        "speaking_style": build_rtc_speaking_style(store),
        "emotion_tag": build_rtc_emotion_tag(store) or "",
    }


@router.get("/status", response_model=RtcStatusResponse)
def rtc_status() -> RtcStatusResponse:
    config = load_rtc_config()
    store = get_memory_store()
    return RtcStatusResponse(
        base_configured=base_rtc_ready(config),
        pure_ready=mode_ready(config, "pure"),
        hybrid_ready=mode_ready(config, "hybrid"),
        missing_pure=missing_for_mode(config, "pure") if not mode_ready(config, "pure") else [],
        missing_hybrid=missing_for_mode(config, "hybrid")
        if not mode_ready(config, "hybrid")
        else [],
        viking_memory_enabled=viking_memory_enabled(config),
        viking_memory_write_ready=viking_memory_write_ready(config),
        sqlite_memory_ready=sqlite_memory_has_content(store),
        default_user_id=config.default_user_id,
    )


@router.post("/prepare", response_model=RtcPrepareResponse)
def rtc_prepare(payload: RtcPrepareRequest) -> RtcPrepareResponse:
    """Mint RTC join credentials only — StartVoiceChat runs after the client joins the room."""
    config = load_rtc_config()
    mode: RtcModeSchema = payload.mode
    if not mode_ready(config, mode):
        missing = ", ".join(missing_for_mode(config, mode))
        raise HTTPException(status_code=503, detail=f"RTC not configured for {mode}: {missing}")

    room_id = payload.room_id.strip() or str(uuid.uuid4())
    user_id = resolve_rtc_user_id(payload.user_id, config)
    token = mint_rtc_token(
        app_id=config.rtc_app_id,
        app_key=config.rtc_app_key,
        room_id=room_id,
        user_id=user_id,
    )

    store = get_memory_store()
    output_mode, bot_user_id, task_id, _ = mode_meta(config, mode)
    welcome_message = _resolve_rtc_welcome_message(config, mode, store)
    return RtcPrepareResponse(
        mode=mode,
        output_mode=output_mode,
        app_id=config.rtc_app_id,
        room_id=room_id,
        user_id=user_id,
        token=token,
        bot_user_id=bot_user_id,
        task_id=task_id,
        welcome_message=welcome_message,
    )


@router.post("/start", response_model=RtcPrepareResponse)
def rtc_start_legacy(payload: RtcPrepareRequest) -> RtcPrepareResponse:
    """Legacy clients (Stage 2c v1) called /rtc/start with StartVoiceChat inline.

    New clients should use /rtc/prepare → joinRoom → /rtc/agent/start.
    """
    prepared = rtc_prepare(payload)
    config = load_rtc_config()
    mode: RtcModeSchema = payload.mode
    store = get_memory_store()
    welcome_message = _resolve_rtc_welcome_message(config, mode, store)
    try:
        start_voice_chat(
            config,
            mode=mode,
            room_id=prepared.room_id,
            target_user_id=prepared.user_id,
            memory_context=_load_rtc_memory_context(config, prepared.user_id),
            welcome_message=welcome_message,
        )
    except RtcApiError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return prepared


@router.post("/agent/start")
def rtc_agent_start(payload: RtcAgentStartRequest) -> dict[str, str]:
    """Start cloud AIGC agent — call after the browser has joined the RTC room."""
    config = load_rtc_config()
    mode: RtcModeSchema = payload.mode
    if not mode_ready(config, mode):
        missing = ", ".join(missing_for_mode(config, mode))
        raise HTTPException(status_code=503, detail=f"RTC not configured for {mode}: {missing}")

    room_id = payload.room_id.strip()
    user_id = payload.user_id.strip()
    if not room_id or not user_id:
        raise HTTPException(status_code=400, detail="room_id and user_id are required")

    store = get_memory_store()
    welcome_message = _resolve_rtc_welcome_message(config, mode, store)
    try:
        start_voice_chat(
            config,
            mode=mode,
            room_id=room_id,
            target_user_id=user_id,
            memory_context=_load_rtc_memory_context(config, user_id),
            welcome_message=welcome_message,
        )
    except RtcApiError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    logger.info("RTC welcome_message chars=%d", len(welcome_message))
    return {"status": "ok", "welcome_message": welcome_message}


@router.post("/stop", response_model=RtcStopResponse)
def rtc_stop(payload: RtcStopRequest) -> RtcStopResponse:
    config = load_rtc_config()
    mode: RtcModeSchema = payload.mode
    if not mode_ready(config, mode):
        missing = ", ".join(missing_for_mode(config, mode))
        raise HTTPException(status_code=503, detail=f"RTC not configured for {mode}: {missing}")

    room_id = payload.room_id.strip()
    if not room_id:
        raise HTTPException(status_code=400, detail="room_id is required")

    try:
        stop_voice_chat(config, mode=mode, room_id=room_id)
    except RtcApiError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return RtcStopResponse(stopped=True, mode=mode, room_id=room_id)


@router.post("/turn", response_model=RtcTurnResponse)
def rtc_turn(payload: RtcTurnRequest, background_tasks: BackgroundTasks) -> RtcTurnResponse:
    """Off-path soul write for a completed pure-E2E voice turn (PS-2)."""
    room_id = payload.room_id.strip()
    user_id = payload.user_id.strip()
    user_text = payload.user_text.strip()
    bot_text = payload.bot_text.strip()
    if not room_id or not user_id or not user_text or not bot_text:
        raise HTTPException(
            status_code=400,
            detail="room_id, user_id, user_text, and bot_text are required",
        )

    store = get_memory_store()
    if not store.claim_turn_analysis(room_id):
        return RtcTurnResponse(status="ok")

    budget = load_budget_config()
    background_tasks.add_task(
        _run_turn_analysis,
        store,
        room_id=room_id,
        user_text=user_text,
        bot_text=bot_text,
        budget=budget,
    )
    return RtcTurnResponse(status="ok")


@router.post("/memory/session", response_model=RtcMemorySessionResponse)
def rtc_memory_session(payload: RtcMemorySessionRequest) -> RtcMemorySessionResponse:
    """Persist RTC subtitles to Viking via AddSession (off-path, after voice ends)."""
    config = load_rtc_config()
    if not viking_memory_write_ready(config):
        raise HTTPException(
            status_code=503,
            detail="Viking memory write not configured (VIKING_MEMORY_COLLECTION + VIKING_MEMORY_API_KEY)",
        )

    user_id = payload.user_id.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    subtitles = [
        {"speaker": item.speaker, "text": item.text}
        for item in payload.subtitles
        if item.text.strip()
    ]
    messages = merge_subtitle_turns(subtitles)
    if not messages:
        raise HTTPException(status_code=400, detail="No subtitle transcript to save")

    try:
        result = add_memory_session(
            config,
            user_id=user_id,
            bot_user_id=payload.bot_user_id.strip(),
            messages=messages,
        )
    except VikingMemoryError as error:
        status = 502 if error.status_code is None else min(error.status_code, 599)
        raise HTTPException(status_code=status, detail=str(error)) from error

    return RtcMemorySessionResponse(
        saved=True,
        session_id=result["session_id"],
        message_count=result["message_count"],
    )
