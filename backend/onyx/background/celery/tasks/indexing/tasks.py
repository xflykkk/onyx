import multiprocessing
import os
import time
import traceback
from datetime import datetime
from datetime import timezone
from enum import Enum
from http import HTTPStatus
from time import sleep
from typing import Any
from typing import cast

import sentry_sdk
from celery import shared_task
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from celery.result import AsyncResult
from celery.states import READY_STATES
from pydantic import BaseModel
from redis import Redis
from redis.lock import Lock as RedisLock
from sqlalchemy.orm import Session

from onyx.background.celery.apps.app_base import task_logger
from onyx.background.celery.celery_utils import httpx_init_vespa_pool
from onyx.background.celery.memory_monitoring import emit_process_memory
from onyx.background.celery.tasks.beat_schedule import CLOUD_BEAT_MULTIPLIER_DEFAULT
from onyx.background.celery.tasks.indexing.utils import get_unfenced_index_attempt_ids
from onyx.background.celery.tasks.indexing.utils import IndexingCallback
from onyx.background.celery.tasks.indexing.utils import is_in_repeated_error_state
from onyx.background.celery.tasks.indexing.utils import should_index
from onyx.background.celery.tasks.indexing.utils import try_creating_indexing_task
from onyx.background.celery.tasks.indexing.utils import validate_indexing_fences
from onyx.background.indexing.checkpointing_utils import cleanup_checkpoint
from onyx.background.indexing.checkpointing_utils import (
    get_index_attempts_with_old_checkpoints,
)
from onyx.background.indexing.job_client import SimpleJob
from onyx.background.indexing.job_client import SimpleJobClient
from onyx.background.indexing.job_client import SimpleJobException
from onyx.background.indexing.run_indexing import run_indexing_entrypoint
from onyx.configs.app_configs import MANAGED_VESPA
from onyx.configs.app_configs import VESPA_CLOUD_CERT_PATH
from onyx.configs.app_configs import VESPA_CLOUD_KEY_PATH
from onyx.configs.constants import CELERY_GENERIC_BEAT_LOCK_TIMEOUT
from onyx.configs.constants import CELERY_INDEXING_LOCK_TIMEOUT
from onyx.configs.constants import CELERY_INDEXING_WATCHDOG_CONNECTOR_TIMEOUT
from onyx.configs.constants import CELERY_TASK_WAIT_FOR_FENCE_TIMEOUT
from onyx.configs.constants import OnyxCeleryPriority
from onyx.configs.constants import OnyxCeleryQueues
from onyx.configs.constants import OnyxCeleryTask
from onyx.configs.constants import OnyxRedisConstants
from onyx.configs.constants import OnyxRedisLocks
from onyx.configs.constants import OnyxRedisSignals
from onyx.connectors.exceptions import ConnectorValidationError
from onyx.db.connector import mark_ccpair_with_indexing_trigger
from onyx.db.connector_credential_pair import fetch_connector_credential_pairs
from onyx.db.connector_credential_pair import get_connector_credential_pair_from_id
from onyx.db.connector_credential_pair import set_cc_pair_repeated_error_state
from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.enums import ConnectorCredentialPairStatus
from onyx.db.enums import IndexingMode
from onyx.db.enums import IndexingStatus
from onyx.db.index_attempt import get_index_attempt
from onyx.db.index_attempt import mark_attempt_canceled
from onyx.db.index_attempt import mark_attempt_failed
from onyx.db.search_settings import get_active_search_settings_list
from onyx.db.search_settings import get_current_search_settings
from onyx.db.swap_index import check_and_perform_index_swap
from onyx.natural_language_processing.search_nlp_models import EmbeddingModel
from onyx.natural_language_processing.search_nlp_models import warm_up_bi_encoder
from onyx.redis.redis_connector import RedisConnector
from onyx.redis.redis_connector_index import RedisConnectorIndex
from onyx.redis.redis_pool import get_redis_client
from onyx.redis.redis_pool import get_redis_replica_client
from onyx.redis.redis_pool import redis_lock_dump
from onyx.redis.redis_pool import SCAN_ITER_COUNT_DEFAULT
from onyx.redis.redis_utils import is_fence
from onyx.server.runtime.onyx_runtime import OnyxRuntime
from onyx.utils.logger import setup_logger
from onyx.utils.variable_functionality import global_version
from shared_configs.configs import INDEXING_MODEL_SERVER_HOST
from shared_configs.configs import INDEXING_MODEL_SERVER_PORT
from shared_configs.configs import MULTI_TENANT
from shared_configs.configs import SENTRY_DSN

logger = setup_logger()


def _get_fence_validation_block_expiration() -> int:
    """
    Compute the expiration time for the fence validation block signal.
    Base expiration is 60 seconds, multiplied by the beat multiplier only in MULTI_TENANT mode.
    """
    base_expiration = 60  # seconds

    if not MULTI_TENANT:
        return base_expiration

    try:
        beat_multiplier = OnyxRuntime.get_beat_multiplier()
    except Exception:
        beat_multiplier = CLOUD_BEAT_MULTIPLIER_DEFAULT

    return int(base_expiration * beat_multiplier)


