from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CommandStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMMAND_STATUS_UNSPECIFIED: _ClassVar[CommandStatus]
    ACKNOWLEDGED: _ClassVar[CommandStatus]
    EXECUTING: _ClassVar[CommandStatus]
    COMPLETED: _ClassVar[CommandStatus]
    FAILED: _ClassVar[CommandStatus]

class ScheduleRunStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SCHEDULE_RUN_STATUS_UNSPECIFIED: _ClassVar[ScheduleRunStatus]
    SCHEDULE_STARTED: _ClassVar[ScheduleRunStatus]
    SCHEDULE_COMPLETED: _ClassVar[ScheduleRunStatus]
    SCHEDULE_FAILED: _ClassVar[ScheduleRunStatus]
    SCHEDULE_SKIPPED: _ClassVar[ScheduleRunStatus]
    SCHEDULE_TIMEOUT: _ClassVar[ScheduleRunStatus]
COMMAND_STATUS_UNSPECIFIED: CommandStatus
ACKNOWLEDGED: CommandStatus
EXECUTING: CommandStatus
COMPLETED: CommandStatus
FAILED: CommandStatus
SCHEDULE_RUN_STATUS_UNSPECIFIED: ScheduleRunStatus
SCHEDULE_STARTED: ScheduleRunStatus
SCHEDULE_COMPLETED: ScheduleRunStatus
SCHEDULE_FAILED: ScheduleRunStatus
SCHEDULE_SKIPPED: ScheduleRunStatus
SCHEDULE_TIMEOUT: ScheduleRunStatus

class ClientMessage(_message.Message):
    __slots__ = ("service_id", "sequence", "heartbeat", "logs", "command_ack", "status_update", "metrics_update", "schedule_ack")
    SERVICE_ID_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    LOGS_FIELD_NUMBER: _ClassVar[int]
    COMMAND_ACK_FIELD_NUMBER: _ClassVar[int]
    STATUS_UPDATE_FIELD_NUMBER: _ClassVar[int]
    METRICS_UPDATE_FIELD_NUMBER: _ClassVar[int]
    SCHEDULE_ACK_FIELD_NUMBER: _ClassVar[int]
    service_id: str
    sequence: int
    heartbeat: Heartbeat
    logs: LogBatch
    command_ack: CommandAck
    status_update: StatusUpdate
    metrics_update: MetricsUpdate
    schedule_ack: ScheduleAck
    def __init__(self, service_id: _Optional[str] = ..., sequence: _Optional[int] = ..., heartbeat: _Optional[_Union[Heartbeat, _Mapping]] = ..., logs: _Optional[_Union[LogBatch, _Mapping]] = ..., command_ack: _Optional[_Union[CommandAck, _Mapping]] = ..., status_update: _Optional[_Union[StatusUpdate, _Mapping]] = ..., metrics_update: _Optional[_Union[MetricsUpdate, _Mapping]] = ..., schedule_ack: _Optional[_Union[ScheduleAck, _Mapping]] = ...) -> None: ...

class Heartbeat(_message.Message):
    __slots__ = ("status", "metrics")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    status: str
    metrics: SystemMetrics
    def __init__(self, status: _Optional[str] = ..., metrics: _Optional[_Union[SystemMetrics, _Mapping]] = ...) -> None: ...

class SystemMetrics(_message.Message):
    __slots__ = ("memory_mb", "cpu_percent", "uptime_seconds", "items_processed", "errors_count")
    MEMORY_MB_FIELD_NUMBER: _ClassVar[int]
    CPU_PERCENT_FIELD_NUMBER: _ClassVar[int]
    UPTIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    ITEMS_PROCESSED_FIELD_NUMBER: _ClassVar[int]
    ERRORS_COUNT_FIELD_NUMBER: _ClassVar[int]
    memory_mb: float
    cpu_percent: float
    uptime_seconds: float
    items_processed: int
    errors_count: int
    def __init__(self, memory_mb: _Optional[float] = ..., cpu_percent: _Optional[float] = ..., uptime_seconds: _Optional[float] = ..., items_processed: _Optional[int] = ..., errors_count: _Optional[int] = ...) -> None: ...

