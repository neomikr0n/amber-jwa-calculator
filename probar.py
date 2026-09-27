#!/usr/bin/env python3
"""Test harness: injects a diagnostic script into the HTML and captures it with Firefox."""
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
    log("creatures loaded", Object.keys(C).length);
    log("model: L.length", M.L.length + "  minLv " + JSON.stringify(M.minLv));

    // --- engine check against known values ---
    log("costeADN legendary 16->20", costeADN("legendary", 16, 20, false) + "  (expected 700)");
    log("costeADN unique 21->30",    costeADN("unique", 21, 30, false) + "  (expected 3000)");
    log("costeADN apex 26->30",      costeADN("apex", 26, 30, false) + "  (expected 700)");
    log("costeADN omega 1->30 create", costeADN("omega", 0, 30, true) + "  (expected 41700)");
    log("costeADN common 1->30 create", costeADN("common", 0, 30, true) + "  (expected 346800)");
    log("costeMon unique 21->30",    costeMon("unique", 21, 30) + "  (expected 1120000)");
    log("costeMon common 1->30",     costeMon("common", 1, 30) + "  (expected 1308190)");
    log("costeMon 30->35",           costeMon("common", 30, 35) + "  (expected 1250000)");
    log("adnFus common->unique",     adnFus("common", "unique") + "  (expected 2000)");
    log("adnFus epic->apex",         adnFus("epic", "apex") + "  (expected 500)");
    log("adnFus rare->epic",         adnFus("rare", "epic") + "  (expected 50)");
    log("nFus(700)",                 nFus(700) + "  (expected 32)");
    log("nFus(3000)",                nFus(3000) + "  (expected 137)");

    // --- interaction 1: Indoraptor not created, target 35 ---
    elegir("indoraptor");
    document.getElementById("nivelAct").value = 0;
    document.getElementById("adnTengo").value = 0;
    document.getElementById("nivelObj").value = 35;
    calcular();
    log("--- Indoraptor 0->35 ---", txt("resultado").slice(0, 700));

    // --- interaction 2: with DNA half done ---
    document.getElementById("adnTengo").value = 1500;
    calcular();
    log("--- Indoraptor with 1500 DNA ---", txt("resultado").slice(0, 420));

    // --- interaction 3: save and see the table ---
    document.getElementById("btnGuardar").click();
    log("inventory after saving", JSON.stringify(INV));
    log("--- Mis criaturas ---", txt("miosCuerpo").slice(0, 400));

    // --- interaction 4: tree ---
    log("--- Arbol ---", txt("arbolCuerpo").slice(0, 700));

    // --- interaction 5: an apex from 3.22 ---
    elegir("paralidactylus");
    document.getElementById("nivelAct").value = 0;
    document.getElementById("adnTengo").value = 0;
    document.getElementById("nivelObj").value = 35;
    calcular();
    log("--- Paralidactylus 0->35 ---", txt("resultado").slice(0, 600));

    // --- interaction 6: omega ---
    elegir("93_classic_t_rex");
    document.getElementById("nivelAct").value = 0;
    document.getElementById("adnTengo").value = 0;
    document.getElementById("nivelObj").value = 35;
    calcular();
    log("--- 93 Classic T.Rex (omega) ---", txt("resultado").slice(0, 500));

    // --- interaction 7: catalysts ---
    document.getElementById("cComun").value = 20000;
    document.getElementById("cRara").value = 0;
    document.getElementById("cEpica").value = 2000;
    document.getElementById("cLegend").value = 500;
    document.getElementById("btnCat").click();
    log("--- Catalizadores ---", txt("catSalida").slice(0, 300));

    // --- tabs: that the four that remain exist ---
    /* The "Referencia" tab was removed on 25-sep-2026. It is checked that its
       button and its section are GONE, and not the other way around: a test that
       only looks at the ones that remain would still pass if someone
       reintroduced the fifth one by mistake. */
    log("tab buttons", document.querySelectorAll("nav button").length + "  (expected 4)");
    log("tabs without \u00abReferencia\u00bb",
        (!document.querySelector('nav button[data-t="ref"]') && !document.getElementById("s-ref")) +
        "  (expected true)");
    log("tab sections", document.querySelectorAll("section").length + "  (expected 4)");

    // --- search box ---
    document.getElementById("q").value = "raptor";
    document.getElementById("q").dispatchEvent(new Event("input"));
    log("search box 'raptor'", document.getElementById("lista").querySelectorAll(".it").length + " results");

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
