#!/usr/bin/env python3
"""
Entrega del informe de una prueba en navegador SIN leer capturas a ojo.

El problema que resuelve
------------------------
Las pruebas de interfaz construyen su informe dentro de la pagina y lo pintan
en un <pre>; Firefox headless hace la captura y ahi se queda. Eso obliga a
leer un PNG a ojo, y "lo he mirado y estaba verde" no es una prueba: es una
impresion. Peor: si la prueba revienta, la captura sale igual de bonita.

Por que no se usa --dump-dom
----------------------------
Probado en Firefox 156.0: se CUELGA. El proceso muere por timeout y por stdout
solo sale el aviso de modo headless. No sirve.

Como funciona
-------------
El script de la pagina manda el informe con un XMLHttpRequest SINCRONO a un
servidor local de un solo uso que abre este modulo.

Sincrono a proposito: Firefox toma la captura justo despues de `load` y se
marcha, asi que un `fetch` asincrono lanzado en ese mismo instante puede no
llegar a salir. Con `open(..., false)` la pagina no avanza hasta que el
servidor ha contestado, y el informe esta entregado antes de que la captura
ocurra.

El Content-Type es `text/plain` a proposito: asi la peticion es "simple" y no
dispara un preflight OPTIONS, que desde un origen `file://` (origen `null`)
seria un lio innecesario.

Uso
---
    srv = arrancar()
    diag = DIAG.replace("__ENTREGA__", srv.js("__diag"))
    ...
    srv.parar()
    informe = srv.texto()          # "" si la pagina no llego a entregarlo
"""
import http.server
import os
import re
import subprocess
import tempfile
import threading


def comprobar_scripts(html, etiqueta="la pagina"):
    """Comprueba que TODOS los bloques <script> compilan JUNTOS, como en el navegador.

    Devuelve (ok, mensaje). Se llama ANTES de abrir el navegador: cuesta
    milisegundos y convierte un fallo mudo en un error que dice el nombre.

    Por que hace falta
    ------------------
    Los bloques <script> de una pagina COMPARTEN el ambito global, pero
    `node --check` los valida uno a uno, asi que una colision entre ellos no se
    ve por ningun lado. Y en el navegador la consecuencia es SILENCIOSA: si la
    aplicacion declara `let x` y el script de la prueba declara `var x` —o al
    reves—, el script que llega despues NO COMPILA, no se ejecuta, y el unico
    sintoma es «el navegador no entrego el informe», que no dice ni que paso ni
    donde. Paso de verdad con `res` (25-sep-2026): el diagnostico de la prueba
    de estres declara `var res = txt("resultado")` y la aplicacion paso a
    declarar `let res`, asi que la prueba entera dejo de correr.

    Unir los bloques con «;» en su propia linea es seguro: si un bloque termina
    en un comentario de linea, el «;» queda en la linea siguiente y no lo
    comenta.
    """
    bloques = re.findall(r"<script>(.*?)</script>", html, re.S)
    ruta = os.path.join(tempfile.gettempdir(), "jwa-scripts-juntos.js")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n;\n".join(bloques))
    r = subprocess.run(["node", "--check", ruta], capture_output=True, text=True)
    if r.returncode == 0:
        return True, "%s: los %d bloques de script compilan juntos" % (etiqueta, len(bloques))
    m = re.search(r"SyntaxError: (.*)", r.stderr)
    linea = re.search(r"jwa-scripts-juntos\.js:(\d+)", r.stderr)
    return False, ("%s: los bloques de script NO compilan juntos -> %s%s. "
                   "Suele ser una colision de nombres en el ambito global entre la "
                   "aplicacion y el diagnostico; renombra el de la aplicacion con un "
                   "nombre especifico." % (etiqueta, m.group(1) if m else r.stderr.strip()[:200],
                                           " (linea %s del conjunto)" % linea.group(1) if linea else ""))


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

            def do_OPTIONS(self):          # por si algun navegador preflighta
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "*")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *a):
                pass                        # nada de ruido en stdout

        # puerto 0 = el que libre el sistema; asi no chocan dos pruebas a la vez
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        self.puerto = self.httpd.server_address[1]
        self.hilo = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.hilo.start()

    def js(self, id_pre):
        """JS que entrega el contenido de <pre id=...> al servidor, sincrono.

        Va al FINAL del manejador de `load`, cuando el informe ya esta armado.
        """
        return """
  /* Entrega del informe: XHR SINCRONO a proposito (ver informe_browser.py).
     Si esto no llegase, la prueba se declara NO JUZGABLE, no verde. */
  try {
    var __p = document.getElementById(%r);
    var __x = new XMLHttpRequest();
    __x.open("POST", "http://127.0.0.1:%d/informe", false);
    __x.setRequestHeader("Content-Type", "text/plain");
    __x.send(__p ? __p.textContent : ("SIN INFORME: falta #" + %r));
  } catch (e) {
    try {
      var __y = new XMLHttpRequest();
      __y.open("POST", "http://127.0.0.1:%d/informe", false);
      __y.setRequestHeader("Content-Type", "text/plain");
      __y.send("SIN INFORME: el envio fallo: " + e.message);
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
    """(codigo_de_salida, lineas_a_imprimir) a partir del informe recibido."""
    if not informe:
        return 2, ["!! el navegador no entrego el informe: la prueba NO es juzgable"]
    if informe.startswith("SIN INFORME"):
        return 2, ["!! " + informe]
    fallos = [l for l in informe.splitlines() if l.startswith("FALLO ")]
    n_ok = sum(1 for l in informe.splitlines() if l.startswith("OK "))
    if "=== TODO OK ===" in informe and not fallos:
        return 0, ["RESULTADO: todo OK (%d comprobaciones)." % n_ok]
    if exigir_ok:
        out = ["RESULTADO: %d FALLOS de %d comprobaciones." % (len(fallos), n_ok + len(fallos))]
        out += ["  - " + f[6:] for f in fallos]
        return 1, out
    return 0, []
