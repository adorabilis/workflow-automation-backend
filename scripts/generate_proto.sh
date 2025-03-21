#!/usr/bin/env bash

# Exit on error
set -e

PROTO_DIR="api/grpc/proto"

# Ensure output directory exists
mkdir -p ${PROTO_DIR}

# Generate Python code
python3 -m grpc_tools.protoc \
  --proto_path=${PROTO_DIR} \
  --python_out=${PROTO_DIR} \
  --grpc_python_out=${PROTO_DIR} \
  ${PROTO_DIR}/execution.proto

# Fix imports in generated files - handle both Linux and macOS sed versions
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS requires an extension argument for -i
  sed -i '' 's/import execution_pb2/import api.grpc.proto.execution_pb2/g' ${PROTO_DIR}/execution_pb2_grpc.py
else
  # Linux version
  sed -i 's/import execution_pb2/import api.grpc.proto.execution_pb2/g' ${PROTO_DIR}/execution_pb2_grpc.py
fi

echo "Proto files generated successfully!"