class IndexingWatchdogTerminalStatus(str, Enum):
    """The different statuses the watchdog can finish with.

    TODO: create broader success/failure/abort categories
    """

    UNDEFINED = "undefined"

    SUCCEEDED = "succeeded"

    SPAWN_FAILED = "spawn_failed"  # connector spawn failed
    SPAWN_NOT_ALIVE = (
        "spawn_not_alive"  # spawn succeeded but process did not come alive
    )

    BLOCKED_BY_DELETION = "blocked_by_deletion"
    BLOCKED_BY_STOP_SIGNAL = "blocked_by_stop_signal"
    FENCE_NOT_FOUND = "fence_not_found"  # fence does not exist
    FENCE_READINESS_TIMEOUT = (
        "fence_readiness_timeout"  # fence exists but wasn't ready within the timeout
    )
    FENCE_MISMATCH = "fence_mismatch"  # task and fence metadata mismatch
    TASK_ALREADY_RUNNING = "task_already_running"  # task appears to be running already
    INDEX_ATTEMPT_MISMATCH = (
        "index_attempt_mismatch"  # expected index attempt metadata not found in db
    )

    CONNECTOR_VALIDATION_ERROR = (
        "connector_validation_error"  # the connector validation failed
    )
    CONNECTOR_EXCEPTIONED = "connector_exceptioned"  # the connector itself exceptioned
    WATCHDOG_EXCEPTIONED = "watchdog_exceptioned"  # the watchdog exceptioned

    # the watchdog received a termination signal
    TERMINATED_BY_SIGNAL = "terminated_by_signal"

    # the watchdog terminated the task due to no activity
    TERMINATED_BY_ACTIVITY_TIMEOUT = "terminated_by_activity_timeout"

    # NOTE: this may actually be the same as SIGKILL, but parsed differently by python
    # consolidate once we know more
    OUT_OF_MEMORY = "out_of_memory"

    PROCESS_SIGNAL_SIGKILL = "process_signal_sigkill"

    @property
    def code(self) -> int:
        _ENUM_TO_CODE: dict[IndexingWatchdogTerminalStatus, int] = {
            IndexingWatchdogTerminalStatus.PROCESS_SIGNAL_SIGKILL: -9,
            IndexingWatchdogTerminalStatus.OUT_OF_MEMORY: 137,
            IndexingWatchdogTerminalStatus.CONNECTOR_VALIDATION_ERROR: 247,
            IndexingWatchdogTerminalStatus.BLOCKED_BY_DELETION: 248,
            IndexingWatchdogTerminalStatus.BLOCKED_BY_STOP_SIGNAL: 249,
            IndexingWatchdogTerminalStatus.FENCE_NOT_FOUND: 250,
            IndexingWatchdogTerminalStatus.FENCE_READINESS_TIMEOUT: 251,
            IndexingWatchdogTerminalStatus.FENCE_MISMATCH: 252,
            IndexingWatchdogTerminalStatus.TASK_ALREADY_RUNNING: 253,
            IndexingWatchdogTerminalStatus.INDEX_ATTEMPT_MISMATCH: 254,
            IndexingWatchdogTerminalStatus.CONNECTOR_EXCEPTIONED: 255,
        }

        return _ENUM_TO_CODE[self]

    @classmethod
    def from_code(cls, code: int) -> "IndexingWatchdogTerminalStatus":
        _CODE_TO_ENUM: dict[int, IndexingWatchdogTerminalStatus] = {
            -9: IndexingWatchdogTerminalStatus.PROCESS_SIGNAL_SIGKILL,
            137: IndexingWatchdogTerminalStatus.OUT_OF_MEMORY,
            247: IndexingWatchdogTerminalStatus.CONNECTOR_VALIDATION_ERROR,
            248: IndexingWatchdogTerminalStatus.BLOCKED_BY_DELETION,
            249: IndexingWatchdogTerminalStatus.BLOCKED_BY_STOP_SIGNAL,
            250: IndexingWatchdogTerminalStatus.FENCE_NOT_FOUND,
            251: IndexingWatchdogTerminalStatus.FENCE_READINESS_TIMEOUT,
            252: IndexingWatchdogTerminalStatus.FENCE_MISMATCH,
            253: IndexingWatchdogTerminalStatus.TASK_ALREADY_RUNNING,
            254: IndexingWatchdogTerminalStatus.INDEX_ATTEMPT_MISMATCH,
            255: IndexingWatchdogTerminalStatus.CONNECTOR_EXCEPTIONED,
        }

        if code in _CODE_TO_ENUM:
            return _CODE_TO_ENUM[code]

        return IndexingWatchdogTerminalStatus.UNDEFINED


class SimpleJobResult:
    """The data we want to have when the watchdog finishes"""

    def __init__(self) -> None:
        self.status = IndexingWatchdogTerminalStatus.UNDEFINED
        self.connector_source = None
        self.exit_code = None
        self.exception_str = None

    status: IndexingWatchdogTerminalStatus
    connector_source: str | None
    exit_code: int | None
    exception_str: str | None


class ConnectorIndexingContext(BaseModel):
    tenant_id: str
    cc_pair_id: int
    search_settings_id: int
    index_attempt_id: int


class ConnectorIndexingLogBuilder:
    def __init__(self, ctx: ConnectorIndexingContext):
        self.ctx = ctx

    def build(self, msg: str, **kwargs: Any) -> str:
        msg_final = (
            f"{msg}: "
            f"tenant_id={self.ctx.tenant_id} "
            f"attempt={self.ctx.index_attempt_id} "
            f"cc_pair={self.ctx.cc_pair_id} "
            f"search_settings={self.ctx.search_settings_id}"
        )

        # Append extra keyword arguments in logfmt style
        if kwargs:
            extra_logfmt = " ".join(f"{key}={value}" for key, value in kwargs.items())
            msg_final = f"{msg_final} {extra_logfmt}"

        return msg_final


