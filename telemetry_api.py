import http.server
import json
import os
import re

PORT = 8080
GATEWAY_LOG_PATH = '/home/mihika/Desktop/cn_project_1/gateway_output.log'

def get_live_cluster_metrics():
    metrics = {
        'server_6001': 0,
        'server_6002': 0,
        'server_6003': 0,
        'server_6004': 0
    }
    
    # Keeps track of which servers we have already updated
    found_servers = set()
    
    if not os.path.exists(GATEWAY_LOG_PATH):
        return metrics
        
    try:
        with open(GATEWAY_LOG_PATH, 'r') as fl:
            lines = fl.readlines()
            
        # Parse backwards from newest log lines
        for line in reversed(lines):
            if "HEARTBEAT:" in line:
                match = re.search(r"HEARTBEAT:(\d+):(\d+)", line)
                if match:
                    port = match.group(1)
                    load_val = int(match.group(2))
                    server_key = f"server_{port}"
                    
                    # Store the value if it's the freshest log for this server
                    if server_key not in found_servers:
                        metrics[server_key] = load_val
                        found_servers.add(server_key)
                        
            # Short-circuit early if we have found updates for all 4 servers
            if len(found_servers) == 4:
                break
    except Exception as e:
        print(f"Log parser issue: {e}")
        
    return metrics

class UnifiedHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        base_dir = '/home/mihika/Desktop/cn_project_1'
        
        # 1. API route supplying data straight to your chart vectors
        if self.path == '/api/metrics':
            data = get_live_cluster_metrics()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
            
        # 2. Serves your custom index.html dashboard file
        elif self.path in ['/', '/index.html']:
            filepath = os.path.join(base_dir, 'gui', 'index.html')
            if os.path.exists(filepath):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                with open(filepath, 'rb') as file_src:
                    self.wfile.write(file_src.read())
            else:
                self.send_error(404, 'Missing index.html inside the gui folder')
        else:
            self.send_error(404, 'Not Found')
            
    def log_message(self, format, *args):
        return

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), UnifiedHandler)
    print(f'[✓] Telemetry API Web Server Active on http://localhost:{PORT}')
    server.serve_forever()

