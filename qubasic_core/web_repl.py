"""QUBASIC web REPL — a single-page terminal served by the standard library.

    qubasic --web            Serve on http://127.0.0.1:8811/?t=<token>
    qubasic --web 9000       Custom port
    QUBASIC_WEB_HOST=0.0.0.0 qubasic --web    Expose on the LAN

One QBasicTerminal per server (a session, like the REPL). The page POSTs each
line to /run and appends the output. A random URL token gates every request;
the server binds to localhost unless QUBASIC_WEB_HOST says otherwise. No
external assets, no dependencies beyond the standard library.
"""

from __future__ import annotations

import io
import json
import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


_PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QUBASIC</title>
<style>
  body { background:#0a0a12; color:#c8f0c8; font:14px/1.45 Consolas, monospace;
         margin:0; display:flex; flex-direction:column; height:100vh; }
  #out { flex:1; overflow-y:auto; padding:12px; white-space:pre-wrap;
         word-break:break-all; }
  #bar { display:flex; border-top:1px solid #2a2a3a; }
  #in  { flex:1; background:#11111c; color:#e8ffe8; border:0; padding:10px 12px;
         font:inherit; outline:none; }
  .cmd { color:#7ec8ff; }
  .err { color:#ff8080; }
</style></head><body>
<div id="out"></div>
<div id="bar"><input id="in" autofocus autocomplete="off"
     placeholder="] 10 H 0   (Enter to run; HELP for commands)"></div>
<script>
const out = document.getElementById('out'), inp = document.getElementById('in');
const token = new URLSearchParams(location.search).get('t') || '';
const hist = []; let hi = 0;
function append(text, cls) {
  const d = document.createElement('div');
  if (cls) d.className = cls;
  d.textContent = text;
  out.appendChild(d); out.scrollTop = out.scrollHeight;
}
append('QUBASIC web REPL — type HELP for commands, DEMO LIST for demos.');
inp.addEventListener('keydown', async (e) => {
  if (e.key === 'ArrowUp')   { if (hi > 0) inp.value = hist[--hi]; return; }
  if (e.key === 'ArrowDown') { inp.value = (hi < hist.length - 1) ? hist[++hi] : ''; return; }
  if (e.key !== 'Enter') return;
  const line = inp.value; inp.value = '';
  if (!line.trim()) return;
  hist.push(line); hi = hist.length;
  append('] ' + line, 'cmd');
  try {
    const r = await fetch('/run?t=' + encodeURIComponent(token), {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({line})});
    const j = await r.json();
    if (j.output) append(j.output.replace(/\\n$/, ''));
  } catch (err) { append('?CONNECTION ERROR: ' + err, 'err'); }
});
</script></body></html>"""


def serve(port: int = 8811) -> None:
    from qubasic_core import __version__
    from qubasic_core.terminal import QBasicTerminal

    term = QBasicTerminal()
    term.agent_mode = True                     # confine file writes to the cwd
    token = secrets.token_urlsafe(12)
    host = os.environ.get('QUBASIC_WEB_HOST', '127.0.0.1')

    class Handler(BaseHTTPRequestHandler):
        def _authed(self) -> bool:
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            return q.get('t', [''])[0] == token

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self._authed():
                self._send(403, b'forbidden (token required)', 'text/plain')
                return
            self._send(200, _PAGE.encode('utf-8'), 'text/html; charset=utf-8')

        def do_POST(self):
            if not self._authed():
                self._send(403, b'{}', 'application/json')
                return
            length = int(self.headers.get('Content-Length', 0) or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b'{}')
                line = str(payload.get('line', ''))[:4096]
            except Exception:
                self._send(400, b'{}', 'application/json')
                return
            buf = io.StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                term.process(line, track_undo=False)
            except Exception as e:
                print(f"?ERROR: {e}")
            finally:
                sys.stdout = old
            body = json.dumps({'output': buf.getvalue()}).encode('utf-8')
            self._send(200, body, 'application/json')

        def log_message(self, *args):                       # quiet access log
            pass

    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"QUBASIC {__version__} web REPL: http://{host}:{port}/?t={token}")
    print("(Ctrl+C to stop; set QUBASIC_WEB_HOST=0.0.0.0 to expose on the LAN)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBYE")
