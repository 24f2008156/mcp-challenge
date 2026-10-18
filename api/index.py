
import hashlib
import json

from http.server import BaseHTTPRequestHandler

EMAIL = "24f2008156@ds.study.iitm.ac.in"


def make_response(request_id, result):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            request = json.loads(body or b"{}")

            method = request.get("method")
            request_id = request.get("id")

            if method == "notifications/initialized":
                self.send_response(202)
                self.end_headers()
                return

            if method == "initialize":
                result = {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "exam-mcp-server",
                        "version": "1.0.0"
                    }
                }

            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": "solve_challenge",
                            "description": (
                                "Calculate the SHA-256 challenge answer "
                                "using the challenge in the HTTP headers."
                            ),
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }

            elif method == "tools/call":
                params = request.get("params", {})
                if params.get("name") != "solve_challenge":
                    self.send_json(
                        make_response(
                            request_id,
                            {
                                "content": [{
                                    "type": "text",
                                    "text": "Unknown tool"
                                }],
                                "isError": True
                            }
                        )
                    )
                    return

                challenge = self.headers.get("X-Exam-Challenge", "")
                timestamp = self.headers.get("X-Exam-Timestamp", "")

                # The challenge must be read from the HTTP headers.
                if (
                    len(challenge) != 32
                    or any(c not in "0123456789abcdef"
                           for c in challenge)
                ):
                    answer = ""
                    is_error = True
                    message = "Missing or invalid challenge header"
                else:
                    normalized_email = EMAIL.strip().lower()
                    value = f"{challenge}:{normalized_email}"
                    answer = hashlib.sha256(
                        value.encode("utf-8")
                    ).hexdigest()[:16]
                    is_error = False
                    message = answer

                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": message
                        }
                    ],
                    "isError": is_error
                }

            else:
                self.send_json({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Method not found"
                    }
                })
                return

            self.send_json(make_response(request_id, result))

        except Exception:
            self.send_json({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": "Internal server error"
                }
            })

    def send_json(self, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
