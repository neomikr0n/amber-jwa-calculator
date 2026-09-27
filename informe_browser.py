#!/usr/bin/env python3
"""
Delivery of the report of a browser test WITHOUT reading screenshots by eye.

The problem it solves
---------------------
The interface tests build their report inside the page and paint it into a
<pre>; headless Firefox takes the screenshot and there it stays. That forces
you to read a PNG by eye, and "I looked at it and it was green" is not a test:
it is an impression. Worse: if the test blows up, the screenshot comes out just
as pretty.

Why --dump-dom is not used
--------------------------
Tested on Firefox 156.0: it HANGS. The process dies on timeout and stdout only
shows the headless mode notice. It is no good.

How it works
------------
The page script sends the report with a SYNCHRONOUS XMLHttpRequest to a
single-use local server that this module opens.

Synchronous on purpose: Firefox takes the screenshot right after `load` and
leaves, so an asynchronous `fetch` launched at that very instant may never get
out. With `open(..., false)` the page does not move on until the server has
answered, and the report is delivered before the screenshot happens.

The Content-Type is `text/plain` on purpose: that way the request is "simple"
and does not trigger an OPTIONS preflight, which from a `file://` origin
(`null` origin) would be an unnecessary mess.

Usage
-----
    srv = arrancar()
    diag = DIAG.replace("__ENTREGA__", srv.js("__diag"))
    ...
    srv.parar()
    informe = srv.texto()          # "" if the page never delivered it
"""
import http.server
import os
import re
import subprocess
import tempfile
import threading


def comprobar_scripts(html, etiqueta="the page"):
    """Checks that ALL the <script> blocks compile TOGETHER, as in the browser.

    Returns (ok, message). It is called BEFORE opening the browser: it costs
    milliseconds and turns a silent failure into an error that names the problem.

    Why it is needed
    ----------------
    The <script> blocks of a page SHARE the global scope, but `node --check`
    validates them one by one, so a collision between them is not seen anywhere.
    And in the browser the consequence is SILENT: if the application declares
    `let x` and the test script declares `var x` —or the other way around—, the
    script that arrives later does NOT COMPILE, does not run, and the only
    symptom is "the browser did not deliver the report", which says neither what
    happened nor where. It really happened with `res` (25-sep-2026): the stress
    test diagnostic declares `var res = txt("resultado")` and the application
    went on to declare `let res`, so the whole test stopped running.

    Joining the blocks with ";" on its own line is safe: if a block ends in a
    line comment, the ";" lands on the next line and is not commented out.
    """
    bloques = re.findall(r"<script>(.*?)</script>", html, re.S)
    ruta = os.path.join(tempfile.gettempdir(), "jwa-scripts-juntos.js")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n;\n".join(bloques))
    r = subprocess.run(["node", "--check", ruta], capture_output=True, text=True)
    if r.returncode == 0:
        return True, "%s: the %d script blocks compile together" % (etiqueta, len(bloques))
    m = re.search(r"SyntaxError: (.*)", r.stderr)
    linea = re.search(r"jwa-scripts-juntos\.js:(\d+)", r.stderr)
    return False, ("%s: the script blocks do NOT compile together -> %s%s. "
                   "It is usually a name collision in the global scope between the "
                   "application and the diagnostic; rename the application one with a "
                   "specific name." % (etiqueta, m.group(1) if m else r.stderr.strip()[:200],
                                       " (line %s of the bundle)" % linea.group(1) if linea else ""))


class Servidor:
    def __init__(self):
        self.recibido = []
        self.error = None
        _yo = self

        class Manejador(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                cuerpo = self.rfile.read(n).decode("utf-8", "replace")
                _yo.recibido.append(cuerpo)
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")

            def do_OPTIONS(self):          # in case some browser preflights
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "*")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *a):
                pass                        # no noise on stdout

        # port 0 = whatever the system leaves free; that way two tests do not clash
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        self.puerto = self.httpd.server_address[1]
        self.hilo = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.hilo.start()

    def js(self, id_pre):
        """JS that delivers the content of <pre id=...> to the server, synchronously.

        It goes at the END of the `load` handler, when the report is already built.
        """
        return """
  /* Report delivery: SYNCHRONOUS XHR on purpose (see informe_browser.py).
     If this did not arrive, the test is declared NOT JUDGEABLE, not green. */
  try {
    var __p = document.getElementById(%r);
    var __x = new XMLHttpRequest();
    __x.open("POST", "http://127.0.0.1:%d/informe", false);
    __x.setRequestHeader("Content-Type", "text/plain");
    __x.send(__p ? __p.textContent : ("NO REPORT: missing #" + %r));
  } catch (e) {
    try {
      var __y = new XMLHttpRequest();
      __y.open("POST", "http://127.0.0.1:%d/informe", false);
      __y.setRequestHeader("Content-Type", "text/plain");
      __y.send("NO REPORT: the send failed: " + e.message);
    } catch (e2) {}
  }
""" % (id_pre, self.puerto, id_pre, self.puerto)

    def texto(self):
        return self.recibido[0] if self.recibido else ""

    def parar(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def arrancar():
    return Servidor()


def veredicto(informe, exigir_ok=True):
    """(exit_code, lines_to_print) from the report received."""
    if not informe:
        return 2, ["!! the browser did not deliver the report: the test is NOT judgeable"]
    if informe.startswith("NO REPORT"):
        return 2, ["!! " + informe]
    lineas = informe.splitlines()
    fallos = [l for l in lineas if l.startswith("FALLO ")]
    n_ok = sum(1 for l in lineas if l.startswith("OK "))
    # The row prefixes are a contract between this function and the tests that
    # write the report. If one side is ever translated without the other, a
    # failing run would produce zero FALLO rows and would be read as if nothing
    # had gone wrong. The marker below is written by the same helper that counts
    # the failures, so the two disagreeing proves the mismatch, and a report
    # that cannot be read must never come back green.
    if "=== FALLOS:" in informe and not fallos:
        return 2, ["!! the report declares failures but no FALLO row was found:",
                   "   the row prefix in the test does not match veredicto()",
                   "   report head: " + informe[:200].replace("\n", " | ")]
    if "=== TODO OK ===" in informe and not fallos:
        return 0, ["RESULT: all OK (%d checks)." % n_ok]
    if exigir_ok:
        out = ["RESULT: %d FALLOs out of %d checks." % (len(fallos), n_ok + len(fallos))]
        out += ["  - " + f[6:] for f in fallos]
        return 1, out
    return 0, []