class LogBatch(_message.Message):
    __slots__ = ("entries",)
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[LogEntry]
    def __init__(self, entries: _Optional[_Iterable[_Union[LogEntry, _Mapping]]] = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ("level", "message", "timestamp", "extra")
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    EXTRA_FIELD_NUMBER: _ClassVar[int]
    level: str
    message: str
    timestamp: str
    extra: str
    def __init__(self, level: _Optional[str] = ..., message: _Optional[str] = ..., timestamp: _Optional[str] = ..., extra: _Optional[str] = ...) -> None: ...

class CommandAck(_message.Message):
    __slots__ = ("command_id", "status", "result", "error")
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    command_id: str
    status: CommandStatus
    result: str
    error: str
    def __init__(self, command_id: _Optional[str] = ..., status: _Optional[_Union[CommandStatus, str]] = ..., result: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class StatusUpdate(_message.Message):
    __slots__ = ("status", "error_message")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    status: str
    error_message: str
    def __init__(self, status: _Optional[str] = ..., error_message: _Optional[str] = ...) -> None: ...

class MetricsUpdate(_message.Message):
    __slots__ = ("items_processed_delta", "errors_count_delta")
    ITEMS_PROCESSED_DELTA_FIELD_NUMBER: _ClassVar[int]
    ERRORS_COUNT_DELTA_FIELD_NUMBER: _ClassVar[int]
    items_processed_delta: int
    errors_count_delta: int
    def __init__(self, items_processed_delta: _Optional[int] = ..., errors_count_delta: _Optional[int] = ...) -> None: ...

class ServerMessage(_message.Message):
    __slots__ = ("sequence", "heartbeat_ack", "command", "config_update", "server_status")
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_ACK_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    CONFIG_UPDATE_FIELD_NUMBER: _ClassVar[int]
    SERVER_STATUS_FIELD_NUMBER: _ClassVar[int]
    sequence: int
    heartbeat_ack: HeartbeatAck
    command: Command
    config_update: ConfigUpdate
    server_status: ServerStatus
    def __init__(self, sequence: _Optional[int] = ..., heartbeat_ack: _Optional[_Union[HeartbeatAck, _Mapping]] = ..., command: _Optional[_Union[Command, _Mapping]] = ..., config_update: _Optional[_Union[ConfigUpdate, _Mapping]] = ..., server_status: _Optional[_Union[ServerStatus, _Mapping]] = ...) -> None: ...

class HeartbeatAck(_message.Message):
    __slots__ = ("received", "server_time", "commands_pending")
    RECEIVED_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIME_FIELD_NUMBER: _ClassVar[int]
    COMMANDS_PENDING_FIELD_NUMBER: _ClassVar[int]
    received: bool
    server_time: str
    commands_pending: int
    def __init__(self, received: bool = ..., server_time: _Optional[str] = ..., commands_pending: _Optional[int] = ...) -> None: ...

class Command(_message.Message):
    __slots__ = ("id", "type", "params", "timeout_ms", "priority")
    ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    id: str
    type: str
    params: str
    timeout_ms: int
    priority: int
    def __init__(self, id: _Optional[str] = ..., type: _Optional[str] = ..., params: _Optional[str] = ..., timeout_ms: _Optional[int] = ..., priority: _Optional[int] = ...) -> None: ...

class ConfigUpdate(_message.Message):
    __slots__ = ("heartbeat_interval_seconds", "log_batch_size", "schedule_config")
    HEARTBEAT_INTERVAL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    LOG_BATCH_SIZE_FIELD_NUMBER: _ClassVar[int]
    SCHEDULE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    heartbeat_interval_seconds: int
    log_batch_size: int
    schedule_config: ScheduleConfig
    def __init__(self, heartbeat_interval_seconds: _Optional[int] = ..., log_batch_size: _Optional[int] = ..., schedule_config: _Optional[_Union[ScheduleConfig, _Mapping]] = ...) -> None: ...

class ServerStatus(_message.Message):
    __slots__ = ("accepting_connections", "message")
    ACCEPTING_CONNECTIONS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    accepting_connections: bool
    message: str
    def __init__(self, accepting_connections: bool = ..., message: _Optional[str] = ...) -> None: ...

class RegisterRequest(_message.Message):
    __slots__ = ("name", "hostname", "pid", "description", "source_code", "executable_path", "working_directory", "sdk_version", "python_version")
    NAME_FIELD_NUMBER: _ClassVar[int]
    HOSTNAME_FIELD_NUMBER: _ClassVar[int]
    PID_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_CODE_FIELD_NUMBER: _ClassVar[int]
    EXECUTABLE_PATH_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    SDK_VERSION_FIELD_NUMBER: _ClassVar[int]
    PYTHON_VERSION_FIELD_NUMBER: _ClassVar[int]
    name: str
    hostname: str
    pid: int
    description: str
    source_code: str
    executable_path: str
    working_directory: str
    sdk_version: str
    python_version: str
    def __init__(self, name: _Optional[str] = ..., hostname: _Optional[str] = ..., pid: _Optional[int] = ..., description: _Optional[str] = ..., source_code: _Optional[str] = ..., executable_path: _Optional[str] = ..., working_directory: _Optional[str] = ..., sdk_version: _Optional[str] = ..., python_version: _Optional[str] = ...) -> None: ...

class RegisterResponse(_message.Message):
    __slots__ = ("success", "service_id", "message", "server_time", "initial_config", "schedule_config")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    SERVICE_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIME_FIELD_NUMBER: _ClassVar[int]
    INITIAL_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SCHEDULE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    success: bool
    service_id: str
    message: str
    server_time: str
    initial_config: ConfigUpdate
    schedule_config: ScheduleConfig
    def __init__(self, success: bool = ..., service_id: _Optional[str] = ..., message: _Optional[str] = ..., server_time: _Optional[str] = ..., initial_config: _Optional[_Union[ConfigUpdate, _Mapping]] = ..., schedule_config: _Optional[_Union[ScheduleConfig, _Mapping]] = ...) -> None: ...

class DeregisterRequest(_message.Message):
    __slots__ = ("service_id", "reason")
    SERVICE_ID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    service_id: str
    reason: str
    def __init__(self, service_id: _Optional[str] = ..., reason: _Optional[str] = ...) -> None: ...

class DeregisterResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class ScheduleConfig(_message.Message):
    __slots__ = ("schedules", "config_version")
    SCHEDULES_FIELD_NUMBER: _ClassVar[int]
    CONFIG_VERSION_FIELD_NUMBER: _ClassVar[int]
    schedules: _containers.RepeatedCompositeFieldContainer[Schedule]
    config_version: int
    def __init__(self, schedules: _Optional[_Iterable[_Union[Schedule, _Mapping]]] = ..., config_version: _Optional[int] = ...) -> None: ...

class Schedule(_message.Message):
    __slots__ = ("id", "name", "enabled", "cron_expression", "timezone", "action_type", "action_params", "timeout_ms", "max_retries", "retry_delay_ms", "next_run_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    CRON_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    TIMEZONE_FIELD_NUMBER: _ClassVar[int]
    ACTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    ACTION_PARAMS_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    MAX_RETRIES_FIELD_NUMBER: _ClassVar[int]
    RETRY_DELAY_MS_FIELD_NUMBER: _ClassVar[int]
    NEXT_RUN_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    enabled: bool
    cron_expression: str
    timezone: str
    action_type: str
    action_params: str
    timeout_ms: int
    max_retries: int
    retry_delay_ms: int
    next_run_at: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., enabled: bool = ..., cron_expression: _Optional[str] = ..., timezone: _Optional[str] = ..., action_type: _Optional[str] = ..., action_params: _Optional[str] = ..., timeout_ms: _Optional[int] = ..., max_retries: _Optional[int] = ..., retry_delay_ms: _Optional[int] = ..., next_run_at: _Optional[str] = ...) -> None: ...

class ScheduleAck(_message.Message):
    __slots__ = ("schedule_id", "run_id", "status", "result", "error", "items_processed", "duration_ms")
    SCHEDULE_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ITEMS_PROCESSED_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    schedule_id: str
    run_id: str
    status: ScheduleRunStatus
    result: str
    error: str
    items_processed: int
    duration_ms: int
    def __init__(self, schedule_id: _Optional[str] = ..., run_id: _Optional[str] = ..., status: _Optional[_Union[ScheduleRunStatus, str]] = ..., result: _Optional[str] = ..., error: _Optional[str] = ..., items_processed: _Optional[int] = ..., duration_ms: _Optional[int] = ...) -> None: ...