def monitor_ccpair_indexing_taskset(
    tenant_id: str, key_bytes: bytes, r: Redis, db_session: Session
) -> None:
    # if the fence doesn't exist, there's nothing to do
    fence_key = key_bytes.decode("utf-8")
    composite_id = RedisConnector.get_id_from_fence_key(fence_key)
    if composite_id is None:
        task_logger.warning(
            f"Connector indexing: could not parse composite_id from {fence_key}"
        )
        return

    # parse out metadata and initialize the helper class with it
    parts = composite_id.split("/")
    if len(parts) != 2:
        return

    cc_pair_id = int(parts[0])
    search_settings_id = int(parts[1])

    redis_connector = RedisConnector(tenant_id, cc_pair_id)
    redis_connector_index = redis_connector.new_index(search_settings_id)
    if not redis_connector_index.fenced:
        return

    payload = redis_connector_index.payload
    if not payload:
        return

    # if the CC Pair is `SCHEDULED`, moved it to `INITIAL_INDEXING`. A CC Pair
    # should only ever be `SCHEDULED` if it's a new connector.
    cc_pair = get_connector_credential_pair_from_id(db_session, cc_pair_id)
    if cc_pair is None:
        raise RuntimeError(f"CC Pair {cc_pair_id} not found")

    if cc_pair.status == ConnectorCredentialPairStatus.SCHEDULED:
        cc_pair.status = ConnectorCredentialPairStatus.INITIAL_INDEXING
        db_session.commit()

    elapsed_started_str = None
    if payload.started:
        elapsed_started = datetime.now(timezone.utc) - payload.started
        elapsed_started_str = f"{elapsed_started.total_seconds():.2f}"

    elapsed_submitted = datetime.now(timezone.utc) - payload.submitted

    progress = redis_connector_index.get_progress()
    if progress is not None:
        task_logger.info(
            f"Connector indexing progress: "
            f"attempt={payload.index_attempt_id} "
            f"cc_pair={cc_pair_id} "
            f"search_settings={search_settings_id} "
            f"progress={progress} "
            f"elapsed_submitted={elapsed_submitted.total_seconds():.2f} "
            f"elapsed_started={elapsed_started_str}"
        )

    if payload.index_attempt_id is None or payload.celery_task_id is None:
        # the task is still setting up
        return

    # never use any blocking methods on the result from inside a task!
    result: AsyncResult = AsyncResult(payload.celery_task_id)

    # inner/outer/inner double check pattern to avoid race conditions when checking for
    # bad state

    # Verify: if the generator isn't complete, the task must not be in READY state
    # inner = get_completion / generator_complete not signaled
    # outer = result.state in READY state
    status_int = redis_connector_index.get_completion()
    if status_int is None:  # inner signal not set ... possible error
        task_state = result.state
        if (
            task_state in READY_STATES
        ):  # outer signal in terminal state ... possible error
            # Now double check!
            if redis_connector_index.get_completion() is None:
                # inner signal still not set (and cannot change when outer result_state is READY)
                # Task is finished but generator complete isn't set.
                # We have a problem! Worker may have crashed.
                task_result = str(result.result)
                task_traceback = str(result.traceback)

                msg = (
                    f"Connector indexing aborted or exceptioned: "
                    f"attempt={payload.index_attempt_id} "
                    f"celery_task={payload.celery_task_id} "
                    f"cc_pair={cc_pair_id} "
                    f"search_settings={search_settings_id} "
                    f"elapsed_submitted={elapsed_submitted.total_seconds():.2f} "
                    f"result.state={task_state} "
                    f"result.result={task_result} "
                    f"result.traceback={task_traceback}"
                )
                task_logger.warning(msg)

                try:
                    index_attempt = get_index_attempt(
                        db_session, payload.index_attempt_id
                    )
                    if index_attempt:
                        if (
                            index_attempt.status != IndexingStatus.CANCELED
                            and index_attempt.status != IndexingStatus.FAILED
                        ):
                            mark_attempt_failed(
                                index_attempt_id=payload.index_attempt_id,
                                db_session=db_session,
                                failure_reason=msg,
                            )
                except Exception:
                    task_logger.exception(
                        "Connector indexing - Transient exception marking index attempt as failed: "
                        f"attempt={payload.index_attempt_id} "
                        f"tenant={tenant_id} "
                        f"cc_pair={cc_pair_id} "
                        f"search_settings={search_settings_id}"
                    )

                redis_connector_index.reset()
        return

    if redis_connector_index.watchdog_signaled():
        # if the generator is complete, don't clean up until the watchdog has exited
        task_logger.info(
            f"Connector indexing - Delaying finalization until watchdog has exited: "
            f"attempt={payload.index_attempt_id} "
            f"cc_pair={cc_pair_id} "
            f"search_settings={search_settings_id} "
            f"progress={progress} "
            f"elapsed_submitted={elapsed_submitted.total_seconds():.2f} "
            f"elapsed_started={elapsed_started_str}"
        )

        return

    status_enum = HTTPStatus(status_int)

    task_logger.info(
        f"Connector indexing finished: "
        f"attempt={payload.index_attempt_id} "
        f"cc_pair={cc_pair_id} "
        f"search_settings={search_settings_id} "
        f"progress={progress} "
        f"status={status_enum.name} "
        f"elapsed_submitted={elapsed_submitted.total_seconds():.2f} "
        f"elapsed_started={elapsed_started_str}"
    )

    redis_connector_index.reset()

    # mark the CC Pair as `ACTIVE` if the attempt was a success and the
    # CC Pair is not active not already
    # This should never technically be in this state, but we'll handle it anyway
    index_attempt = get_index_attempt(db_session, payload.index_attempt_id)
    index_attempt_is_successful = index_attempt and index_attempt.status.is_successful()
    if (
        index_attempt_is_successful
        and cc_pair.status == ConnectorCredentialPairStatus.SCHEDULED
        or cc_pair.status == ConnectorCredentialPairStatus.INITIAL_INDEXING
    ):
        cc_pair.status = ConnectorCredentialPairStatus.ACTIVE
        db_session.commit()

    # if the index attempt is successful, clear the repeated error state
    if cc_pair.in_repeated_error_state and index_attempt_is_successful:
        cc_pair.in_repeated_error_state = False
        db_session.commit()


