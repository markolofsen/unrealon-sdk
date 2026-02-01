"""SDK constants and defaults."""

# gRPC server addresses
DEFAULT_GRPC_SERVER = "grpc.unrealon.com:443"
DEFAULT_GRPC_SERVER_LOCAL = "localhost:50051"

# Default intervals (seconds) - production
DEFAULT_HEARTBEAT_INTERVAL = 30
DEFAULT_LOG_FLUSH_INTERVAL = 3.0

# Dev mode intervals (faster for testing)
DEV_HEARTBEAT_INTERVAL = 5
DEV_LOG_FLUSH_INTERVAL = 3.0

# Default batch sizes
DEFAULT_LOG_BATCH_SIZE = 50
