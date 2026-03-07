# Run: python scripts/local_webhook_receiver.py
# Then run ngrok http 8765 and use the ngrok URL as SKYFI_VALIDATION_WEBHOOK_URL
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        print("Received POST:", body.decode("utf-8", errors="replace")[:500])
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')
    def log_message(self, format, *args): pass
HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
