PROTO_DIR := proto
GEN_GO := gen/go
GEN_PY := gen/python
GEN_TS := gen/ts

.PHONY: proto-go proto-py proto-ts clean

proto-go:
	mkdir -p $(GEN_GO)
	protoc --go_out=$(GEN_GO) --go_opt=paths=source_relative \
		--go-grpc_out=$(GEN_GO) --go-grpc_opt=paths=source_relative \
		$(PROTO_DIR)/*.proto

proto-py:
	mkdir -p $(GEN_PY)
	python -m grpc_tools.protoc -I$(PROTO_DIR) \
		--python_out=$(GEN_PY) --grpc_python_out=$(GEN_PY) \
		$(PROTO_DIR)/telemetry.proto $(PROTO_DIR)/detections.proto

proto-ts:
	mkdir -p $(GEN_TS)
	npx protoc --ts_out $(GEN_TS) --proto_path $(PROTO_DIR) $(PROTO_DIR)/*.proto

clean:
	rm -rf gen