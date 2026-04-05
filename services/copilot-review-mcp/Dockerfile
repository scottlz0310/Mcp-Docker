# syntax=docker/dockerfile:1
FROM golang:1.26-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" \
    -o /out/copilot-review-mcp ./cmd/server

# distroless: no shell, no package manager
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /out/copilot-review-mcp /copilot-review-mcp
EXPOSE 8083
# Trivy DS-0002: explicitly declare non-root user (distroless:nonroot UID=65532)
USER nonroot:nonroot
ENTRYPOINT ["/copilot-review-mcp"]