@shared_task(
    name=OnyxCeleryTask.CHECK_FOR_INDEXING,
    soft_time_limit=300,
    bind=True,
)
def check_for_indexing(self: Task, *, tenant_id: str) -> int | None:
    """a lightweight task used to kick off indexing tasks.
    Occcasionally does some validation of existing state to clear up error conditions"""

    time_start = time.monotonic()
    task_logger.warning("check_for_indexing - Starting")

    tasks_created = 0
    locked = False
    redis_client = get_redis_client()
    redis_client_replica = get_redis_replica_client()

    # we need to use celery's redis client to access its redis data
    # (which lives on a different db number)
    redis_client_celery: Redis = self.app.broker_connection().channel().client  # type: ignore

    lock_beat: RedisLock = redis_client.lock(
        OnyxRedisLocks.CHECK_INDEXING_BEAT_LOCK,
        timeout=CELERY_GENERIC_BEAT_LOCK_TIMEOUT,
    )

    # these tasks should never overlap
    if not lock_beat.acquire(blocking=False):
        return None

    try:
        locked = True

        # SPECIAL 0/3: sync lookup table for active fences
        # we want to run this less frequently than the overall task
        if not redis_client.exists(OnyxRedisSignals.BLOCK_BUILD_FENCE_LOOKUP_TABLE):
            # build a lookup table of existing fences
            # this is just a migration concern and should be unnecessary once
            # lookup tables are rolled out
            task_logger.info("check_for_indexing - Starting Redis scan for fence lookup table")
            start_time = time.time()
            fence_count = 0
            for key_bytes in redis_client_replica.scan_iter(
                count=SCAN_ITER_COUNT_DEFAULT
            ):
                if is_fence(key_bytes) and not redis_client.sismember(
                    OnyxRedisConstants.ACTIVE_FENCES, key_bytes
                ):
                    logger.warning(f"Adding {key_bytes} to the lookup table.")
                    redis_client.sadd(OnyxRedisConstants.ACTIVE_FENCES, key_bytes)
                    fence_count += 1
            end_time = time.time()
            task_logger.info(f"check_for_indexing - Redis scan completed: {end_time - start_time:.2f} seconds, processed {fence_count} fences")

            redis_client.set(
                OnyxRedisSignals.BLOCK_BUILD_FENCE_LOOKUP_TABLE,
                1,
                ex=OnyxRuntime.get_build_fence_lookup_table_interval(),
            )

        # 1/3: KICKOFF

        # check for search settings swap
        with get_session_with_current_tenant() as db_session:
            old_search_settings = check_and_perform_index_swap(db_session=db_session)
            current_search_settings = get_current_search_settings(db_session)
            # So that the first time users aren't surprised by really slow speed of first
            # batch of documents indexed
            if current_search_settings.provider_type is None and not MULTI_TENANT:
                if old_search_settings:
                    embedding_model = EmbeddingModel.from_db_model(
                        search_settings=current_search_settings,
                        server_host=INDEXING_MODEL_SERVER_HOST,
                        server_port=INDEXING_MODEL_SERVER_PORT,
                    )

                    # only warm up if search settings were changed
                    warm_up_bi_encoder(
                        embedding_model=embedding_model,
                    )

        # gather cc_pair_ids
        lock_beat.reacquire()
        cc_pair_ids: list[int] = []
        with get_session_with_current_tenant() as db_session:
            cc_pairs = fetch_connector_credential_pairs(
                db_session, include_user_files=True
            )
            
            # 注释掉时间过滤器 - Connector 可能需要重新索引历史数据
            # 时间范围过滤：只处理最近3天创建的 CC Pairs
            # from datetime import datetime, timedelta, timezone
            # cutoff_time = datetime.now(timezone.utc) - timedelta(days=3)
            
            # filtered_cc_pairs = []
            # for cc_pair_entry in cc_pairs:
            #     if cc_pair_entry.connector.time_created >= cutoff_time:
            #         filtered_cc_pairs.append(cc_pair_entry)
            #         cc_pair_ids.append(cc_pair_entry.id)
            
            # task_logger.info(f"check_for_indexing - Time filtering: {len(cc_pairs)} total -> {len(filtered_cc_pairs)} recent (last 3 days)")
            
            # 使用原有逻辑：处理所有符合条件的 CC Pairs
            filtered_cc_pairs = cc_pairs
            cc_pair_ids = [cc_pair.id for cc_pair in filtered_cc_pairs]

        # mark CC Pairs that are repeatedly failing as in repeated error state
        with get_session_with_current_tenant() as db_session:
            current_search_settings = get_current_search_settings(db_session)
            for cc_pair_id in cc_pair_ids:
                if is_in_repeated_error_state(
                    cc_pair_id=cc_pair_id,
                    search_settings_id=current_search_settings.id,
                    db_session=db_session,
                ):
                    set_cc_pair_repeated_error_state(
                        db_session=db_session,
                        cc_pair_id=cc_pair_id,
                        in_repeated_error_state=True,
                    )

        # kick off index attempts
        for cc_pair_id in cc_pair_ids:
            lock_beat.reacquire()

            redis_connector = RedisConnector(tenant_id, cc_pair_id)
            with get_session_with_current_tenant() as db_session:
                search_settings_list = get_active_search_settings_list(db_session)
                for search_settings_instance in search_settings_list:
                    # skip non-live search settings that don't have background reindex enabled
                    # those should just auto-change to live shortly after creation without
                    # requiring any indexing till that point
                    if (
                        not search_settings_instance.status.is_current()
                        and not search_settings_instance.background_reindex_enabled
                    ):
                        task_logger.warning("SKIPPING DUE TO NON-LIVE SEARCH SETTINGS")

                        continue

                    redis_connector_index = redis_connector.new_index(
                        search_settings_instance.id
                    )
                    if redis_connector_index.fenced:
                        task_logger.debug(
                            f"check_for_indexing - Skipping fenced connector: "
                            f"cc_pair={cc_pair_id} search_settings={search_settings_instance.id}"
                        )
                        continue

                    cc_pair = get_connector_credential_pair_from_id(
                        db_session=db_session,
                        cc_pair_id=cc_pair_id,
                    )
                    if not cc_pair:
                        task_logger.warning(
                            f"check_for_indexing - CC pair not found: cc_pair={cc_pair_id}"
                        )
                        continue

                    if not should_index(
                        cc_pair=cc_pair,
                        search_settings_instance=search_settings_instance,
                        secondary_index_building=len(search_settings_list) > 1,
                        db_session=db_session,
                    ):
                        task_logger.debug(
                            f"check_for_indexing - Not indexing cc_pair_id: {cc_pair_id} "
                            f"search_settings={search_settings_instance.id}, "
                            f"secondary_index_building={len(search_settings_list) > 1}"
                        )
                        continue
                    else:
                        task_logger.debug(
                            f"check_for_indexing - Will index cc_pair_id: {cc_pair_id} "
                            f"search_settings={search_settings_instance.id}, "
                            f"secondary_index_building={len(search_settings_list) > 1}"
                        )

                    reindex = False
                    if search_settings_instance.status.is_current():
                        # the indexing trigger is only checked and cleared with the current search settings
                        if cc_pair.indexing_trigger is not None:
                            if cc_pair.indexing_trigger == IndexingMode.REINDEX:
                                reindex = True

                            task_logger.info(
                                f"Connector indexing manual trigger detected: "
                                f"cc_pair={cc_pair.id} "
                                f"search_settings={search_settings_instance.id} "
                                f"indexing_mode={cc_pair.indexing_trigger}"
                            )

                            mark_ccpair_with_indexing_trigger(
                                cc_pair.id, None, db_session
                            )

                    # using a task queue and only allowing one task per cc_pair/search_setting
                    # prevents us from starving out certain attempts
                    attempt_id = try_creating_indexing_task(
                        self.app,
                        cc_pair,
                        search_settings_instance,
                        reindex,
                        db_session,
                        redis_client,
                        tenant_id,
                    )
                    if attempt_id:
                        task_logger.info(
                            f"Connector indexing queued: "
                            f"index_attempt={attempt_id} "
                            f"cc_pair={cc_pair.id} "
                            f"search_settings={search_settings_instance.id}"
                        )
                        tasks_created += 1
                    else:
                        task_logger.info(
                            f"Failed to create indexing task: "
                            f"cc_pair={cc_pair.id} "
                            f"search_settings={search_settings_instance.id}"
                        )

        lock_beat.reacquire()

        # 2/3: VALIDATE

        # Fail any index attempts in the DB that don't have fences
        # This shouldn't ever happen!
        with get_session_with_current_tenant() as db_session:
            unfenced_attempt_ids = get_unfenced_index_attempt_ids(
                db_session, redis_client
            )

            for attempt_id in unfenced_attempt_ids:
                lock_beat.reacquire()

                attempt = get_index_attempt(db_session, attempt_id)
                if not attempt:
                    continue

                failure_reason = (
                    f"Unfenced index attempt found in DB: "
                    f"index_attempt={attempt.id} "
                    f"cc_pair={attempt.connector_credential_pair_id} "
                    f"search_settings={attempt.search_settings_id}"
                )
                task_logger.error(failure_reason)
                mark_attempt_failed(
                    attempt.id, db_session, failure_reason=failure_reason
                )

        lock_beat.reacquire()
        # we want to run this less frequently than the overall task
        if not redis_client.exists(OnyxRedisSignals.BLOCK_VALIDATE_INDEXING_FENCES):
            # clear any indexing fences that don't have associated celery tasks in progress
            # tasks can be in the queue in redis, in reserved tasks (prefetched by the worker),
            # or be currently executing
            try:
                validate_indexing_fences(
                    tenant_id, redis_client_replica, redis_client_celery, lock_beat
                )
            except Exception:
                task_logger.exception("Exception while validating indexing fences")

            redis_client.set(
                OnyxRedisSignals.BLOCK_VALIDATE_INDEXING_FENCES,
                1,
                ex=_get_fence_validation_block_expiration(),
            )

        # 3/3: FINALIZE
        lock_beat.reacquire()
        keys = cast(
            set[Any], redis_client_replica.smembers(OnyxRedisConstants.ACTIVE_FENCES)
        )
        for key in keys:
            key_bytes = cast(bytes, key)

            if not redis_client.exists(key_bytes):
                redis_client.srem(OnyxRedisConstants.ACTIVE_FENCES, key_bytes)
                continue

            key_str = key_bytes.decode("utf-8")
            if key_str.startswith(RedisConnectorIndex.FENCE_PREFIX):
                with get_session_with_current_tenant() as db_session:
                    monitor_ccpair_indexing_taskset(
                        tenant_id, key_bytes, redis_client_replica, db_session
                    )

    except SoftTimeLimitExceeded:
        task_logger.info(
            "Soft time limit exceeded, task is being terminated gracefully."
        )
    except Exception:
        task_logger.exception("Unexpected exception during indexing check")
    finally:
        if locked:
            if lock_beat.owned():
                lock_beat.release()
            else:
                task_logger.error(
                    "check_for_indexing - Lock not owned on completion: "
                    f"tenant={tenant_id}"
                )
                redis_lock_dump(lock_beat, redis_client)

    time_elapsed = time.monotonic() - time_start
    task_logger.info(f"check_for_indexing finished: elapsed={time_elapsed:.2f}")
    return tasks_created


