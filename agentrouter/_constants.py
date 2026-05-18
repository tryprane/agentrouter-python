"""
Constants for the agentrouter SDK.

The KILO_IDENTITY_HEADERS are extracted directly from the KiloCode open-source
repository (packages/opencode/src/kilocode/const.ts and
packages/kilo-gateway/src/headers.ts).

AgentRouter's gateway performs HTTP-header fingerprinting on every request and
rejects connections that don't look like they originate from an approved client.
These headers tell the gateway that the request is coming from Kilo Code, which
is on the approved list.
"""

VERSION = "0.2.0"

DEFAULT_BASE_URL = "https://agentrouter.org/v1"
DEFAULT_MODEL    = "deepseek-v4-pro"

# Exact values from kilocode/const.ts  →  DEFAULT_HEADERS
# and kilo-gateway/src/headers.ts      →  buildKiloHeaders / getDefaultHeaders
KILO_IDENTITY_HEADERS: dict[str, str] = {
    "HTTP-Referer":          "https://kilocode.ai",
    "X-Title":               "Kilo Code",
    "User-Agent":            "Kilo-Code/2.4.0",
    "X-KILOCODE-EDITORNAME": "Visual Studio Code 2.4.0",
}

DEFAULT_TIMEOUT = 120.0
DEFAULT_MAX_RETRIES = 2
