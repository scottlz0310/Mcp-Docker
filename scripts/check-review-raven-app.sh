#!/bin/bash
set -eu

raven_proxy_secret="${REVIEW_RAVEN_PROXY_SECRET:-}"
if [ "${#raven_proxy_secret}" -lt 32 ]; then
    printf '%s\n' 'ERROR: REVIEW_RAVEN_PROXY_SECRETは32文字以上で設定してください。' >&2
    exit 1
fi