def connector_indexing_task(
    index_attempt_id: int,
    cc_pair_id: int,
    search_settings_id: int,
    is_ee: bool,
    tenant_id: str,
) -> int | None:
    """Indexing task. For a cc pair, this task pulls all document IDs from the source
    and compares those IDs to locally stored documents and deletes all locally stored IDs missing
    from the most recently pulled document ID list

    acks_late must be set to False. Otherwise, celery's visibility timeout will
    cause any task that runs longer than the timeout to be redispatched by the broker.
    There appears to be no good workaround for this, so we need to handle redispatching
    manually.

    Returns None if the task did not run (possibly due to a conflict).
    Otherwise, returns an int >= 0 representing the number of indexed docs.

    NOTE: if an exception is raised out of this task, the primary worker will detect
    that the task transitioned to a "READY" state but the generator_complete_key doesn't exist.
    This will cause the primary worker to abort the indexing attempt and clean up.
    """

    # Since connector_indexing_proxy_task spawns a new process using this function as
    # the entrypoint, we init Sentry here.
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=0.1,
        )
        logger.info("Sentry initialized")
    else:
        logger.debug("Sentry DSN not provided, skipping Sentry initialization")

    logger.info(
        f"Indexing spawned task starting: "
        f"attempt={index_attempt_id} "
        f"tenant={tenant_id} "
        f"cc_pair={cc_pair_id} "
        f"search_settings={search_settings_id}"
    )

    n_final_progress: int | None = None

    # 20 is the documented default for httpx max_keepalive_connections
    if MANAGED_VESPA:
        httpx_init_vespa_pool(
            20, ssl_cert=VESPA_CLOUD_CERT_PATH, ssl_key=VESPA_CLOUD_KEY_PATH
        )
    else:
        httpx_init_vespa_pool(20)

    redis_connector = RedisConnector(tenant_id, cc_pair_id)
    redis_connector_index = redis_connector.new_index(search_settings_id)

    r = get_redis_client()

    if redis_connector.delete.fenced:
        raise SimpleJobException(
            f"Indexing will not start because connector deletion is in progress: "
            f"attempt={index_attempt_id} "
            f"cc_pair={cc_pair_id} "
            f"fence={redis_connector.delete.fence_key}",
            code=IndexingWatchdogTerminalStatus.BLOCKED_BY_DELETION.code,
        )

    if redis_connector.stop.fenced:
        raise SimpleJobException(
            f"Indexing will not start because a connector stop signal was detected: "
            f"attempt={index_attempt_id} "
            f"cc_pair={cc_pair_id} "
            f"fence={redis_connector.stop.fence_key}",
            code=IndexingWatchdogTerminalStatus.BLOCKED_BY_STOP_SIGNAL.code,
        )

    # this wait is needed to avoid a race condition where
    # the primary worker sends the task and it is immediately executed
    # before the primary worker can finalize the fence
    start = time.monotonic()
    while True:
        if time.monotonic() - start > CELERY_TASK_WAIT_FOR_FENCE_TIMEOUT:
            raise SimpleJobException(
                f"connector_indexing_task - timed out waiting for fence to be ready: "
                f"fence={redis_connector.permissions.fence_key}",
                code=IndexingWatchdogTerminalStatus.FENCE_READINESS_TIMEOUT.code,
            )

        if not redis_connector_index.fenced:  # The fence must exist
            raise SimpleJobException(
                f"connector_indexing_task - fence not found: fence={redis_connector_index.fence_key}",
                code=IndexingWatchdogTerminalStatus.FENCE_NOT_FOUND.code,
            )

        payload = redis_connector_index.payload  # The payload must exist
        if not payload:
            raise SimpleJobException(
                "connector_indexing_task: payload invalid or not found",
                code=IndexingWatchdogTerminalStatus.FENCE_NOT_FOUND.code,
            )

        if payload.index_attempt_id is None or payload.celery_task_id is None:
            logger.info(
                f"connector_indexing_task - Waiting for fence: fence={redis_connector_index.fence_key}"
            )
            sleep(1)
            continue

        if payload.index_attempt_id != index_attempt_id:
            raise SimpleJobException(
                f"connector_indexing_task - id mismatch. Task may be left over from previous run.: "
                f"task_index_attempt={index_attempt_id} "
                f"payload_index_attempt={payload.index_attempt_id}",
                code=IndexingWatchdogTerminalStatus.FENCE_MISMATCH.code,
            )

        logger.info(
            f"connector_indexing_task - Fence found, continuing...: fence={redis_connector_index.fence_key}"
        )
        break

    # set thread_local=False since we don't control what thread the indexing/pruning
    # might run our callback with
    lock: RedisLock = r.lock(
        redis_connector_index.generator_lock_key,
        timeout=CELERY_INDEXING_LOCK_TIMEOUT,
        thread_local=False,
    )

    acquired = lock.acquire(blocking=False)
    if not acquired:
        logger.warning(
            f"Indexing task already running, exiting...: "
            f"index_attempt={index_attempt_id} "
            f"cc_pair={cc_pair_id} "
            f"search_settings={search_settings_id}"
        )

        raise SimpleJobException(
            f"Indexing task already running, exiting...: "
            f"index_attempt={index_attempt_id} "
            f"cc_pair={cc_pair_id} "
            f"search_settings={search_settings_id}",
            code=IndexingWatchdogTerminalStatus.TASK_ALREADY_RUNNING.code,
        )

    payload.started = datetime.now(timezone.utc)
    redis_connector_index.set_fence(payload)

    try:
        with get_session_with_current_tenant() as db_session:
            attempt = get_index_attempt(db_session, index_attempt_id)
            if not attempt:
                raise SimpleJobException(
                    f"Index attempt not found: index_attempt={index_attempt_id}",
                    code=IndexingWatchdogTerminalStatus.INDEX_ATTEMPT_MISMATCH.code,
                )

            cc_pair = get_connector_credential_pair_from_id(
                db_session=db_session,
                cc_pair_id=cc_pair_id,
            )

            if not cc_pair:
                raise SimpleJobException(
                    f"cc_pair not found: cc_pair={cc_pair_id}",
                    code=IndexingWatchdogTerminalStatus.INDEX_ATTEMPT_MISMATCH.code,
                )

            if not cc_pair.connector:
                raise SimpleJobException(
                    f"Connector not found: cc_pair={cc_pair_id} connector={cc_pair.connector_id}",
                    code=IndexingWatchdogTerminalStatus.INDEX_ATTEMPT_MISMATCH.code,
                )

            if not cc_pair.credential:
                raise SimpleJobException(
                    f"Credential not found: cc_pair={cc_pair_id} credential={cc_pair.credential_id}",
                    code=IndexingWatchdogTerminalStatus.INDEX_ATTEMPT_MISMATCH.code,
                )

        # define a callback class
        callback = IndexingCallback(
            os.getppid(),
            redis_connector,
            lock,
            r,
            redis_connector_index,
        )

        logger.info(
            f"Indexing spawned task running entrypoint: attempt={index_attempt_id} "
            f"tenant={tenant_id} "
            f"cc_pair={cc_pair_id} "
            f"search_settings={search_settings_id}"
        )

        # This is where the heavy/real work happens
        run_indexing_entrypoint(
            index_attempt_id,
            tenant_id,
            cc_pair_id,
            is_ee,
            callback=callback,
        )

        # get back the total number of indexed docs and return it
        n_final_progress = redis_connector_index.get_progress()
        redis_connector_index.set_generator_complete(HTTPStatus.OK.value)
    except ConnectorValidationError:
        raise SimpleJobException(
            f"Indexing task failed: attempt={index_attempt_id} "
            f"tenant={tenant_id} "
            f"cc_pair={cc_pair_id} "
            f"search_settings={search_settings_id}",
            code=IndexingWatchdogTerminalStatus.CONNECTOR_VALIDATION_ERROR.code,
        )

    except Exception as e:
        logger.exception(
            f"Indexing spawned task failed: attempt={index_attempt_id} "
            f"tenant={tenant_id} "
            f"cc_pair={cc_pair_id} "
            f"search_settings={search_settings_id}"
        )

        # special bulletproofing ... truncate long exception messages
        # for exception types that require more args, this will fail
        # thus the try/except
        try:
            sanitized_e = type(e)(str(e)[:1024])
            sanitized_e.__traceback__ = e.__traceback__
            raise sanitized_e
        except Exception:
            raise e

    finally:
        if lock.owned():
            lock.release()

    logger.info(
        f"Indexing spawned task finished: attempt={index_attempt_id} "
        f"cc_pair={cc_pair_id} "
        f"search_settings={search_settings_id}"
    )
    return n_final_progress


