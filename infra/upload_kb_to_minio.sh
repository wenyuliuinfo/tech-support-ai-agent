#!/usr/bin/env bash
#
# Upload Knowledge Base source files to MinIO using the ADR-04 layout:
#
#   knowledge-base/{document_id}/{ingestion_version}/{file_name}
#
# The script loads the repository root .env by default. Existing environment
# variables take precedence over values from the env file.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env}"
SOURCE_DIR="${SOURCE_DIR:-${REPO_ROOT}/docs/knowledge_base}"
KB_PREFIX="${KB_PREFIX:-knowledge-base}"

usage() {
  cat <<'EOF'
Usage: infra/upload_kb_to_minio.sh [--dry-run]

Uploads every non-hidden file under docs/knowledge_base to MinIO using:
  knowledge-base/{document_id}/{ingestion_version}/{file_name}

Options:
  --dry-run   Print the computed object keys without uploading.
  -h, --help  Show this help.

Environment:
  ENV_FILE             Env file to load. Default: <repo>/.env
  SOURCE_DIR           Source directory. Default: <repo>/docs/knowledge_base
  MINIO_ENDPOINT       MinIO endpoint. Default: http://localhost:9000
  MINIO_ACCESS_KEY     MinIO access key. Default: minioadmin
  MINIO_SECRET_KEY     MinIO secret key. Default: minioadmin123
  MINIO_BUCKET_NAME    Bucket name. Default: tech-support-kb
  MINIO_USE_SSL        Used when MINIO_ENDPOINT has no scheme.
  INGESTION_VERSION    Batch version. Default: UTC timestamp
  KB_PREFIX            Object prefix. Default: knowledge-base
  MINIO_ALIAS          mc alias name. Default: local
EOF
}

DRY_RUN=false
for arg in "$@"; do
  case "${arg}" in
    --dry-run)
      DRY_RUN=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -f "${ENV_FILE}" ]]; then
  # Preserve explicitly exported values so the shell override wins over .env.
  override_minio_endpoint="${MINIO_ENDPOINT-}"
  override_minio_access_key="${MINIO_ACCESS_KEY-}"
  override_minio_secret_key="${MINIO_SECRET_KEY-}"
  override_minio_bucket_name="${MINIO_BUCKET_NAME-}"
  override_minio_use_ssl="${MINIO_USE_SSL-}"
  override_ingestion_version="${INGESTION_VERSION-}"

  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a

  [[ -n "${override_minio_endpoint}" ]] && MINIO_ENDPOINT="${override_minio_endpoint}"
  [[ -n "${override_minio_access_key}" ]] && MINIO_ACCESS_KEY="${override_minio_access_key}"
  [[ -n "${override_minio_secret_key}" ]] && MINIO_SECRET_KEY="${override_minio_secret_key}"
  [[ -n "${override_minio_bucket_name}" ]] && MINIO_BUCKET_NAME="${override_minio_bucket_name}"
  [[ -n "${override_minio_use_ssl}" ]] && MINIO_USE_SSL="${override_minio_use_ssl}"
  [[ -n "${override_ingestion_version}" ]] && INGESTION_VERSION="${override_ingestion_version}"
fi

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin123}"
MINIO_BUCKET_NAME="${MINIO_BUCKET_NAME:-tech-support-kb}"
MINIO_USE_SSL="${MINIO_USE_SSL:-false}"
MINIO_ALIAS="${MINIO_ALIAS:-local}"
INGESTION_VERSION="${INGESTION_VERSION:-$(date -u +%Y%m%dT%H%M%SZ)}"

if [[ "${MINIO_ENDPOINT}" != http://* && "${MINIO_ENDPOINT}" != https://* ]]; then
  if [[ "${MINIO_USE_SSL}" == "true" ]]; then
    MINIO_ENDPOINT="https://${MINIO_ENDPOINT}"
  else
    MINIO_ENDPOINT="http://${MINIO_ENDPOINT}"
  fi
fi

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Source directory not found: ${SOURCE_DIR}" >&2
  exit 1
fi

compute_document_id() {
  local source_path="$1"

  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "${source_path}" | shasum -a 256 | cut -c1-16
  elif command -v sha256sum >/dev/null 2>&1; then
    printf '%s' "${source_path}" | sha256sum | cut -c1-16
  else
    echo "Neither shasum nor sha256sum is available." >&2
    exit 1
  fi
}

if [[ "${DRY_RUN}" == "false" ]]; then
  if ! command -v mc >/dev/null 2>&1; then
    echo "MinIO client 'mc' is not installed or not on PATH." >&2
    exit 1
  fi

  mc alias set \
    "${MINIO_ALIAS}" \
    "${MINIO_ENDPOINT}" \
    "${MINIO_ACCESS_KEY}" \
    "${MINIO_SECRET_KEY}" >/dev/null

  mc mb --ignore-existing "${MINIO_ALIAS}/${MINIO_BUCKET_NAME}" >/dev/null
fi

uploaded=0
while IFS= read -r -d '' source_file; do
  relative_path="${source_file#"${SOURCE_DIR}/"}"
  source_path="knowledge_base/${relative_path}"
  file_name="$(basename "${source_file}")"
  document_id="$(compute_document_id "${source_path}")"
  object_key="${KB_PREFIX}/${document_id}/${INGESTION_VERSION}/${file_name}"
  destination="${MINIO_ALIAS}/${MINIO_BUCKET_NAME}/${object_key}"

  if [[ "${DRY_RUN}" == "true" ]]; then
    printf 'DRY RUN source=%s document_id=%s ingestion_version=%s object=%s\n' \
      "${source_path}" \
      "${document_id}" \
      "${INGESTION_VERSION}" \
      "${object_key}"
  else
    printf 'Uploading %s -> %s\n' "${source_file}" "${destination}"
    mc cp "${source_file}" "${destination}"
  fi

  uploaded=$((uploaded + 1))
done < <(find "${SOURCE_DIR}" -type f ! -name '.*' -print0)

if [[ "${uploaded}" -eq 0 ]]; then
  echo "No files found under ${SOURCE_DIR}" >&2
  exit 1
fi

if [[ "${DRY_RUN}" == "true" ]]; then
  printf 'Dry run complete: %d file(s), ingestion_version=%s\n' \
    "${uploaded}" \
    "${INGESTION_VERSION}"
else
  printf 'Upload complete: %d file(s), ingestion_version=%s\n' \
    "${uploaded}" \
    "${INGESTION_VERSION}"
fi
