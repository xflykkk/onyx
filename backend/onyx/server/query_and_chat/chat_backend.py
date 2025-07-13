import asyncio
import datetime
import io
import json
import os
import time
from collections.abc import Callable
from collections.abc import Generator
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi import UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from onyx.auth.users import current_chat_accessible_user
from onyx.auth.users import current_user
from onyx.chat.chat_utils import create_chat_chain
from onyx.chat.chat_utils import extract_headers
from onyx.chat.process_message import stream_chat_message
from onyx.chat.prompt_builder.citations_prompt import (
    compute_max_document_tokens_for_persona,
)
from onyx.configs.app_configs import WEB_DOMAIN
from onyx.configs.chat_configs import HARD_DELETE_CHATS
from onyx.utils.stream_logger import create_stream_logger_wrapper, create_request_info
from onyx.configs.constants import DocumentSource
from onyx.configs.constants import FileOrigin
from onyx.configs.constants import MessageType
from onyx.configs.constants import MilestoneRecordType
from onyx.configs.model_configs import LITELLM_PASS_THROUGH_HEADERS
from onyx.connectors.models import InputType
from onyx.db.chat import add_chats_to_session_from_slack_thread
from onyx.db.chat import create_chat_session
from onyx.db.chat import create_new_chat_message
from onyx.db.chat import delete_all_chat_sessions_for_user
from onyx.db.chat import delete_chat_session
from onyx.db.chat import duplicate_chat_session_for_user_from_slack
from onyx.db.chat import get_chat_message
from onyx.db.chat import get_chat_messages_by_session
from onyx.db.chat import get_chat_session_by_id
from onyx.db.chat import get_chat_sessions_by_user
from onyx.db.chat import get_or_create_root_message
from onyx.db.chat import set_as_latest_chat_message
from onyx.db.chat import translate_db_message_to_chat_message_detail
from onyx.db.chat import update_chat_session
from onyx.db.chat_search import search_chat_sessions
from onyx.db.connector import create_connector
from onyx.db.connector_credential_pair import add_credential_to_connector
from onyx.db.credentials import create_credential
from onyx.db.engine.sql_engine import get_session
from onyx.db.engine.sql_engine import get_session_with_tenant
from onyx.db.enums import AccessType
from onyx.db.feedback import create_chat_message_feedback
from onyx.db.feedback import create_doc_retrieval_feedback
from onyx.db.models import User
from onyx.db.persona import get_persona_by_id
from onyx.db.user_documents import create_user_files
from onyx.file_processing.extract_file_text import docx_to_txt_filename
from onyx.file_processing.extract_file_text import extract_file_text
from onyx.file_store.file_store import get_default_file_store
from onyx.file_store.models import ChatFileType
from onyx.file_store.models import FileDescriptor
from onyx.llm.exceptions import GenAIDisabledException
from onyx.llm.factory import get_default_llms
from onyx.llm.factory import get_llms_for_persona
from onyx.natural_language_processing.utils import get_tokenizer
from onyx.secondary_llm_flows.chat_session_naming import (
    get_renamed_conversation_name,
)
from onyx.server.documents.models import ConnectorBase
from onyx.server.documents.models import CredentialBase
from onyx.server.query_and_chat.chat_utils import mime_type_to_chat_file_type
from onyx.server.query_and_chat.models import ChatFeedbackRequest
from onyx.server.query_and_chat.models import ChatMessageIdentifier
from onyx.server.query_and_chat.models import ChatRenameRequest
from onyx.server.query_and_chat.models import ChatSearchResponse
from onyx.server.query_and_chat.models import ChatSessionCreationRequest
from onyx.server.query_and_chat.models import ChatSessionDetailResponse
from onyx.server.query_and_chat.models import ChatSessionDetails
from onyx.server.query_and_chat.models import ChatSessionGroup
from onyx.server.query_and_chat.models import ChatSessionsResponse
from onyx.server.query_and_chat.models import ChatSessionSummary
from onyx.server.query_and_chat.models import ChatSessionUpdateRequest
from onyx.server.query_and_chat.models import CreateChatMessageRequest
from onyx.server.query_and_chat.models import CreateChatSessionID
from onyx.server.query_and_chat.models import LLMOverride
from onyx.server.query_and_chat.models import PromptOverride
from onyx.server.query_and_chat.models import RenameChatSessionResponse
from onyx.server.query_and_chat.models import SearchFeedbackRequest
from onyx.server.query_and_chat.models import UpdateChatSessionTemperatureRequest
from onyx.server.query_and_chat.models import UpdateChatSessionThreadRequest
from onyx.server.query_and_chat.token_limit import check_token_rate_limits
from onyx.utils.file_types import UploadMimeTypes
from onyx.utils.headers import get_custom_tool_additional_request_headers
from onyx.utils.logger import setup_logger
from onyx.utils.telemetry import create_milestone_and_report
from shared_configs.contextvars import get_current_tenant_id

