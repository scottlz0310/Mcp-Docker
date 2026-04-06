# syntax=docker/dockerfile:1
FROM golang:1.26-alpine AS builder
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" \
    -o /out/github-oauth-proxy ./cmd/server

# distroless: no shell, no package manager
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /out/github-oauth-proxy /github-oauth-proxy
EXPOSE 8084
# Trivy DS-0002: explicitly declare non-root user (distroless:nonroot UID=65532)
USER nonroot:nonroot
ENTRYPOINT ["/github-oauth-proxy"]