def process_job_result(
    job: SimpleJob,
    connector_source: str | None,
    redis_connector_index: RedisConnectorIndex,
    log_builder: ConnectorIndexingLogBuilder,
) -> SimpleJobResult:
    result = SimpleJobResult()
    result.connector_source = connector_source

    if job.process:
        result.exit_code = job.process.exitcode

    if job.status != "error":
        result.status = IndexingWatchdogTerminalStatus.SUCCEEDED
        return result

    ignore_exitcode = False

    # In EKS, there is an edge case where successful tasks return exit
    # code 1 in the cloud due to the set_spawn_method not sticking.
    # We've since worked around this, but the following is a safe way to
    # work around this issue. Basically, we ignore the job error state
    # if the completion signal is OK.
    status_int = redis_connector_index.get_completion()
    if status_int:
        status_enum = HTTPStatus(status_int)
        if status_enum == HTTPStatus.OK:
            ignore_exitcode = True

    if ignore_exitcode:
        result.status = IndexingWatchdogTerminalStatus.SUCCEEDED
        task_logger.warning(
            log_builder.build(
                "Indexing watchdog - spawned task has non-zero exit code "
                "but completion signal is OK. Continuing...",
                exit_code=str(result.exit_code),
            )
        )
    else:
        if result.exit_code is not None:
            result.status = IndexingWatchdogTerminalStatus.from_code(result.exit_code)

        result.exception_str = job.exception()

    return result