RECENT_DOCS_FOLDER_ID = -1

logger = setup_logger()

router = APIRouter(prefix="/chat")


@router.get("/get-user-chat-sessions")
def get_user_chat_sessions(
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> ChatSessionsResponse:
    user_id = user.id if user is not None else None

    try:
        chat_sessions = get_chat_sessions_by_user(
            user_id=user_id, deleted=False, db_session=db_session
        )

    except ValueError:
        raise ValueError("Chat session does not exist or has been deleted")

    return ChatSessionsResponse(
        sessions=[
            ChatSessionDetails(
                id=chat.id,
                name=chat.description,
                persona_id=chat.persona_id,
                time_created=chat.time_created.isoformat(),
                time_updated=chat.time_updated.isoformat(),
                shared_status=chat.shared_status,
                folder_id=chat.folder_id,
                current_alternate_model=chat.current_alternate_model,
                current_temperature_override=chat.temperature_override,
            )
            for chat in chat_sessions
        ]
    )


@router.put("/update-chat-session-temperature")
def update_chat_session_temperature(
    update_thread_req: UpdateChatSessionTemperatureRequest,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    chat_session = get_chat_session_by_id(
        chat_session_id=update_thread_req.chat_session_id,
        user_id=user.id if user is not None else None,
        db_session=db_session,
    )

    # Validate temperature_override
    if update_thread_req.temperature_override is not None:
        if (
            update_thread_req.temperature_override < 0
            or update_thread_req.temperature_override > 2
        ):
            raise HTTPException(
                status_code=400, detail="Temperature must be between 0 and 2"
            )

        # Additional check for Anthropic models
        if (
            chat_session.current_alternate_model
            and "anthropic" in chat_session.current_alternate_model.lower()
        ):
            if update_thread_req.temperature_override > 1:
                raise HTTPException(
                    status_code=400,
                    detail="Temperature for Anthropic models must be between 0 and 1",
                )

    chat_session.temperature_override = update_thread_req.temperature_override

    db_session.add(chat_session)
    db_session.commit()


@router.put("/update-chat-session-model")
def update_chat_session_model(
    update_thread_req: UpdateChatSessionThreadRequest,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    chat_session = get_chat_session_by_id(
        chat_session_id=update_thread_req.chat_session_id,
        user_id=user.id if user is not None else None,
        db_session=db_session,
    )
    chat_session.current_alternate_model = update_thread_req.new_alternate_model

    db_session.add(chat_session)
    db_session.commit()


@router.get("/get-chat-session/{session_id}")
def get_chat_session(
    session_id: UUID,
    is_shared: bool = False,
    include_deleted: bool = False,
    user: User | None = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
) -> ChatSessionDetailResponse:
    user_id = user.id if user is not None else None
    try:
        chat_session = get_chat_session_by_id(
            chat_session_id=session_id,
            user_id=user_id,
            db_session=db_session,
            is_shared=is_shared,
            include_deleted=include_deleted,
        )
    except ValueError:
        raise ValueError("Chat session does not exist or has been deleted")

    # for chat-seeding: if the session is unassigned, assign it now. This is done here
    # to avoid another back and forth between FE -> BE before starting the first
    # message generation
    if chat_session.user_id is None and user_id is not None:
        chat_session.user_id = user_id
        db_session.commit()

    session_messages = get_chat_messages_by_session(
        chat_session_id=session_id,
        user_id=user_id,
        db_session=db_session,
        # we already did a permission check above with the call to
        # `get_chat_session_by_id`, so we can skip it here
        skip_permission_check=True,
        # we need the tool call objs anyways, so just fetch them in a single call
        prefetch_tool_calls=True,
    )

    return ChatSessionDetailResponse(
        chat_session_id=session_id,
        description=chat_session.description,
        persona_id=chat_session.persona_id,
        persona_name=chat_session.persona.name if chat_session.persona else None,
        persona_icon_color=(
            chat_session.persona.icon_color if chat_session.persona else None
        ),
        persona_icon_shape=(
            chat_session.persona.icon_shape if chat_session.persona else None
        ),
        current_alternate_model=chat_session.current_alternate_model,
        messages=[
            translate_db_message_to_chat_message_detail(msg) for msg in session_messages
        ],
        time_created=chat_session.time_created,
        shared_status=chat_session.shared_status,
        current_temperature_override=chat_session.temperature_override,
        deleted=chat_session.deleted,
    )


@router.post("/create-chat-session")
def create_new_chat_session(
    chat_session_creation_request: ChatSessionCreationRequest,
    user: User | None = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
) -> CreateChatSessionID:
    user_id = user.id if user is not None else None
    try:
        new_chat_session = create_chat_session(
            db_session=db_session,
            description=chat_session_creation_request.description
            or "",  # Leave the naming till later to prevent delay
            user_id=user_id,
            persona_id=chat_session_creation_request.persona_id,
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=400, detail="Invalid Persona provided.")

    return CreateChatSessionID(chat_session_id=new_chat_session.id)


@router.put("/rename-chat-session")
def rename_chat_session(
    rename_req: ChatRenameRequest,
    request: Request,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> RenameChatSessionResponse:
    name = rename_req.name
    chat_session_id = rename_req.chat_session_id
    user_id = user.id if user is not None else None

    if name:
        update_chat_session(
            db_session=db_session,
            user_id=user_id,
            chat_session_id=chat_session_id,
            description=name,
        )
        return RenameChatSessionResponse(new_name=name)

    final_msg, history_msgs = create_chat_chain(
        chat_session_id=chat_session_id, db_session=db_session
    )
    full_history = history_msgs + [final_msg]

    try:
        llm, _ = get_default_llms(
            additional_headers=extract_headers(
                request.headers, LITELLM_PASS_THROUGH_HEADERS
            )
        )
    except GenAIDisabledException:
        # This may be longer than what the LLM tends to produce but is the most
        # clear thing we can do
        return RenameChatSessionResponse(new_name=full_history[0].message)

    new_name = get_renamed_conversation_name(full_history=full_history, llm=llm)

    update_chat_session(
        db_session=db_session,
        user_id=user_id,
        chat_session_id=chat_session_id,
        description=new_name,
    )

    return RenameChatSessionResponse(new_name=new_name)


@router.patch("/chat-session/{session_id}")
def patch_chat_session(
    session_id: UUID,
    chat_session_update_req: ChatSessionUpdateRequest,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    user_id = user.id if user is not None else None
    update_chat_session(
        db_session=db_session,
        user_id=user_id,
        chat_session_id=session_id,
        sharing_status=chat_session_update_req.sharing_status,
    )
    return None


@router.delete("/delete-all-chat-sessions")
def delete_all_chat_sessions(
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    try:
        delete_all_chat_sessions_for_user(user=user, db_session=db_session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/delete-chat-session/{session_id}")
def delete_chat_session_by_id(
    session_id: UUID,
    hard_delete: bool | None = None,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    user_id = user.id if user is not None else None
    try:
        # Use the provided hard_delete parameter if specified, otherwise use the default config
        actual_hard_delete = (
            hard_delete if hard_delete is not None else HARD_DELETE_CHATS
        )
        delete_chat_session(
            user_id, session_id, db_session, hard_delete=actual_hard_delete
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def is_connected(request: Request) -> Callable[[], bool]:
    main_loop = asyncio.get_event_loop()

    def is_connected_sync() -> bool:
        future = asyncio.run_coroutine_threadsafe(request.is_disconnected(), main_loop)
        try:
            is_connected = not future.result(timeout=0.05)
            return is_connected
        except asyncio.TimeoutError:
            logger.warning(
                "Asyncio timed out (potentially missed request to stop streaming)"
            )
            return True
        except Exception as e:
            error_msg = str(e)
            logger.critical(
                f"An unexpected error occured with the disconnect check coroutine: {error_msg}"
            )
            return True

    return is_connected_sync


@router.post("/send-message")
def handle_new_chat_message(
    chat_message_req: CreateChatMessageRequest,
    request: Request,
    user: User | None = Depends(current_chat_accessible_user),
    _rate_limit_check: None = Depends(check_token_rate_limits),
    is_connected_func: Callable[[], bool] = Depends(is_connected),
) -> StreamingResponse:
    """
    This endpoint is both used for all the following purposes:
    - Sending a new message in the session
    - Regenerating a message in the session (just send the same one again)
    - Editing a message (similar to regenerating but sending a different message)
    - Kicking off a seeded chat session (set `use_existing_user_message`)

    Assumes that previous messages have been set as the latest to minimize overhead.

    Args:
        chat_message_req (CreateChatMessageRequest): Details about the new chat message.
        request (Request): The current HTTP request context.
        user (User | None): The current user, obtained via dependency injection.
        _ (None): Rate limit check is run if user/group/global rate limits are enabled.
        is_connected_func (Callable[[], bool]): Function to check client disconnection,
            used to stop the streaming response if the client disconnects.

    Returns:
        StreamingResponse: Streams the response to the new chat message.
    """
    tenant_id = get_current_tenant_id()
    logger.debug(f"Received new chat message: {chat_message_req.message}")

    if (
        not chat_message_req.message
        and chat_message_req.prompt_id is not None
        and not chat_message_req.use_existing_user_message
    ):
        raise HTTPException(status_code=400, detail="Empty chat message is invalid")

    with get_session_with_tenant(tenant_id=tenant_id) as db_session:
        create_milestone_and_report(
            user=user,
            distinct_id=user.email if user else tenant_id or "N/A",
            event_type=MilestoneRecordType.RAN_QUERY,
            properties=None,
            db_session=db_session,
        )

    def stream_generator() -> Generator[str, None, None]:
        try:
            for packet in stream_chat_message(
                new_msg_req=chat_message_req,
                user=user,
                litellm_additional_headers=extract_headers(
                    request.headers, LITELLM_PASS_THROUGH_HEADERS
                ),
                custom_tool_additional_headers=get_custom_tool_additional_request_headers(
                    request.headers
                ),
                is_connected=is_connected_func,
            ):
                yield packet

        except Exception as e:
            logger.exception("Error in chat message streaming")
            yield json.dumps({"error": str(e)})

        finally:
            logger.debug("Stream generator finished")

    # 创建请求信息用于日志记录
    request_info = create_request_info(
        chat_message_req=chat_message_req,
        user=user,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown")
    )
    
    # 包装流生成器，添加日志记录
    logged_stream = create_stream_logger_wrapper(stream_generator(), request_info)
    
    return StreamingResponse(logged_stream, media_type="text/event-stream")


@router.put("/set-message-as-latest")
def set_message_as_latest(
    message_identifier: ChatMessageIdentifier,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    user_id = user.id if user is not None else None

    chat_message = get_chat_message(
        chat_message_id=message_identifier.message_id,
        user_id=user_id,
        db_session=db_session,
    )

    set_as_latest_chat_message(
        chat_message=chat_message,
        user_id=user_id,
        db_session=db_session,
    )


@router.post("/create-chat-message-feedback")
def create_chat_feedback(
    feedback: ChatFeedbackRequest,
    user: User | None = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
) -> None:
    user_id = user.id if user else None

    create_chat_message_feedback(
        is_positive=feedback.is_positive,
        feedback_text=feedback.feedback_text,
        predefined_feedback=feedback.predefined_feedback,
        chat_message_id=feedback.chat_message_id,
        user_id=user_id,
        db_session=db_session,
    )


@router.post("/document-search-feedback")
def create_search_feedback(
    feedback: SearchFeedbackRequest,
    _: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    """This endpoint isn't protected - it does not check if the user has access to the document
    Users could try changing boosts of arbitrary docs but this does not leak any data.
    """
    create_doc_retrieval_feedback(
        message_id=feedback.message_id,
        document_id=feedback.document_id,
        document_rank=feedback.document_rank,
        clicked=feedback.click,
        feedback=feedback.search_feedback,
        db_session=db_session,
    )


class MaxSelectedDocumentTokens(BaseModel):
    max_tokens: int


@router.get("/max-selected-document-tokens")
def get_max_document_tokens(
    persona_id: int,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> MaxSelectedDocumentTokens:
    try:
        persona = get_persona_by_id(
            persona_id=persona_id,
            user=user,
            db_session=db_session,
            is_for_edit=False,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Persona not found")

    return MaxSelectedDocumentTokens(
        max_tokens=compute_max_document_tokens_for_persona(
            db_session=db_session,
            persona=persona,
        ),
    )


"""Endpoints for chat seeding"""


class ChatSeedRequest(BaseModel):
    # standard chat session stuff
    persona_id: int
    prompt_id: int | None = None

    # overrides / seeding
    llm_override: LLMOverride | None = None
    prompt_override: PromptOverride | None = None
    description: str | None = None
    message: str | None = None

    # TODO: support this
    # initial_message_retrieval_options: RetrievalDetails | None = None


class ChatSeedResponse(BaseModel):
    redirect_url: str


@router.post("/seed-chat-session")
def seed_chat(
    chat_seed_request: ChatSeedRequest,
    # NOTE: realistically, this will be an API key not an actual user
    _: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> ChatSeedResponse:
    try:
        new_chat_session = create_chat_session(
            db_session=db_session,
            description=chat_seed_request.description or "",
            user_id=None,  # this chat session is "unassigned" until a user visits the web UI
            persona_id=chat_seed_request.persona_id,
            llm_override=chat_seed_request.llm_override,
            prompt_override=chat_seed_request.prompt_override,
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=400, detail="Invalid Persona provided.")

    if chat_seed_request.message is not None:
        root_message = get_or_create_root_message(
            chat_session_id=new_chat_session.id, db_session=db_session
        )
        llm, fast_llm = get_llms_for_persona(persona=new_chat_session.persona)

        tokenizer = get_tokenizer(
            model_name=llm.config.model_name,
            provider_type=llm.config.model_provider,
        )
        token_count = len(tokenizer.encode(chat_seed_request.message))

        create_new_chat_message(
            chat_session_id=new_chat_session.id,
            parent_message=root_message,
            prompt_id=chat_seed_request.prompt_id
            or (
                new_chat_session.persona.prompts[0].id
                if new_chat_session.persona.prompts
                else None
            ),
            message=chat_seed_request.message,
            token_count=token_count,
            message_type=MessageType.USER,
            db_session=db_session,
        )

    return ChatSeedResponse(
        redirect_url=f"{WEB_DOMAIN}/chat?chatId={new_chat_session.id}&seeded=true"
    )


class SeedChatFromSlackRequest(BaseModel):
    chat_session_id: UUID


class SeedChatFromSlackResponse(BaseModel):
    redirect_url: str


@router.post("/seed-chat-session-from-slack")
def seed_chat_from_slack(
    chat_seed_request: SeedChatFromSlackRequest,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> SeedChatFromSlackResponse:
    slack_chat_session_id = chat_seed_request.chat_session_id
    new_chat_session = duplicate_chat_session_for_user_from_slack(
        db_session=db_session,
        user=user,
        chat_session_id=slack_chat_session_id,
    )

    add_chats_to_session_from_slack_thread(
        db_session=db_session,
        slack_chat_session_id=slack_chat_session_id,
        new_chat_session_id=new_chat_session.id,
    )

    return SeedChatFromSlackResponse(
        redirect_url=f"{WEB_DOMAIN}/chat?chatId={new_chat_session.id}"
    )


"""File upload"""


@router.post("/file")
def upload_files_for_chat(
    files: list[UploadFile],
    db_session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
) -> dict[str, list[FileDescriptor]]:

    # NOTE(rkuo): Unify this with file_validation.py and extract_file_text.py
    # image_content_types = {"image/jpeg", "image/png", "image/webp"}
    # csv_content_types = {"text/csv"}
    # text_content_types = {
    #     "text/plain",
    #     "text/markdown",
    #     "text/x-markdown",
    #     "text/x-config",
    #     "text/tab-separated-values",
    #     "application/json",
    #     "application/xml",
    #     "text/xml",
    #     "application/x-yaml",
    # }
    # document_content_types = {
    #     "application/pdf",
    #     "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    #     "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    #     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    #     "message/rfc822",
    #     "application/epub+zip",
    # }

    # allowed_content_types = (
    #     image_content_types.union(text_content_types)
    #     .union(document_content_types)
    #     .union(csv_content_types)
    # )

    for file in files:
        if not file.content_type:
            raise HTTPException(status_code=400, detail="File content type is required")

        if file.content_type not in UploadMimeTypes.ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported file type.")

        if (
            file.content_type in UploadMimeTypes.IMAGE_MIME_TYPES
            and file.size
            and file.size > 20 * 1024 * 1024
        ):
            raise HTTPException(
                status_code=400,
                detail="File size must be less than 20MB",
            )

    file_store = get_default_file_store(db_session)

    file_info: list[tuple[str, str | None, ChatFileType]] = []
    for file in files:
        file_type = mime_type_to_chat_file_type(file.content_type)

        file_content = file.file.read()  # Read the file content

        # NOTE: Image conversion to JPEG used to be enforced here.
        # This was removed to:
        # 1. Preserve original file content for downloads
        # 2. Maintain transparency in formats like PNG
        # 3. Ameliorate issue with file conversion
        file_content_io = io.BytesIO(file_content)

        new_content_type = file.content_type

        # Store the file normally
        file_id = file_store.save_file(
            content=file_content_io,
            display_name=file.filename,
            file_origin=FileOrigin.CHAT_UPLOAD,
            file_type=new_content_type or file_type.value,
        )

        # 4) If the file is a doc, extract text and store that separately
        if file_type == ChatFileType.DOC:
            # Re-wrap bytes in a fresh BytesIO so we start at position 0
            extracted_text_io = io.BytesIO(file_content)
            extracted_text = extract_file_text(
                file=extracted_text_io,  # use the bytes we already read
                file_name=file.filename or "",
            )

            text_file_id = file_store.save_file(
                content=io.BytesIO(extracted_text.encode()),
                display_name=file.filename,
                file_origin=FileOrigin.CHAT_UPLOAD,
                file_type="text/plain",
            )
            # Return the text file as the "main" file descriptor for doc types
            file_info.append((text_file_id, file.filename, ChatFileType.PLAIN_TEXT))
        else:
            file_info.append((file_id, file.filename, file_type))

        # 5) Create a user file for each uploaded file
        user_files = create_user_files([file], RECENT_DOCS_FOLDER_ID, user, db_session)
        for user_file in user_files:
            # 6) Create connector
            connector_base = ConnectorBase(
                name=f"UserFile-{int(time.time())}",
                source=DocumentSource.FILE,
                input_type=InputType.LOAD_STATE,
                connector_specific_config={
                    "file_locations": [user_file.file_id],
                    "zip_metadata": {},
                },
                refresh_freq=None,
                prune_freq=None,
                indexing_start=None,
            )
            connector = create_connector(
                db_session=db_session,
                connector_data=connector_base,
            )

            # 7) Create credential
            credential_info = CredentialBase(
                credential_json={},
                admin_public=True,
                source=DocumentSource.FILE,
                curator_public=True,
                groups=[],
                name=f"UserFileCredential-{int(time.time())}",
                is_user_file=True,
            )
            credential = create_credential(credential_info, user, db_session)

            # 8) Create connector credential pair
            cc_pair = add_credential_to_connector(
                db_session=db_session,
                user=user,
                connector_id=connector.id,
                credential_id=credential.id,
                cc_pair_name=f"UserFileCCPair-{int(time.time())}",
                access_type=AccessType.PRIVATE,
                auto_sync_options=None,
                groups=[],
            )
            user_file.cc_pair_id = cc_pair.data
            db_session.commit()

    return {
        "files": [
            {"id": file_id, "type": file_type, "name": file_name}
            for file_id, file_name, file_type in file_info
        ]
    }


@router.get("/file/{file_id:path}")
def fetch_chat_file(
    file_id: str,
    db_session: Session = Depends(get_session),
    _: User | None = Depends(current_user),
) -> Response:
    file_store = get_default_file_store(db_session)
    file_record = file_store.read_file_record(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    original_file_name = file_record.display_name
    if file_record.file_type.startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        # Check if a converted text file exists for .docx files
        txt_file_name = docx_to_txt_filename(original_file_name)
        txt_file_id = os.path.join(os.path.dirname(file_id), txt_file_name)
        txt_file_record = file_store.read_file_record(txt_file_id)
        if txt_file_record:
            file_record = txt_file_record
            file_id = txt_file_id

    media_type = file_record.file_type
    file_io = file_store.read_file(file_id, mode="b")

    return StreamingResponse(file_io, media_type=media_type)


@router.get("/search")
async def search_chats(
    query: str | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(10),
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> ChatSearchResponse:
    """
    Search for chat sessions based on the provided query.
    If no query is provided, returns recent chat sessions.
    """

    # Use the enhanced database function for chat search
    chat_sessions, has_more = search_chat_sessions(
        user_id=user.id if user else None,
        db_session=db_session,
        query=query,
        page=page,
        page_size=page_size,
        include_deleted=False,
        include_onyxbot_flows=False,
    )

    # Group chat sessions by time period
    today = datetime.datetime.now().date()
    yesterday = today - timedelta(days=1)
    this_week = today - timedelta(days=7)
    this_month = today - timedelta(days=30)

    today_chats: list[ChatSessionSummary] = []
    yesterday_chats: list[ChatSessionSummary] = []
    this_week_chats: list[ChatSessionSummary] = []
    this_month_chats: list[ChatSessionSummary] = []
    older_chats: list[ChatSessionSummary] = []

    for session in chat_sessions:
        session_date = session.time_created.date()

        chat_summary = ChatSessionSummary(
            id=session.id,
            name=session.description,
            persona_id=session.persona_id,
            time_created=session.time_created,
            shared_status=session.shared_status,
            folder_id=session.folder_id,
            current_alternate_model=session.current_alternate_model,
            current_temperature_override=session.temperature_override,
        )

        if session_date == today:
            today_chats.append(chat_summary)
        elif session_date == yesterday:
            yesterday_chats.append(chat_summary)
        elif session_date > this_week:
            this_week_chats.append(chat_summary)
        elif session_date > this_month:
            this_month_chats.append(chat_summary)
        else:
            older_chats.append(chat_summary)

    # Create groups
    groups = []
    if today_chats:
        groups.append(ChatSessionGroup(title="Today", chats=today_chats))
    if yesterday_chats:
        groups.append(ChatSessionGroup(title="Yesterday", chats=yesterday_chats))
    if this_week_chats:
        groups.append(ChatSessionGroup(title="This Week", chats=this_week_chats))
    if this_month_chats:
        groups.append(ChatSessionGroup(title="This Month", chats=this_month_chats))
    if older_chats:
        groups.append(ChatSessionGroup(title="Older", chats=older_chats))

    return ChatSearchResponse(
        groups=groups,
        has_more=has_more,
        next_page=page + 1 if has_more else None,
    )
