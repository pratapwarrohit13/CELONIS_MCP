import argparse
import requests
import json
import uuid
import sys
import threading
import time
from urllib.parse import urljoin

class CelonisMCPClient:
    def __init__(self, api_token=None, client_id=None, client_secret=None, team_url=None, server_id=None, endpoint_url=None):
        """
        Initialize the Celonis MCP Client.
        """
        # Determine Base URL and Endpoint
        if endpoint_url:
            self.endpoint = endpoint_url
            parsed = requests.utils.urlparse(endpoint_url)
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        elif team_url and server_id:
            self.base_url = team_url.rstrip('/')
            self.server_id = server_id
            self.endpoint = f"{self.base_url}/studio-copilot/api/v1/mcp-servers/mcp/{self.server_id}"
        else:
            raise ValueError("Configuration Error: Missing endpoint details.")

        # Authentication
        if api_token:
            self.token = api_token
        elif client_id and client_secret:
            self.token = self._authenticate_oauth(client_id, client_secret)
        else:
            raise ValueError("Authentication Error: Missing credentials.")
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        # SSE State
        self.post_endpoint = None
        self.sse_thread = None
        self.shutdown_event = threading.Event()
        self.pending_requests = {} # {id: (Event, container)}
        self.endpoint_found = threading.Event()

    def _authenticate_oauth(self, client_id, client_secret):
        token_url = f"{self.base_url}/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "mcp-asset.tools:execute"
        }
        try:
            response = requests.post(token_url, data=payload)
            response.raise_for_status()
            return response.json()["access_token"]
        except Exception as e:
            print(f"OAuth Authentication Failed: {e}", file=sys.stderr)
            sys.exit(1)

    def connect(self):
        """
        Connects to the SSE stream and starts the listener thread.
        Waits until the POST endpoint is discovered.
        """
        print(f"Connecting to SSE at {self.endpoint}...")
        self.sse_thread = threading.Thread(target=self._listen_sse, daemon=True)
        self.sse_thread.start()
        
        if not self.endpoint_found.wait(timeout=10):
            print("Timeout waiting for endpoint from SSE.", file=sys.stderr)
            sys.exit(1)
            
        print(f"Connected. POST Endpoint: {self.post_endpoint}")

    def _listen_sse(self):
        print("Starting SSE listener thread...")
        headers = self.headers.copy()
        headers["Accept"] = "text/event-stream"
        headers.pop("Content-Type", None) 
        
        try:
            print(f"Requesting GET {self.endpoint}...")
            # Use request directly like sse_test.py
            response = requests.get(self.endpoint, headers=headers, stream=True)
            response.raise_for_status()
            
            print("Entering SSE loop...")
            for line in response.iter_lines(chunk_size=1):
                if self.shutdown_event.is_set():
                    break
                    
                if line:
                    decoded_line = line.decode('utf-8')
                    # print(f"[SSE RAW] {decoded_line}", flush=True) # Debug
                    
                    if decoded_line.startswith("event: endpoint"):
                        # The next line should be data: <url>
                        continue
                        
                    if decoded_line.startswith("data: "):
                        data_content = decoded_line[6:].strip()
                        
                        if data_content.startswith("/") or data_content.startswith("http"):
                             # It's the endpoint
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

    def _handle_rpc_response(self, msg):
        req_id = msg.get("id")
        if req_id in self.pending_requests:
            event, container = self.pending_requests.pop(req_id)
            container['response'] = msg
            event.set()

    def _send_json_rpc(self, method, params=None):
        req_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": req_id
        }
        if params is not None:
            payload["params"] = params
            
        # Prepare to wait
        event = threading.Event()
        container = {}
        self.pending_requests[req_id] = (event, container)
        
        try:
            response = requests.post(self.post_endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            
            # Wait for SSE response
            if not event.wait(timeout=30):
                print(f"Timeout waiting for RPC response to {method} (id: {req_id})", file=sys.stderr)
                return None
                
            return container.get('response', {}).get('result')

        except Exception as e:
            print(f"RPC Call Failed: {e}", file=sys.stderr)
            if 'response' in locals():
                print(f"Response: {response.text}", file=sys.stderr)
            return None
        finally:
            self.pending_requests.pop(req_id, None)

    def list_tools(self):
        if not self.post_endpoint:
            self.connect()
        print(f"Listing tools...")
        return self._send_json_rpc("tools/list")

    def call_tool(self, tool_name, tool_args):
        if not self.post_endpoint:
            self.connect()
        print(f"Calling tool '{tool_name}'...")
        params = {
            "name": tool_name,
            "arguments": tool_args
        }
        return self._send_json_rpc("tools/call", params)

def main():
    parser = argparse.ArgumentParser(description="Celonis MCP Server Client (SSE)")
    
    # Connection arguments
    auth_group = parser.add_mutually_exclusive_group(required=False)
    auth_group.add_argument("--api-key", help="Your Celonis Application Key")
    auth_group.add_argument("--oauth", nargs=2, metavar=('CLIENT_ID', 'CLIENT_SECRET'), help="OAuth2 ID and Secret")
    
    conn_group = parser.add_mutually_exclusive_group(required=False)
    conn_group.add_argument("--endpoint-url", help="MCP Server Endpoint URL")
    conn_group.add_argument("--team-info", nargs=2, metavar=('TEAM', 'ID'), help="Team URL and Server ID")

    # Action arguments
    parser.add_argument("--action", choices=["list", "call"], default="list", help="Action to perform")
    parser.add_argument("--tool-name", help="Tool name for 'call'")
    parser.add_argument("--tool-args", help="Tool args (JSON string)")

    args = parser.parse_args()

    # Parse Auth
    api_key = args.api_key
    client_id, client_secret = args.oauth if args.oauth else (None, None)
    
    # Load from Env if not provided
    if not api_key and not (client_id and client_secret):
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        # Try Env Vars
        api_key = os.getenv("CELONIS_API_KEY")
        if not api_key:
            client_id = os.getenv("CELONIS_CLIENT_ID")
            client_secret = os.getenv("CELONIS_CLIENT_SECRET")
    
    # Parse Connection
    team_url, server_id = args.team_info if args.team_info else (None, None)
    endpoint_url = args.endpoint_url
    
    if not endpoint_url and not (team_url and server_id):
        from dotenv import load_dotenv
        import os
        load_dotenv()
        endpoint_url = os.getenv("CELONIS_ENDPOINT_URL")

    try:
        client = CelonisMCPClient(
            api_token=api_key, 
            client_id=client_id, 
            client_secret=client_secret,
            team_url=team_url, 
            server_id=server_id, 
            endpoint_url=endpoint_url
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
    finally:
        # Force exit to kill daemon threads if needed, though daemon=True handles it
        pass

if __name__ == "__main__":
    main()
