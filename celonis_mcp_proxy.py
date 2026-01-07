import argparse
import json
import sys
import threading
import time
import uuid
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin, urlparse

import requests
from requests.auth import HTTPProxyAuth


class CelonisMCPProxyClient:
    """
    Celonis MCP Client with explicit proxy support.

    - Uses OAuth2 Client Credentials (preferred) or API Key.
    - Communicates via JSON-RPC 2.0 over HTTP(S) with SSE-compatible endpoints.
    - Honors corporate proxies via CLI args or environment variables.
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        team_url: Optional[str] = None,
        server_id: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        proxy_url: Optional[str] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        verify: Optional[Union[bool, str]] = None,
    ) -> None:
        # Determine Base URL and Endpoint
        if endpoint_url:
            if "?" not in endpoint_url:
                self.endpoint = f"{endpoint_url}?draft=false"
            else:
                self.endpoint = endpoint_url
            parsed = urlparse(endpoint_url)
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        elif team_url and server_id:
            self.base_url = team_url.rstrip("/")
            self.server_id = server_id
            self.endpoint = f"{self.base_url}/studio-copilot/api/v1/mcp-servers/mcp/{self.server_id}?draft=false"
        else:
            raise ValueError("Configuration Error: Missing endpoint details.")

        # Proxy setup (applies to all requests)
        self.session = requests.Session()
        if proxy_url:
            self.session.proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            if proxy_username and proxy_password:
                self.session.auth = HTTPProxyAuth(proxy_username, proxy_password)
        if verify is not None:
            # verify can be bool or path to CA bundle
            self.session.verify = verify

        # Authentication Strategy
        if api_token:
            self.token = api_token
        elif client_id and client_secret:
            self.token = self._authenticate_oauth(client_id, client_secret)
        else:
            raise ValueError("Authentication Error: Missing credentials.")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

        self.post_endpoint = None
        self.sse_thread = None
        self.shutdown_event = threading.Event()
        self.pending_requests: Dict[str, tuple] = {}
        self.endpoint_found = threading.Event()

    def _authenticate_oauth(self, client_id: str, client_secret: str) -> str:
        token_url = f"{self.base_url}/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "mcp-asset.tools:execute",
        }
        response = None
        try:
            print(f"Authenticating via OAuth2... ({token_url})")
            response = self.session.post(token_url, data=payload)
            response.raise_for_status()
            return response.json()["access_token"]
        except Exception as e:
            print(f"OAuth Authentication Failed: {e}", file=sys.stderr)
            if response is not None:
                try:
                    print(f"Auth Error Body: {response.text}", file=sys.stderr)
                except Exception:
                    pass
            sys.exit(1)

    def connect(self) -> None:
        """Establish SSE connection and set POST endpoint (same URL)."""
        print(f"Connecting to SSE at {self.endpoint}...")
        self.post_endpoint = self.endpoint
        print(f"Using POST Endpoint: {self.post_endpoint}")

        self.sse_thread = threading.Thread(target=self._listen_sse, daemon=True)
        self.sse_thread.start()
        time.sleep(1)
        print("Connected.")

    def _listen_sse(self) -> None:
        print("Starting SSE listener thread...")
        headers = self.headers.copy()
        headers["Accept"] = "application/json, text/event-stream"
        headers.pop("Content-Type", None)
        try:
            response = self.session.get(self.endpoint, headers=headers, stream=True)
            response.raise_for_status()
            print("Entering SSE loop...")
            for line in response.iter_lines(chunk_size=1):
                if self.shutdown_event.is_set():
                    break
                if not line:
                    continue
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    data_content = decoded_line[6:].strip()
                    if data_content.startswith("/") or data_content.startswith("http"):
                        if data_content.startswith("http"):
                            self.post_endpoint = data_content
                        else:
                            self.post_endpoint = urljoin(self.endpoint, data_content)
                        print(f"Discovered POST Endpoint: {self.post_endpoint}")
                        self.endpoint_found.set()
                    elif data_content.startswith("{"):
                        try:
                            msg = json.loads(data_content)
                            if "id" in msg:
                                self._handle_rpc_response(msg)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"SSE Connection Error: {e}", file=sys.stderr)
            self.shutdown_event.set()

    def _handle_rpc_response(self, msg: dict) -> None:
        req_id = msg.get("id")
        if req_id in self.pending_requests:
            event, container = self.pending_requests.pop(req_id)
            container["response"] = msg
            event.set()

    def _send_json_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Optional[dict]:
        req_id = str(uuid.uuid4())
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "id": req_id,
        }
        if params is not None:
            payload["params"] = params

        response = None
        try:
            if not self.post_endpoint:
                raise RuntimeError("POST endpoint not set. Call connect() first.")

            headers = self.headers.copy()
            headers["Accept"] = "application/json, text/event-stream"

            response = self.session.post(self.post_endpoint, headers=headers, json=payload)
            response.raise_for_status()

            result = self._parse_sse_response(response.text)
            return result
        except Exception as e:
            print(f"RPC Call Failed: {e}", file=sys.stderr)
            if response is not None:
                try:
                    print(f"Response: {response.text}", file=sys.stderr)
                except Exception:
                    pass
            return None

    def _parse_sse_response(self, sse_text: str) -> Optional[dict]:
        lines = sse_text.strip().split("\n")
        for line in lines:
            if line.startswith("data: "):
                data_content = line[6:].strip()
                try:
                    msg = json.loads(data_content)
                    if "result" in msg:
                        return msg["result"]
                    if "error" in msg:
                        print(f"JSON-RPC Error: {msg['error']}", file=sys.stderr)
                        return None
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON: {e}", file=sys.stderr)
        return None

    def list_tools(self) -> Optional[dict]:
        if not self.post_endpoint:
            self.connect()
        print("Listing tools...")
        return self._send_json_rpc("tools/list")

    def call_tool(self, tool_name: str, tool_args: dict) -> Optional[dict]:
        if not self.post_endpoint:
            self.connect()
        print(f"Calling tool '{tool_name}'...")
        params = {"name": tool_name, "arguments": tool_args}
        return self._send_json_rpc("tools/call", params)


def _build_proxy_url(args) -> Optional[str]:
    if args.proxy_url:
        return args.proxy_url
    if args.proxy_host and args.proxy_port:
        auth_part = ""
        if args.proxy_user and args.proxy_pass:
            auth_part = f"{args.proxy_user}:{args.proxy_pass}@"
        return f"http://{auth_part}{args.proxy_host}:{args.proxy_port}"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Celonis MCP Client with Proxy Support")

    # Auth args
    auth_group = parser.add_mutually_exclusive_group(required=False)
    auth_group.add_argument("--api-key", help="Celonis API Key (legacy)")
    auth_group.add_argument("--oauth", nargs=2, metavar=("CLIENT_ID", "CLIENT_SECRET"), help="OAuth2 Client ID and Secret")

    # Connection args
    conn_group = parser.add_mutually_exclusive_group(required=False)
    conn_group.add_argument("--endpoint-url", help="MCP Server Endpoint URL")
    conn_group.add_argument("--team-info", nargs=2, metavar=("TEAM", "ID"), help="Team URL and Server ID")

    # Proxy args
    parser.add_argument("--proxy-url", help="Proxy URL (e.g., http://user:pass@host:port)")
    parser.add_argument("--proxy-host", help="Proxy host")
    parser.add_argument("--proxy-port", help="Proxy port")
    parser.add_argument("--proxy-user", help="Proxy username")
    parser.add_argument("--proxy-pass", help="Proxy password")
    parser.add_argument("--no-verify", action="store_true", help="Disable TLS verification (not recommended)")
    parser.add_argument("--ca-bundle", help="Path to custom CA bundle")

    # Actions
    parser.add_argument("--action", choices=["list", "call"], default="list", help="Action to perform")
    parser.add_argument("--tool-name", help="Tool name for 'call'")
    parser.add_argument("--tool-args", help="Tool args (JSON string)")

    args = parser.parse_args()

    # Load env vars if CLI not provided
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
    except ImportError:
        os = None  # type: ignore

    api_key = args.api_key or (os.getenv("CELONIS_API_KEY") if "os" in locals() and os else None)
    client_id = None
    client_secret = None
    if args.oauth:
        client_id, client_secret = args.oauth
    elif "os" in locals() and os:
        client_id = os.getenv("CELONIS_CLIENT_ID")
        client_secret = os.getenv("CELONIS_CLIENT_SECRET")

    team_url, server_id = args.team_info if args.team_info else (None, None)
    if not team_url and "os" in locals() and os:
        team_url = os.getenv("CELONIS_TEAM_URL")
    if not server_id and "os" in locals() and os:
        server_id = os.getenv("CELONIS_SERVER_ID")

    endpoint_url = args.endpoint_url or ((os.getenv("CELONIS_ENDPOINT_URL") if "os" in locals() and os else None))

    proxy_url = _build_proxy_url(args)
    if not proxy_url and "os" in locals() and os:
        proxy_url = os.getenv("PROXY_URL")
        if not proxy_url:
            env_proxy_host = os.getenv("PROXY_HOST")
            env_proxy_port = os.getenv("PROXY_PORT")
            env_proxy_user = os.getenv("PROXY_USER")
            env_proxy_pass = os.getenv("PROXY_PASS")
            if env_proxy_host and env_proxy_port:
                auth_part = f"{env_proxy_user}:{env_proxy_pass}@" if env_proxy_user and env_proxy_pass else ""
                proxy_url = f"http://{auth_part}{env_proxy_host}:{env_proxy_port}"
    proxy_user = args.proxy_user or (os.getenv("PROXY_USER") if "os" in locals() and os else None)
    proxy_pass = args.proxy_pass or (os.getenv("PROXY_PASS") if "os" in locals() and os else None)

    verify: Optional[Union[bool, str]]
    if args.no_verify:
        verify = False
    elif args.ca_bundle:
        verify = args.ca_bundle
    else:
        verify = True

    try:
        client = CelonisMCPProxyClient(
            api_token=api_key,
            client_id=client_id,
            client_secret=client_secret,
            team_url=team_url,
            server_id=server_id,
            endpoint_url=endpoint_url,
            proxy_url=proxy_url,
            proxy_username=proxy_user,
            proxy_password=proxy_pass,
            verify=verify,
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    try:
        if args.action == "list":
            result = client.list_tools()
            if result:
                print(json.dumps(result, indent=2))
        elif args.action == "call":
            if not args.tool_name:
                print("Error: --tool-name required.")
                sys.exit(1)
            args_dict = {}
            if args.tool_args:
                try:
                    args_dict = json.loads(args.tool_args)
                except json.JSONDecodeError:
                    print("Error: Invalid JSON args.")
                    sys.exit(1)
            result = client.call_tool(args.tool_name, args_dict)
            if result:
                print(json.dumps(result, indent=2))
    except KeyboardInterrupt:
        print("\nExiting...")
        client.shutdown_event.set()


if __name__ == "__main__":
    main()
