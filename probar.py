#!/usr/bin/env python3
"""Arnés de prueba: mete un script de diagnostico en el HTML y lo captura con Firefox."""
import os, re, subprocess, sys, shutil, glob

RAIZ = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(RAIZ, "amber-jwa-3.22.html")
DIR = "/tmp/jwa-test"
PERFIL = os.path.join(DIR, "perfil")
FUERA = os.path.join(DIR, "diag.html")
SHOT = os.path.join(DIR, "diag.png")

DIAG = r"""
<script>
(function(){
  var out = [];
  function log(k, v){ out.push(k + ": " + v); }
  function txt(id){ var e = document.getElementById(id); return e ? e.innerText.replace(/\s+/g, " ").trim() : "(falta " + id + ")"; }
  try {
    log("criaturas cargadas", Object.keys(C).length);
    log("modelo: L.length", M.L.length + "  minLv " + JSON.stringify(M.minLv));

    // --- comprobacion del motor contra valores conocidos ---
    log("costeADN legendary 16->20", costeADN("legendary", 16, 20, false) + "  (esperado 700)");
    log("costeADN unique 21->30",    costeADN("unique", 21, 30, false) + "  (esperado 3000)");
    log("costeADN apex 26->30",      costeADN("apex", 26, 30, false) + "  (esperado 700)");
    log("costeADN omega 1->30 crear", costeADN("omega", 0, 30, true) + "  (esperado 41700)");
    log("costeADN common 1->30 crear", costeADN("common", 0, 30, true) + "  (esperado 346800)");
    log("costeMon unique 21->30",    costeMon("unique", 21, 30) + "  (esperado 1120000)");
    log("costeMon common 1->30",     costeMon("common", 1, 30) + "  (esperado 1308190)");
    log("costeMon 30->35",           costeMon("common", 30, 35) + "  (esperado 1250000)");
    log("adnFus common->unique",     adnFus("common", "unique") + "  (esperado 2000)");
    log("adnFus epic->apex",         adnFus("epic", "apex") + "  (esperado 500)");
    log("adnFus rare->epic",         adnFus("rare", "epic") + "  (esperado 50)");
    log("nFus(700)",                 nFus(700) + "  (esperado 32)");
    log("nFus(3000)",                nFus(3000) + "  (esperado 137)");

    // --- interaccion 1: Indoraptor sin crear, objetivo 35 ---
    elegir("indoraptor");
    document.getElementById("nivelAct").value = 0;
    document.getElementById("adnTengo").value = 0;
    document.getElementById("nivelObj").value = 35;
    calcular();
    log("--- Indoraptor 0->35 ---", txt("resultado").slice(0, 700));

    // --- interaccion 2: con ADN a medias ---
    document.getElementById("adnTengo").value = 1500;
    calcular();
    log("--- Indoraptor con 1500 ADN ---", txt("resultado").slice(0, 420));

    // --- interaccion 3: guardar y ver la tabla ---
    document.getElementById("btnGuardar").click();
    log("inventario tras guardar", JSON.stringify(INV));
    log("--- Mis criaturas ---", txt("miosCuerpo").slice(0, 400));

    // --- interaccion 4: arbol ---
    log("--- Arbol ---", txt("arbolCuerpo").slice(0, 700));

    // --- interaccion 5: un apex de la 3.22 ---
    elegir("paralidactylus");
    document.getElementById("nivelAct").value = 0;
    document.getElementById("adnTengo").value = 0;
    document.getElementById("nivelObj").value = 35;
    calcular();
    log("--- Paralidactylus 0->35 ---", txt("resultado").slice(0, 600));

    // --- interaccion 6: omega ---
    elegir("93_classic_t_rex");
    document.getElementById("nivelAct").value = 0;
    document.getElementById("adnTengo").value = 0;
    document.getElementById("nivelObj").value = 35;
    calcular();
    log("--- 93 Classic T.Rex (omega) ---", txt("resultado").slice(0, 500));

    // --- interaccion 7: catalizadores ---
    document.getElementById("cComun").value = 20000;
    document.getElementById("cRara").value = 0;
    document.getElementById("cEpica").value = 2000;
    document.getElementById("cLegend").value = 500;
    document.getElementById("btnCat").click();
    log("--- Catalizadores ---", txt("catSalida").slice(0, 300));

    // --- pestanas: que existan las cuatro que quedan ---
    /* La pestana «Referencia» se quito el 25-sep-2026. Se comprueba que su boton
       y su seccion YA NO estan, y no al reves: una prueba que solo mira las que
       quedan pasaria igual si alguien reintrodujera la quinta por descuido. */
    log("botones de pestana", document.querySelectorAll("nav button").length + "  (esperado 4)");
    log("pestanas sin «Referencia»",
        (!document.querySelector('nav button[data-t="ref"]') && !document.getElementById("s-ref")) +
        "  (esperado true)");
    log("secciones de pestana", document.querySelectorAll("section").length + "  (esperado 4)");

    // --- buscador ---
    document.getElementById("q").value = "raptor";
    document.getElementById("q").dispatchEvent(new Event("input"));
    log("buscador 'raptor'", document.getElementById("lista").querySelectorAll(".it").length + " resultados");

  } catch (e) {
    log("!! EXCEPCION", e.message + "  @@ " + (e.stack || "").split("\n")[1]);
  }
  var d = document.createElement("pre");
  d.id = "__diag";
  d.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;font:10.5px/1.35 monospace;padding:10px;margin:0;overflow:auto;white-space:pre-wrap";
  d.textContent = out.join("\n");
  document.body.appendChild(d);
})();
</script>
"""

os.makedirs(DIR, exist_ok=True)
os.makedirs(PERFIL, exist_ok=True)
shutil.copy(HTML, FUERA)
with open(FUERA, "a", encoding="utf-8") as f:
    f.write(DIAG)

env = dict(os.environ)
env.update({
    "DBUS_SESSION_BUS_ADDRESS": "disabled:",
    "NO_AT_BRIDGE": "1",
    "MOZ_HEADLESS": "1",
    "MOZ_DISABLE_CONTENT_SANDBOX": "1",
    "HOME": DIR,
})
cmd = ["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL,
       "--window-size", "1500,2400", "--screenshot", SHOT, "file://" + FUERA]
r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=180)
print("rc:", r.returncode)
if r.stderr.strip():
    print("stderr:", r.stderr.strip()[:600])
print("png:", SHOT, os.path.getsize(SHOT) if os.path.exists(SHOT) else "NO")