@shared_task(
    name=OnyxCeleryTask.CONNECTOR_INDEXING_PROXY_TASK,
    bind=True,
    acks_late=False,
    track_started=True,
    max_retries=3,  # Allow up to 3 retries for broken pipe errors
    default_retry_delay=60,  # Wait 60 seconds before first retry
)
def connector_indexing_proxy_task(
    self: Task,
    index_attempt_id: int,
    cc_pair_id: int,
    search_settings_id: int,
    tenant_id: str,
) -> None:
    """celery out of process task execution strategy is pool=prefork, but it uses fork,
    and forking is inherently unstable.

    To work around this, we use pool=threads and proxy our work to a spawned task.

    TODO(rkuo): refactor this so that there is a single return path where we canonically
    log the result of running this function.

    NOTE: we try/except all db access in this function because as a watchdog, this function
    needs to be extremely stable.
    """
    start = time.monotonic()

    result = SimpleJobResult()

    ctx = ConnectorIndexingContext(
        tenant_id=tenant_id,
        cc_pair_id=cc_pair_id,
        search_settings_id=search_settings_id,
        index_attempt_id=index_attempt_id,
    )

    log_builder = ConnectorIndexingLogBuilder(ctx)

    task_logger.info(
        log_builder.build(
            "Indexing watchdog - starting",
            mp_start_method=str(multiprocessing.get_start_method()),
        )
    )

    if not self.request.id:
        task_logger.error("self.request.id is None!")

    client = SimpleJobClient()
    task_logger.info(f"submitting connector_indexing_task with tenant_id={tenant_id}")

    try:
        job = client.submit(
            connector_indexing_task,
            index_attempt_id,
            cc_pair_id,
            search_settings_id,
            global_version.is_ee_version(),
            tenant_id,
        )
    except Exception as e:
        # Check for Broken pipe errors and OSErrors specifically during job submission
        error_message = str(e).lower()
        if ("broken pipe" in error_message or 
            "errno 32" in error_message or 
            isinstance(e, (BrokenPipeError, OSError))):
            
            # Log the broken pipe error for debugging
            task_logger.warning(
                log_builder.build(
                    "Indexing watchdog - Broken pipe error during job submission",
                    error=str(e),
                    attempt=self.request.retries + 1,
                    max_retries=self.max_retries,
                )
            )
            
            # Only retry if we haven't exceeded max retries
            if self.request.retries < self.max_retries:
                # Exponential backoff: 60s, 120s, 240s
                countdown = self.default_retry_delay * (2 ** self.request.retries)
                
                task_logger.info(
                    log_builder.build(
                        "Indexing watchdog - Retrying due to broken pipe during submission",
                        retry_attempt=self.request.retries + 1,
                        countdown=f"{countdown}s",
                    )
                )
                
                # Retry the task
                raise self.retry(exc=e, countdown=countdown)
            else:
                task_logger.error(
                    log_builder.build(
                        "Indexing watchdog - Max retries exceeded for broken pipe during submission",
                        final_attempt=self.request.retries + 1,
                    )
                )
        
        # Re-raise other exceptions
        raise

    if not job or not job.process:
        result.status = IndexingWatchdogTerminalStatus.SPAWN_FAILED
        task_logger.info(
            log_builder.build(
                "Indexing watchdog - finished",
                status=str(result.status.value),
                exit_code=str(result.exit_code),
            )
        )
        return

    # Ensure the process has moved out of the starting state
    num_waits = 0
    while True:
        if num_waits > 15:
            result.status = IndexingWatchdogTerminalStatus.SPAWN_NOT_ALIVE
            task_logger.info(
                log_builder.build(
                    "Indexing watchdog - finished",
                    status=str(result.status.value),
                    exit_code=str(result.exit_code),
                )
            )
            job.release()
            return

        if job.process.is_alive() or job.process.exitcode is not None:
            break

        sleep(1)
        num_waits += 1

    task_logger.info(
        log_builder.build(
            "Indexing watchdog - spawn succeeded",
            pid=str(job.process.pid),
        )
    )

    redis_connector = RedisConnector(tenant_id, cc_pair_id)
    redis_connector_index = redis_connector.new_index(search_settings_id)

    # Track the last time memory info was emitted
    last_memory_emit_time = 0.0

    # track the last ttl and the time it was observed
    last_activity_ttl_observed: float = time.monotonic()
    last_activity_ttl: int = 0

    try:
        with get_session_with_current_tenant() as db_session:
            index_attempt = get_index_attempt(
                db_session=db_session, index_attempt_id=index_attempt_id
            )
            if not index_attempt:
                raise RuntimeError("Index attempt not found")

            result.connector_source = (
                index_attempt.connector_credential_pair.connector.source.value
            )

        redis_connector_index.set_active()  # renew active signal

        # prime the connector active signal (renewed inside the connector)
        redis_connector_index.set_connector_active()

        while True:
            sleep(5)

            now = time.monotonic()

            # renew watchdog signal (this has a shorter timeout than set_active)
            redis_connector_index.set_watchdog(True)

            # renew active signal
            redis_connector_index.set_active()

            # if the job is done, clean up and break
            if job.done():
                try:
                    result = process_job_result(
                        job, result.connector_source, redis_connector_index, log_builder
                    )
                except Exception:
                    task_logger.exception(
                        log_builder.build(
                            "Indexing watchdog - spawned task exceptioned"
                        )
                    )
                finally:
                    job.release()
                    break

            # log the memory usage for tracking down memory leaks / connector-specific memory issues
            pid = job.process.pid
            if pid is not None:
                # Only emit memory info once per minute (60 seconds)
                current_time = time.monotonic()
                if current_time - last_memory_emit_time >= 60.0:
                    emit_process_memory(
                        pid,
                        "indexing_worker",
                        {
                            "cc_pair_id": cc_pair_id,
                            "search_settings_id": search_settings_id,
                            "index_attempt_id": index_attempt_id,
                        },
                    )
                    last_memory_emit_time = current_time

            # if a termination signal is detected, break (exit point will clean up)
            if self.request.id and redis_connector_index.terminating(self.request.id):
                task_logger.warning(
                    log_builder.build("Indexing watchdog - termination signal detected")
                )

                result.status = IndexingWatchdogTerminalStatus.TERMINATED_BY_SIGNAL
                break

            # if activity timeout is detected, break (exit point will clean up)
            ttl = redis_connector_index.connector_active_ttl()
            if ttl < 0:
                # verify expectations around ttl
                last_observed = last_activity_ttl_observed - now
                if now > last_activity_ttl_observed + last_activity_ttl:
                    task_logger.warning(
                        log_builder.build(
                            "Indexing watchdog - activity timeout exceeded",
                            last_observed=f"{last_observed:.2f}s",
                            last_ttl=f"{last_activity_ttl}",
                            timeout=f"{CELERY_INDEXING_WATCHDOG_CONNECTOR_TIMEOUT}s",
                        )
                    )

                    result.status = (
                        IndexingWatchdogTerminalStatus.TERMINATED_BY_ACTIVITY_TIMEOUT
                    )
                    break
                else:
                    task_logger.warning(
                        log_builder.build(
                            "Indexing watchdog - activity timeout expired unexpectedly, "
                            "waiting for last observed TTL before exiting",
                            last_observed=f"{last_observed:.2f}s",
                            last_ttl=f"{last_activity_ttl}",
                            timeout=f"{CELERY_INDEXING_WATCHDOG_CONNECTOR_TIMEOUT}s",
                        )
                    )
            else:
                last_activity_ttl_observed = now
                last_activity_ttl = ttl

            # if the spawned task is still running, restart the check once again
            # if the index attempt is not in a finished status
            try:
                with get_session_with_current_tenant() as db_session:
                    index_attempt = get_index_attempt(
                        db_session=db_session, index_attempt_id=index_attempt_id
                    )

                    if not index_attempt:
                        continue

                    if not index_attempt.is_finished():
                        continue

            except Exception:
                task_logger.exception(
                    log_builder.build(
                        "Indexing watchdog - transient exception looking up index attempt"
                    )
                )
                continue

    except Exception as e:
        # Check for Broken pipe errors and retry if possible
        error_message = str(e).lower()
        if ("broken pipe" in error_message or 
            "errno 32" in error_message or 
            isinstance(e, BrokenPipeError)):
            
            # Log the broken pipe error for debugging
            task_logger.warning(
                log_builder.build(
                    "Indexing watchdog - Broken pipe error detected",
                    error=str(e),
                    attempt=self.request.retries + 1,
                    max_retries=self.max_retries,
                )
            )
            
            # Only retry if we haven't exceeded max retries
            if self.request.retries < self.max_retries:
                # Exponential backoff: 60s, 120s, 240s
                countdown = self.default_retry_delay * (2 ** self.request.retries)
                
                task_logger.info(
                    log_builder.build(
                        "Indexing watchdog - Retrying due to broken pipe",
                        retry_attempt=self.request.retries + 1,
                        countdown=f"{countdown}s",
                    )
                )
                
                # Retry the task
                raise self.retry(exc=e, countdown=countdown)
            else:
                task_logger.error(
                    log_builder.build(
                        "Indexing watchdog - Max retries exceeded for broken pipe error",
                        final_attempt=self.request.retries + 1,
                    )
                )
        
        result.status = IndexingWatchdogTerminalStatus.WATCHDOG_EXCEPTIONED
        if isinstance(e, ConnectorValidationError):
            # No need to expose full stack trace for validation errors
            result.exception_str = str(e)
        else:
            result.exception_str = traceback.format_exc()

    # handle exit and reporting
    elapsed = time.monotonic() - start
    if result.exception_str is not None:
        # print with exception
        try:
            with get_session_with_current_tenant() as db_session:
                failure_reason = (
                    f"Spawned task exceptioned: exit_code={result.exit_code}"
                )
                mark_attempt_failed(
                    ctx.index_attempt_id,
                    db_session,
                    failure_reason=failure_reason,
                    full_exception_trace=result.exception_str,
                )
        except Exception:
            task_logger.exception(
                log_builder.build(
                    "Indexing watchdog - transient exception marking index attempt as failed"
                )
            )

        normalized_exception_str = "None"
        if result.exception_str:
            normalized_exception_str = result.exception_str.replace(
                "\n", "\\n"
            ).replace('"', '\\"')

        task_logger.warning(
            log_builder.build(
                "Indexing watchdog - finished",
                source=result.connector_source,
                status=result.status.value,
                exit_code=str(result.exit_code),
                exception=f'"{normalized_exception_str}"',
                elapsed=f"{elapsed:.2f}s",
            )
        )

        redis_connector_index.set_watchdog(False)
        raise RuntimeError(f"Exception encountered: traceback={result.exception_str}")

    # print without exception
    if result.status == IndexingWatchdogTerminalStatus.TERMINATED_BY_SIGNAL:
        try:
            with get_session_with_current_tenant() as db_session:
                logger.exception(
                    f"Marking attempt {index_attempt_id} as canceled due to termination signal"
                )
                mark_attempt_canceled(
                    index_attempt_id,
                    db_session,
                    "Connector termination signal detected",
                )
        except Exception:
            task_logger.exception(
                log_builder.build(
                    "Indexing watchdog - transient exception marking index attempt as canceled"
                )
            )

        job.cancel()
    elif result.status == IndexingWatchdogTerminalStatus.TERMINATED_BY_ACTIVITY_TIMEOUT:
        try:
            with get_session_with_current_tenant() as db_session:
                mark_attempt_failed(
                    index_attempt_id,
                    db_session,
                    "Indexing watchdog - activity timeout exceeded: "
                    f"attempt={index_attempt_id} "
                    f"timeout={CELERY_INDEXING_WATCHDOG_CONNECTOR_TIMEOUT}s",
                )
        except Exception:
            logger.exception(
                log_builder.build(
                    "Indexing watchdog - transient exception marking index attempt as failed"
                )
            )
        job.cancel()
    else:
        pass

    task_logger.info(
        log_builder.build(
            "Indexing watchdog - finished",
            source=result.connector_source,
            status=str(result.status.value),
            exit_code=str(result.exit_code),
            elapsed=f"{elapsed:.2f}s",
        )
    )

    redis_connector_index.set_watchdog(False)
    return


