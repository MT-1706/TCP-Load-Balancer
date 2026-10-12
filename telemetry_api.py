
import http.server
import json
import os
import re

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GATEWAY_LOG_PATH = os.path.join(BASE_DIR, "gateway_output.log")
BACKEND_PORTS = (6001, 6002, 6003, 6004)


def get_live_cluster_metrics():
    metrics = {f"server_{port}": 0 for port in BACKEND_PORTS}
    found = set()

    if not os.path.exists(GATEWAY_LOG_PATH):
        return metrics

    try:
        with open(
            GATEWAY_LOG_PATH, "r", encoding="utf-8", errors="replace"
        ) as log_file:
            lines = log_file.readlines()

        # Read backwards so the first matching heartbeat is the latest.
        for line in reversed(lines):
            match = re.search(r"HEARTBEAT:(\d+):(\d+)", line)
            if not match:
                continue

            port = int(match.group(1))
            load = int(match.group(2))
            key = f"server_{port}"

            if port in BACKEND_PORTS and port not in found:
                metrics[key] = load
                found.add(port)

            if len(found) == len(BACKEND_PORTS):
                break

    except OSError as error:
        print(f"Could not read gateway log: {error}")

    return metrics


class UnifiedHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/metrics":
            data = get_live_cluster_metrics()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif self.path in ["/", "/index.html"]:
            filepath = os.path.join(BASE_DIR, "gui", "index.html")

            if os.path.exists(filepath):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()

                with open(filepath, "rb") as file_src:
                    self.wfile.write(file_src.read())
            else:
                self.send_error(404, "Missing gui/index.html")

        else:
            self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), UnifiedHandler)
    print(f"Telemetry API active at http://localhost:{PORT}")
    server.serve_forever()
