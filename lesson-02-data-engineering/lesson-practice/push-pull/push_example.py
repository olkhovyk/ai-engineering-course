from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

events: list[dict] = []


class WebhookHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        data = json.loads(self.rfile.read(length))

        event = {
            "path": self.path,
            "data": data,
            "received_at": datetime.now().isoformat(),
        }
        events.append(event)
        print(f"[PUSH] Received: {event}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(events, indent=2).encode())


if __name__ == "__main__":
    server = HTTPServer(("localhost", 5000), WebhookHandler)
    print("[PUSH] Webhook server listening on http://localhost:5000")
    print()
    print("Test with:")
    print('  curl -X POST http://localhost:5000/webhook/payment -H "Content-Type: application/json" -d \'{"customer": "Alice", "amount": 99.99}\'')
    print('  curl http://localhost:5000/events')
    print()
    server.serve_forever()