# primary
@shared_task(
    name=OnyxCeleryTask.CHECK_FOR_CHECKPOINT_CLEANUP,
    soft_time_limit=300,
    bind=True,
)
def check_for_checkpoint_cleanup(self: Task, *, tenant_id: str) -> None:
    """Clean up old checkpoints that are older than 7 days."""
    locked = False
    redis_client = get_redis_client(tenant_id=tenant_id)
    lock: RedisLock = redis_client.lock(
        OnyxRedisLocks.CHECK_CHECKPOINT_CLEANUP_BEAT_LOCK,
        timeout=CELERY_GENERIC_BEAT_LOCK_TIMEOUT,
    )

    # these tasks should never overlap
    if not lock.acquire(blocking=False):
        return None

    try:
        locked = True
        with get_session_with_current_tenant() as db_session:
            old_attempts = get_index_attempts_with_old_checkpoints(db_session)
            for attempt in old_attempts:
                task_logger.info(
                    f"Cleaning up checkpoint for index attempt {attempt.id}"
                )
                self.app.send_task(
                    OnyxCeleryTask.CLEANUP_CHECKPOINT,
                    kwargs={
                        "index_attempt_id": attempt.id,
                        "tenant_id": tenant_id,
                    },
                    queue=OnyxCeleryQueues.CHECKPOINT_CLEANUP,
                    priority=OnyxCeleryPriority.MEDIUM,
                )
    except Exception:
        task_logger.exception("Unexpected exception during checkpoint cleanup")
        return None
    finally:
        if locked:
            if lock.owned():
                lock.release()
            else:
                task_logger.error(
                    "check_for_checkpoint_cleanup - Lock not owned on completion: "
                    f"tenant={tenant_id}"
                )


# light worker
@shared_task(
    name=OnyxCeleryTask.CLEANUP_CHECKPOINT,
    bind=True,
)
def cleanup_checkpoint_task(
    self: Task, *, index_attempt_id: int, tenant_id: str | None
) -> None:
    """Clean up a checkpoint for a given index attempt"""

    start = time.monotonic()

    try:
        with get_session_with_current_tenant() as db_session:
            cleanup_checkpoint(db_session, index_attempt_id)
    finally:
        elapsed = time.monotonic() - start

        task_logger.info(
            f"cleanup_checkpoint_task completed: tenant_id={tenant_id} "
            f"index_attempt_id={index_attempt_id} "
            f"elapsed={elapsed:.2f}"
        )
