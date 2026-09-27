# Ámbar — calculadora de ADN de Jurassic World Alive 3.22

Herramienta para saber **cuánto ADN, cuántas monedas y cuántas fusiones** hacen falta
para subir cualquier criatura del juego hasta el nivel que quieras, y para ver en
cascada **todos los ingredientes** que llevan a crear un híbrido.

El nombre de la herramienta vive en una sola línea de `modelo.py` (`NOMBRE`), y de ahí sale a
los **dos** sitios que lo dicen: el `<title>` y el `<h1>`. Antes estaba escrito a mano en los dos, y
ese es justo el tipo de dato que se separa sin que nadie lo note. (Aquí decía «los tres: el `<title>`,
el `<h1>` y el pie» — **el pie no lleva el nombre**, y lo comprobé contando las apariciones en el HTML
entregable: dos. No se le añadió al pie para que la frase cuadrara; se corrigió la frase.)

    calculadora-jwa-3.22.html      <- el entregable. Ábrelo con doble clic.
    img/                           <- las 518 fotos de las criaturas (WebP, 8,7 MB)
    img/favicon.svg                <- el icono de la pestaña (dibujado aquí, ver abajo)
    img/stat/ · img/res/ · img/cat/ <- iconos de stats, recursos y catalizadores
    img/clase/                     <- 7 iconos de CLASE descargados y NO usados (ver abajo)
    modelo.py                      <- el modelo de costes verificado (+ autocomprobación)
    scrape_paleo.py                <- descarga el dinodex de paleo.gg
    descargar_imagenes.py          <- descarga y convierte las fotos a WebP
    build.py                       <- junta datos + modelo y genera el HTML
    plantilla.html                 <- el HTML sin datos
    data/jwa-3.22.json             <- 518 criaturas
    cache/                         <- 519 fichas HTML crudas (no borrar si quieres re-generar)
    verificar_motor.py             <- prueba fuerte: motor del HTML vs modelo.py
    verificar_arbol.py             <- prueba fuerte: árbol de fusión nodo por nodo
    equivalencia.py                <- prueba fuerte: motor DENTRO de la página vs modelo.py
    verificar_fuentes.py           <- las etiquetas de las zonas, contra el caché de paleo.gg
    verificar_stats.py             <- los seis stats y la pista de mejoras, contra el caché
    probar_ui.py                   <- prueba de interfaz en Firefox real
    probar_estres.py               <- árbol más grande, cifras del modelo, techo de ADN y los botones
    probar_rareza.py               <- colores de rareza: calculados y auditados
    informe_browser.py             <- entrega el informe de una prueba, y comprueba que los
                                      bloques <script> compilan juntos (colisiones de nombre)
    captura.py                     <- capturas de las seis vistas, para revisar el aspecto
    captura_informe.py             <- captura SOLO el informe del árbol (default, yellow, --despues)
    probar.py                      <- prueba antigua (la sustituyen las de arriba)

## Cómo se usa

`calculadora-jwa-3.22.html` **necesita la carpeta `img/` al lado**. El HTML solo pesa
**262.117 bytes (256 KB)**; las fotos son 8,7 MB aparte. Si copias el fichero a otro sitio, cópiale también
`img/`, o verás la herramienta sin fotos (no se rompe: simplemente no las muestra).

No necesita internet, ni servidor, ni instalar nada. Se abre en cualquier navegador y
funciona sin conexión. Tus datos (nivel, ADN y si está creada, de cada criatura) se
guardan en el propio navegador, en este dispositivo, y no se envían a ningún sitio.

**El buscador está arriba, en la franja de las pestañas**, no dentro de la calculadora: se
ve en las cuatro pestañas. Escribe un nombre y **muévete con ↑ y ↓**; **Enter** lleva a la
calculadora de la criatura resaltada, y **Escape** cierra sin elegir. Ver «El buscador, y
por qué está arriba», abajo.

Cuatro pestañas:

1. **Calculadora** — **arriba del todo, una tira con hasta 10 fotos de «Mis criaturas»**:
   pulsar una carga esa criatura, igual que pulsar su fila en la pestaña de la lista. Debajo,
   **el apartado «1 · La criatura» tiene la ficha a la izquierda y los stats a la derecha, a
   la par**: la foto, la descripción, la rareza, los ingredientes y la línea «Lleva a» a un
   lado; los seis stats, los puntos de mejora y el coste de la pista al otro. Pones tu nivel y
   tu ADN, eliges el objetivo. Te da ADN necesario, ADN que
   falta, monedas, y si es híbrido: fusiones, ADN de cada ingrediente y el nivel mínimo que
   deben tener. **Debajo del nivel objetivo** te dice hasta qué nivel llegas con el ADN que
   tienes ahora mismo.
2. **Árbol de fusión** — el árbol completo hacia abajo, en cascada, con una **foto y tres
   campos editables en cada criatura** (creada, nivel, ADN). Lo que escribas se guarda al
   momento y recalcula todo lo que cuelga de ahí. **Pero no entra en «Mis criaturas»:** el
   árbol es estado de trabajo, no tu lista. Ver «Qué se guarda y qué no», abajo.
3. **Mis criaturas** — **solo lo que has guardado a propósito**, con el nivel máximo
   alcanzable hoy y el total pendiente. **Pulsa cualquier fila** (el nombre, la foto o
   cualquier hueco de la línea) y te lleva a la calculadora de esa criatura, con su nivel, su
   ADN y **su nivel objetivo** tal y como los dejaste. La × de la derecha borra sin navegar.
   Exporta e importa JSON.
4. **Catalizadores** — planificador de recombinación (**datos sin verificar**, ver abajo).

**Todos los nombres de criatura que se ven son pulsables** y llevan a su calculadora. En la
ficha de la criatura elegida, la línea **«Lleva a»** no enseña solo los hijos directos: enseña
**todas las criaturas de cada rama superior**, en orden de cercanía, **cada una con el color de
su rareza** y sin más texto que el nombre. Pulsar cualquiera carga esa criatura. Son pocas: la
mediana son 2 y el máximo 11 (Nundasuchus → Rajadorixis), así que caben en una línea.

**La pestaña «Referencia» se quitó el 25-sep-2026**, a petición de n30: era informativa y no
se usaba. Se llevó cuatro paneles: la escalera de ADN nivel a nivel, el coste por fusión, los
topes de inventario y la tabla de fiabilidad de cada dato. **Ninguna cifra se ha ido con
ella:** el modelo sigue entero y verificado, la tabla de fiabilidad está más abajo en este
documento, y la pestaña «Calculadora» aplica esos números al caso que elijas.

### El buscador, y por qué está arriba

Pedido por n30 el 25-sep-2026, en tres partes: «quiero que la búsqueda quede fuera del
apartado 1», «donde la foto y pequeña descripción de la criatura quedan abajo, debería de
estar arriba y a la par de los stats», y «si varios dinos pueden ser seleccionados en la
búsqueda, pueda seleccionarlos con las teclas de arriba y abajo y un enter dirija a la
calculadora a dicha criatura».

**Dónde vive.** El buscador salió de `#s-calc` y subió a una franja propia (`.barra-sup`) que
comparte con las pestañas. Tres consecuencias que no son de adorno:

- **Al salir de la sección, el buscador es GLOBAL:** se ve en las cuatro pestañas. Y eso
  obliga a que elegir una criatura **lleve a la calculadora**, porque si no, desde «Árbol de
  fusión» el usuario elegiría una criatura y se quedaría mirando otra pantalla. Por eso el
  clic y el Enter llaman a `irACalculadora`, no a `elegir`.
- **El ancho del buscador es fijo (290 px).** Si creciera con el texto, las pestañas se
  moverían al teclear.
- **En pantalla estrecha (≤820 px) se apila:** el buscador arriba y las pestañas debajo, que
  es como estaba antes.

**La ficha sube a la par de los stats.** Estaba a lo ancho, debajo de la rejilla; ahora es la
celda izquierda de `#filaElegir` y los stats son la derecha. No se cambió el contenido de
ninguna de las dos, solo su sitio.

**El teclado.** La lista se recorre con ↑ y ↓, se elige con Enter y se cierra con Escape.

- **El foco no sale del campo de texto.** El teclado se captura en el `<input>`, no en las
  filas: es como se comporta un desplegable de verdad, y es lo que permite seguir escribiendo
  después de moverse con las flechas. Para que un lector de pantalla sepa qué fila está
  resaltada se usa `aria-activedescendant` — sin él, la selección por teclado sería invisible
  para quien no ve la pantalla.
- **Solo se interceptan ↑ y ↓.** Las flechas horizontales, Inicio/Fin, borrar y seleccionar
  texto con Mayús se dejan intactas: un manejador que se queda con *todas* las teclas rompe el
  movimiento del cursor dentro del texto, que es lo que se espera de un campo de texto.
- **Al teclear no queda nada resaltado, y Enter no navega.** Con el buscador por subcadena
  («rex» casa con media docena), un resaltado heredado de la búsqueda anterior llevaría a una
  criatura que no es la que se acaba de escribir. Hay que bajar con ↓ para elegir.
- **El resaltado es un ÍNDICE, no una clase sobre un nodo.** La lista se rehace entera con
  `innerHTML` en cada pulsación, así que el nodo resaltado deja de existir en el pintado
  siguiente: si el resaltado viviera en el nodo, se perdería solo. El índice sobrevive porque
  apunta a la lista de resultados.
- **La lista se desplaza sola para que el resaltado quede a la vista**, con `scrollTop` a mano
  y no con `scrollIntoView`: `scrollIntoView` puede arrastrar también a los ancestros
  —incluida la página—, y aquí solo debe moverse la lista. Con 60 resultados y 330 px de alto,
  el resaltado se sale del marco en cuanto pasas de la octava fila; sin esto, el teclado
  parece «no hacer nada» aunque se esté moviendo.
- **Pasar el ratón mueve el resaltado**, para que Enter elija lo que se ve y no lo que quedó
  resaltado con el teclado antes.

**El resaltado va en `--pill` (cian), no en `--marca`.** Por lo mismo que el botón `criar`: en
«default» `--marca` vale exactamente `--r-unica`, y la lista enseña criaturas de todas las
rarezas con su etiqueta a la derecha, así que una barra verde al lado de una etiqueta verde
parecería hablar de la rareza. El cian no es color de ninguna rareza: es el color de estado de
la herramienta.

### El nivel objetivo es de cada criatura

Cada dino guarda **su propio nivel objetivo**, igual que guarda su nivel y su ADN. Lo pones
con el deslizador de la pestaña «Calculadora» y **se guarda al moverlo**, no al pulsar
*Guardar*: ese botón solo decide quién entra en «Mis criaturas». Se ve en tres sitios a la
vez —el deslizador, el informe del árbol y la columna **Objetivo** de «Mis criaturas»— y
sobrevive a recargar la página.

Antes no era así y el fallo era silencioso: había **una sola** escritura del objetivo (la del
botón *Guardar*), y al cambiar de criatura el deslizador **conservaba** el valor que tuviera
en vez de restaurar el de la nueva. Poner 30 en el Indoraptor y pasar al T-Rex le dejaba el
30 al T-Rex sin que nadie lo hubiera pedido. Corregido el 25-sep-2026.

Dos detalles que se rompen solos si alguien toca esto: el árbol saca el objetivo de su raíz
**del deslizador**, así que moverlo tiene que repintar el árbol y no solo el informe; y
`fijar()` **reemplaza** el objeto guardado entero, así que el objetivo tiene que viajar con
él o teclear el ADN de un ingrediente le borraría el objetivo a la criatura abierta.

### Qué se guarda y qué no

Hay **dos cosas distintas**, y conviene no confundirlas:

| | Qué es | Quién lo escribe |
|---|---|---|
| **Lo que tienes** | Nivel, ADN, «creada» y **nivel objetivo** de cada criatura, incluidas las del árbol | La calculadora y el árbol, al teclear; el objetivo, al mover su deslizador |
| **«Mis criaturas»** | La lista de las que has guardado | **Solo el botón «Guardar en mis criaturas»** (y la × y la importación) |

Las dos se conservan en el navegador, así que **nada de lo que teclees se pierde al
recargar**. La diferencia es la lista: teclear en el árbol sirve para calcular, pero no
añade filas. Para meter una criatura en «Mis criaturas», elige la y pulsa el botón.

Antes esto no era así: «Mis criaturas» era simplemente «todo lo que tengas datos», de modo
que editar el ADN de los ingredientes de un híbrido metía en la lista el **árbol genealógico
entero**. Pulsar *Guardar* no era la causa, sino la confirmación. Corregido el 25-sep-2026.

Los ficheros exportados llevan ahora **las dos cosas** (`mios` y `inventario`). Un fichero de
una versión anterior se sigue importando: sus criaturas pasan a la lista, que es exactamente
lo que significaban entonces.

### El informe del árbol completo

En la pestaña **Calculadora**, entre tus datos y el nivel máximo, va el **informe del árbol
completo**: todo el ADN que hace falta para llevar la criatura elegida a su nivel objetivo,
**criatura por criatura**, hasta las que se recolectan. No es un resumen del árbol: es la
lista de la compra.

| Columna | Qué es |
|---|---|
| Criatura | **el nombre, con el color de su rareza y pulsable** (carga esa criatura); con píldoras para «raíz» y **la zona donde se consigue** si hay que ir a por ella |
| Nivel | de dónde a dónde hay que subirla; solo el nivel exigido si no se paga su subida; y **`criar`** si esa criatura aún no existe (ver abajo) |
| ADN necesario | lo que esa criatura consume **en todo el árbol**: su escalera más el ADN que se le echa encima al fusionarla |
| Tienes / Falta | tu reserva de esa criatura, descontada **una sola vez** |
| Fusiones | cuántas fusiones la implican (— si no se fusiona) |

**La columna «Rareza» se quitó el 25-sep-2026**, a petición de n30: el color del nombre ya la
dice, y una columna de etiquetas repetía la misma información gastando el ancho que necesita
la de «ADN necesario».

**La columna «Veces» se quitó el 25-sep-2026**, también a petición de n30: «no da información
útil». Enseñaba en cuántas ramas del árbol salía cada criatura, un dato que solo es distinto de
1 en los ingredientes compartidos y que **no cambia ninguna decisión** — lo que cambia la
decisión es que el ADN compartido se descuenta una sola vez, y eso ya lo dicen la columna
«Tienes» y la nota de debajo. Lo que **no** se quitó es el contador que la alimentaba: `p.veces`
sigue vivo porque es lo que suma `repetidas`, y `repetidas` sale en **dos cifras del informe**
(«en N criaturas distintas, M compartidas», en la primera tarjeta) y en la propia nota. Quitar la
columna y el contador a la vez habría borrado esas dos cifras sin que nadie lo pidiera.

La nota de debajo decía «las de Veces > 1»; al quitar la columna se reescribió para decir lo
mismo **sin señalar a una columna que ya no existe**. Ahora nombra el hecho (una criatura sale
en varias ramas) y añade el único error que el usuario puede cometer ahí: sumar las filas a mano.

#### Criar desde el informe (25-sep-2026)

Petición de n30. Antes, una criatura sin crear salía **dos veces**: una píldora «sin crear» detrás
del nombre y la celda del nivel empezando por «sin crear → 20». Ahora:

- **Detrás del nombre no hay nada.** La píldora se fue; el nombre solo lleva «raíz» y la zona.
- **En la columna «Nivel» hay un botón `criar`** —en cian, el color de estado— seguido del
  objetivo: `criar → 20`. Pulsarlo **deja esa criatura en el nivel que exige la fusión** —20 en
  ese ejemplo— y la marca como creada. No se reimplementa la cuenta: llama a
  `fijar(u, "nivel", n)`, **el mismo camino que teclear el nivel en la pestaña del árbol**, así
  que no puede haber dos definiciones del mínimo que se separen con el tiempo.
- **En la fila «Total del árbol», en la columna «Nivel», sale «Criar a todas»** si hay al menos
  una criatura que no sirva. Pone al nivel de la fusión **las que no están creadas y las que
  están por debajo de ese nivel**, y **no toca la raíz ni las que ya están en ese nivel o por
  encima**.

#### Corregido el 25-sep-2026 (segunda vuelta): el nivel es el de la fusión, no el de nacimiento

n30: *«el botón de criar a todas debe poner al nivel mínimo usable para el dinosaurio de la
calculadora, ahorita mismo los cria a nivel mínimo de acuerdo a su rareza, cámbialo»*. Tenía
razón y el fallo era de definición: una criatura **en su nivel de nacimiento todavía no sirve**
para el árbol —hay que subirla—, así que el número que la fila enseñaba tras la flecha
(`criar → 20`) no era el que quedaba puesto al pulsar. Ahora sí lo es.

Lo que cambió, y por qué cada pieza:

- **El nivel objetivo es `p.objetivo`** —el que exige la fusión, o sea el mismo que ya enseñaba
  la flecha—, **nunca por debajo del nivel de nacimiento**. Una sola definición, `nivelFusion`,
  usada por la celda y por el atajo, para que no puedan separarse.
- **La raíz queda fuera**, aunque no esté creada. n30: *«la criatura raíz no se modifica,
  solamente su árbol»*. No es un capricho: la raíz no es ingrediente de nada, así que no hay
  nivel de fusión que la haga «usable», y su objetivo es el que **el usuario persigue**, no un
  mínimo que haya que alcanzar. Si se le aplicara, el informe daría por hecho que ya la tienes
  en su objetivo y la cifra de ADN necesario se desplomaría.
- **Entran las creadas que se quedaron cortas.** n30: *«solamente que o no tengan datos o que el
  dato que tengan sea menor al nivel mínimo que exige la fusión»*. Una criatura a 11 cuando la
  fusión pide 15 no sirve: sube a 15. Y las que ya están en ese nivel **o por encima** no se
  tocan — bajarlas sería borrarle al usuario niveles que ya tiene.
- **El suelo de nacimiento es load-bearing, no decorativo.** `fijar(u, "nivel", n)` marca la
  criatura como **no creada** si `n` queda por debajo de su nivel de nacimiento (lo hace para no
  dejar un nivel imposible guardado). O sea que si `nivelFusion` no llevara el `Math.max(...,
  minLv)`, un objetivo por debajo del nacimiento **descrearía** la criatura. Medido: en los 496
  pares padre→ingrediente de los datos el nivel pedido nunca baja del nacimiento (el margen
  mínimo es **+4**), así que hoy el suelo no actúa — y por eso mismo hay que sujetarlo, porque
  un cambio de datos lo activaría en silencio. Lo comprueba `verificar_fuentes.py`.
- **El atajo ya no recorre los botones.** Antes bastaba con `querySelectorAll('[data-criar]')`
  porque el conjunto era «las no creadas», y los botones eran exactamente esas. Ahora el
  conjunto es más ancho —incluye creadas que no llevan botón—, así que el informe publica la
  lista (`POR_CRIAR`) calculada **de la misma `cri` que pinta las filas**: sigue sin poder tocar
  una criatura que no salga en el informe.
- **Y el suelo de `fijar` tiene una consecuencia que se vio en un sabotaje:** con un nivel por
  debajo del nacimiento, la criatura no se queda en un nivel raro, **desaparece** (`creado:
  false, nivel: 0`). Por eso el suelo no es defensivo de más.

Tres decisiones que no son obvias:

- **El estado «sin crear» no desaparece: se muda.** Si se hubiera quitado de los dos sitios, el
  informe dejaría de decir que esa criatura no existe, y el gasto de creación (que se paga aparte
  de la escalera) quedaría invisible. Está en la columna del nivel, y además como acción.
- **El atajo trabaja sobre una lista que publica el informe (`POR_CRIAR`), no sobre los botones
  ni sobre una lista recalculada aparte.** Nació recorriendo los botones —«las sin crear» y «las
  que llevan botón» eran el mismo conjunto—, pero el 25-sep el conjunto se ensanchó a las creadas
  que se quedaron por debajo del nivel exigido, y esas no llevan botón. La lista se calcula de la
  misma `cri` que pinta las filas, así que el atajo sigue sin poder tocar una criatura que no
  salga en el informe. (Y las que ya están en el nivel o por encima quedan fuera por dos vías
  independientes: el filtro y que el objetivo de un nodo nunca baja de donde ya está.)
- **El `colspan` de la fila Total bajó de 2 a 1.** La columna «Nivel» no existía en esa fila (la
  primera celda ocupaba dos); para poner el atajo justo ahí había que crearla. Efecto lateral
  bueno: la fila Total pasa a tener **6 celdas, las mismas que la cabecera**, y deja de ser la
  única fila con una cuenta de celdas distinta. (Efecto lateral malo, y cazado: las dos pruebas
  que leían esa fila por posición empezaron a leer otra columna. Ver la trampa 16.)

Lo que **no** se tocó: la píldora «sin crear» de la pestaña **Árbol de fusión** y la de **«Mis
criaturas»** siguen donde estaban. El cambio es del informe, que es lo que se pidió.

#### ¿Son todas hembras? No

Aquí decía, siguiendo el recuerdo de n30, que **todos los dinosaurios de Jurassic World Alive son
hembras**. Se midió contra las **518 descripciones del propio juego** (`cache/*.html` →
`detail.description`) y es **falso**:

| Criatura | Lo que dice su ficha |
|---|---|
| Tyrannosaur Buck | «This **male** T. rex was once hunted by the big game hunter Roland Tembo on Isla Sorna!» |
| Tyrannosaur Doe | «This **female** T. rex is the **mate of Tyrannosaur Buck**! Can you help her find her offspring, Junior?» |
| Tarbosaurus | «Like a pride **male** lion, the Tarbosaurus becomes increasingly aggressive as it grows older» |
| Rebel | «Contrary to **his** name, Rebel is sweet and very affectionate! **He** loves to play with the humans» |
| Toro | «identical to other members of **his** species, except for **his** stunted right horn» |

Y la ficha de **Angel** lo cierra por el otro lado: «Angel is more fiery than **her brother**
Rebel». Hay, por tanto, **machos confirmados por el texto del juego**, y Buck y Doe son
literalmente **una pareja con cría** (Junior). Del lado femenino sí abundan los pronombres: Blue,
Beta («an exact clone of **her mother**, Blue»), Echo («**her sister** Blue»), Brunette («a
**female** Becklespinax»), Angel, Big Eatie («**Mother** to a young tyrannosaurus»), Scorpios Rex,
Indominus Rex Gen 2, Indolycan.

**De dónde viene el malentendido:** el canon de las películas sí dice que InGen **fabrica** a
todos los dinosaurios hembras para no poder controlar su cría (lo explica Henry Wu en *Jurassic
Park*, 1993), y ese es el recuerdo razonable. Pero las propias películas enseñan que **no se
sostuvo**: aparecen huevos fuera del laboratorio (el ADN de rana permitía cambiar de sexo), Buck y
Doe crían, y el Indoraptor de *Fallen Kingdom* es el primer macho confirmado de la trilogía
*Jurassic World*. En el juego, además, la ficha de Buck y Doe lo dice sin ambigüedad.

**Confianza: alta** para el dato del juego —está en el texto que el propio juego publica— y alta
para el matiz del canon. Lo que **no** se ha verificado es si el juego declara el sexo de las 518;
lo que se ha medido es que **al menos cinco son machos**, y eso basta para tumbar el «todas».

Esto no cambia nada del «criar»: en español «criar» aquí significa **crear y sacar adelante**, que
es lo que hace el juego al crear una criatura a partir de su ADN, no criar en el sentido de
reproducir. Pero conviene tenerlo claro, porque el juego sí tiene una pareja reproductora.

Debajo de la tabla, el **ADN que hay que ir a recolectar por rareza**, que son solo las
criaturas sin ingredientes: lo demás sale de fusionar.

Tres reglas que el informe respeta y que es fácil equivocar a mano:

- **Un ingrediente compartido es una sola reserva.** El Velociraptor sale dos veces en el
  árbol del Indoraptor (ingrediente directo suyo y de su Indominus Rex). Su ADN necesario
  es la **suma** de lo que pide cada rama, porque son fusiones distintas; pero lo que tú
  tienes se descuenta **una vez**, no una por rama. Lo avisa la nota de debajo de la tabla,
  y la cifra «N compartidas» de la primera tarjeta. (Lo avisaba la columna «Veces», retirada
  el 25-sep-2026.)
- **La escalera se paga una vez por criatura**, no una vez por aparición.
- **La raíz siempre paga su subida**, aunque el interruptor de ingredientes esté apagado:
  es el objetivo del cálculo, no un ingrediente.

### Dónde se consigue cada criatura

**Sustituye a la píldora «se recolecta» el 25-sep-2026**, a petición de n30: decir «hay que
cazarla» no servía de nada, y **dónde** cazarla es lo que se necesita para ir a por ella.

El dato no se inventó: está en `data/jwa-3.22.json`, campo `fuentes_adn` de cada criatura
(`loc` y las franjas horarias), y **las etiquetas se extrajeron del HTML de paleo.gg** que
quedó en `cache/`. Cada código tiene **una sola** etiqueta en las 518 fichas, y
`verificar_fuentes.py` lo vuelve a comprobar contra el caché cada vez: si alguien escribe una
etiqueta a mano y no coincide con la del juego, la prueba falla.

La distinción que importa, y que no es cosmética:

| | Qué es | Cómo se ve |
|---|---|---|
| **Dardeo** | zonas del mapa donde se puede lanzar un dardo | la etiqueta, tal cual: `Local Area 1`…`4`, `Park`, `Short Range`, `Everywhere`, `Continental` |
| **Combate** | de donde se saca ADN **peleando**, no dardear | la etiqueta y **`· combate`** detrás: `Arena`, `Strike Towers`, `Raid`, `Alliance Missions` |

**La Arena no es una zona de dardear** y por eso no se presenta como si lo fuera. De las **270
criaturas sin ingredientes**, que son las que antes decían «se recolecta»:

| De dónde sale | Cuántas |
|---|---|
| Zona de dardeo | **146** |
| Solo combate (Arena, Strike Towers, Raid, Alliance) | **106** |
| Dardeo **y** combate a la vez | **2** |
| **Solo en el santuario** | **4** |
| Sin fuente ninguna (omega y de evento) | **12** |

Y de los **248 híbridos**, **247 no salen en el mapa** (se fusionan) y **uno sí**: Purrolyth, que
además de fusionarse cae en Strike Towers. En total, las 518: **146 dardeo · 107 combate · 2
ambos · 4 santuario · 259 sin fuente**.

Dos cosas que se midieron y que conviene no re-descubrir:

- **El sufijo `| All Day` es redundante.** Las zonas de dardear del mapa son las cuatro franjas
  horarias, así que la etiqueta se enseña sin él. Va completo en el `title` de la píldora.
- **El santuario sí se enseña, y aquí hubo un error de método que conviene recordar.** Se dejó
  escrito que «ninguna de las 518 lo tiene como única fuente: 0 casos, comprobado». **Es falso:
  son 4** —Alioramus, Aquilops, Arsinoitherium y Titanosaurus—, y las cuatro dicen «solo en
  santuario». Lo que pasó es que la comprobación preguntaba si el conjunto de fuentes era
  **exactamente** `{sanctuary}`, y esas cuatro traen `[sanctuary, none]`. Como `none` no es una
  fuente —es «no sale en el mapa»—, el santuario **es** su único origen. **La prueba compartía
  el malentendido del dato y por eso pasaba en verde**, que es la trampa del espejo de la que
  habla más abajo. Ahora `verificar_fuentes.py` resta `none` antes de preguntar, y afirma los
  cinco recuentos uno a uno: cambiando el santuario de una sola criatura, falla y dice cuál.

**Y la píldora solo aparece si dice algo.** De las 518, **248 son híbridos y su fuente es
`none`**: a un híbrido no se le busca en el mapa, se fusiona. Decirle «sin fuente en el mapa»
sería ruido repetido en casi la mitad del dinodex. La regla, que se comprueba en `probar_ui.py`
criatura por criatura contra el modelo:

- **Las 270 sin ingredientes la llevan siempre.** Es justo el dato que hace falta para
  conseguirlas, incluidas las 16 que se quedan en «sin fuente en el mapa» (omega y de evento).
- **Un híbrido la lleva solo si de verdad sale en el mapa.** Hay exactamente **uno**:
  **Purrolyth**, que además de fusionarse cae en **Strike Towers**. Los otros 247 no la llevan.

La distinción se marca con una clase propia, `.pill.zona`, para que una prueba pueda preguntar
«¿está la píldora?» sin depender del texto que lleve dentro.

### Las fotos

Vienen del CDN de paleo.gg, `cdn.paleo.gg/games/jwa/images/creature/<uuid>.png`, a
**207×250 px**. Esa es la única resolución que existe: se probaron `@2x`, `/large/` y
`.webp` en el CDN y las tres devuelven 403. Así que 207×250 es el techo de calidad, no
una elección mía.

El PNG original pesa ~48 KB y está mal comprimido (optipng no le saca nada, pngquant lo
deja en 24 KB). Convertido a **WebP q90 baja a ~16 KB** sin diferencia visible a ese
tamaño, y eso deja las 518 en 8,7 MB en vez de 25 MB. Se nota que el arte oficial trae
fondo de color: el 97,8% de los píxeles son opacos.

**Las fotos de la tira de «Mis criaturas» van con carga ansiosa; las del árbol, vagas.** No es
un descuido: es la diferencia entre 10 imágenes y 518. Y costó encontrarlo. Con
`loading="lazy"`, las de la tira **no cargaban nunca** en el arranque normal —`naturalWidth`
0 en las tres— aunque los ficheros estuvieran bien: clones ansiosos de **las mismas
direcciones** cargaban sin problema. El síntoma era que se veía el texto alternativo en su
sitio. La primera medición no lo cazó porque pintaba la tira **dentro del propio evento
`load`**, así que daba `0x0` con `lazy` **y también con `eager`**: no distinguía nada. Hay que
medirlo en el arranque real, con la lista ya guardada en `localStorage`.

### Los stats del dino y los puntos de mejora

Donde antes estaba el desplegable «Filtrar por rareza» hay ahora el **panel de stats** de la
criatura elegida: seis números con su icono, los cuatro mandos de puntos, y lo que cuesta y
lo que da el siguiente paso de la pista de mejoras.

**Los seis números son de nivel 26, y eso no es una deducción mía.** Lo declara la propia
ficha de paleo.gg en el enlace «Compare Creatures», que lleva `compare?ck=0__<uuid>__26` en
**las 518 fichas**. Encaja con dos cosas más: el multiplicador de nivel 26 vale exactamente
`1.000000` (ver abajo) y el texto renderizado de la ficha enseña esos mismos números. Las
tres las comprueba `verificar_stats.py` contra el caché, no contra el JSON.

**La tabla de niveles no se recalcula: se copia.** `MULT_NIVEL` son 35 enteros en
milmillonésimas, copiados **verbatim** de la constante `m` del propio código de paleo.gg
(módulo 88475 de su bundle), y

    stat(L) = floor(stat26 × MULT_NIVEL[L-1] / 1e9)

**Solo la vida y el daño escalan con el nivel.** La velocidad, la armadura y los dos
críticos no: un Indoraptor de nivel 1 y uno de 35 tienen la misma velocidad.

> **La forma cerrada `1,05^(L-26)` no vale, y esto costó una corrección.** Aquí decía que
> difería «en hasta 5e-5 relativo, ~0,3 puntos de vida». **Era falso.** Al medirlo entero
> para escribir la prueba salió otra cosa: del nivel 1 al 30 la tabla **sí** es
> `1,05^(L-26)` salvo ruido de redondeo (1,5e-4 como mucho), pero **del 31 al 35 se separa a
> propósito**: son cifras redondas puestas a mano —`1,27 · 1,32 · 1,37 · 1,425 · 1,5`— y la
> forma cerrada se desvía hasta un **3,68 %** (nivel 34: 1,425 contra 1,477). En una criatura
> de 6.000 de vida son **314 puntos**, no 0,3. La prueba sujeta las dos direcciones, así que
> nadie puede «simplificar» la tabla creyendo que sobran números.

**Los puntos de mejora** («stat boosts») suman **+2 de velocidad plano** y **+2,5 % de vida y
de daño** cada uno, sobre el valor ya escalado. El tope es un **fondo común**, no un tope por
stat:

    tope = nivel de la criatura + Σ(boost_max de los pasos de la pista ya puestos)

y además cada stat por separado no pasa de **20**. O sea que para poner un punto en velocidad
cuando el fondo está lleno habría que quitarlo de otro, y eso no lo decide la interfaz: los
botones se **apagan**, no se esconden — un mando que desaparece deja de decir dónde está el
tope.

**La pista de mejoras** («enhancements») son **5 pasos**, solo para **Única (92) y Apex (55)**
—147 de 518—, y exigen **nivel 30 o más**. El orden de los pasos **no es el mismo** en las dos
rarezas, y esto también fue una corrección:

| Rareza | Paso 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Única | vida ×1,10 | daño ×1,10 | +2 velocidad | **boost_max +1** | reactivo |
| Apex | +2 velocidad | vida ×1,10 | **boost_max +2** | daño ×1,10 | reactivo |

Se había dado por supuesto un único orden para las dos. Lo desmintió una **captura**: el paso 1
del Indoraptor es vida, no velocidad. El navegador no usa esa tabla para nada —lee el tipo de
cada paso de los propios datos—; vive en `modelo.py` como documentación y `verificar_stats.py`
la comprueba contra el JSON para que no se quede desactualizada en silencio.

**El incremento se compara contra la misma criatura, al mismo nivel y sin puntos** — no contra
el nivel 26. Comparando contra el 26, una criatura de nivel 20 saldría con deltas negativos y
parecería que las mejoras quitan stats. El nivel 26 se sigue viendo, pero en el `title` de cada
ficha, junto a la base al nivel actual y el valor con tus puntos.

### El tema, y por qué el panel de stats no usa el color de marca

Hay un desplegable con dos temas: **`default`** (el de siempre) y **`yellow`** (la paleta de la
imagen: negro, naranja y ámbar). El tema se aplica como atributo `data-tema` en `<html>`, con un
script en línea en el `<head>` para que no haya destello al cargar, y `default` **no lleva
atributo** —quitarlo es volver al tema de siempre, no ponerlo en `"default"`.

La regla es que **el tema cambia decoración y nada más**. Los siete colores de rareza y los
semánticos (`--verde` alcanza, `--ambar` falta, `--rojo` error, `--azul` información) son
**idénticos en los dos temas**, y `probar_ui.py` lo mide con `getComputedStyle` sobre los 13:
leer el CSS solo demuestra que la línea está escrita.

Para poder hacer eso hacía falta separar dos cosas que compartían variable: `--marca` es el
color de **marca** (pestaña activa, botones, titulares) y cambia entre temas; `--verde`
significa **«alcanza»** y no cambia. En `default` valen el mismo hex, así que el aspecto no
cambió ni un píxel — se comprobó comparando capturas.

**Y el panel de stats tiene su propio acento, `--st-acc` (cian), por un fallo real.** El «+165»
que aportan los puntos iba con `--marca`, que en `default` vale `#4ade80`: **literalmente
`--r-unica`**. En una captura se veía el nombre `indoraptor` en verde en la tira de «Mis
criaturas» y el `+165` del panel **en el mismo verde**, en la misma pantalla. Cambiar el nombre
de la variable no bastaba —el hex seguía siendo el mismo—, así que el panel usa un tono que no
está ni en la paleta de rareza ni en la semántica. Lo cazó `probar_rareza.py`, que mide el color
**renderizado** de cada elemento y falla si alguno lleva un hex de rareza sin declararlo; se
comprobó que vuelve a fallar si se deshace el arreglo.

### El icono de la pestaña

`img/favicon.svg` es **un terópodo sobre un disco ámbar, dibujado aquí**. No es el logo de
Jurassic Park ni el de Jurassic World: esos son **marca registrada**, y copiarlos para el icono
de una herramienta no es lo mismo que homenajearlos. Se dibujó a mano con la paleta del logo
(negro y ámbar) para que se lea como lo que es sin serlo. Va incrustado en el HTML como
`data:image/svg+xml` (926 bytes), así que no depende de ningún fichero externo.

**Lo que se midió, y no lo que parece:** renderizado a 128, 64, 32, 24 y 16 px y en una barra de
pestañas simulada. La primera versión (cabeza al 1,00 con dos filas de dientes) **no se leía a 16 px**,
y aquí estaba escrito que sí: «los dientes se funden en silueta y la cabeza se sigue leyendo» era una
afirmación que **no había medido a ese tamaño**. Se probaron seis variantes y se quedó la que aguanta:
cabeza al **1,26**, **una sola fila de dientes** y el ojo más grande. Con eso, a **32 px la boca abierta
se distingue**, a 24 px todavía, y **a 16 px se lee como un disco ámbar con una mancha dentada, no como
una cabeza**. Eso es lo que hay: un icono de 16 px no da para más, y decirlo es más útil que adornarlo.

### Los colores de las rarezas

**No son los del juego: son una elección de n30**, pedida el 24-sep-2026.

| Rareza | Color | Hex | Contraste sobre el panel más claro |
|---|---|---|---|
| Común | blanco | `#f1f5f9` | 14,7:1 |
| Rara | azul | `#60a5fa` | 6,3:1 |
| Épica | amarillo | `#fbbf24` | 9,6:1 |
| Legendaria | rojo | `#f87171` | 5,8:1 |
| Única | verde | `#4ade80` | 9,2:1 |
| Apex | morado | `#c084fc` | 6,1:1 |
| **Omega** | fucsia | `#f472b6` | 6,1:1 |

Los siete pasan el mínimo de contraste **AA (4,5:1)** con margen, y también sobre la fila
verde de la raíz del informe. El rojo del apex anterior (`#ef4444`) se quedaba en **4,3:1**:
por debajo. Ese es el motivo de que el rojo sea un rojo claro y no uno puro.

**Omega no estaba en la lista.** Antes era violeta (`#a78bfa`, 255° de tono), que es
prácticamente el morado que ahora pide el apex (270°): **a 15° de distancia se confundían**.
Se movió a fucsia (329°), a 59° del morado. Si prefieres otro tono para omega, es una línea.

**Cuatro de estos colores son el MISMO hex que colores que la interfaz ya usaba para otra
cosa.** No es parecido: es el mismo valor.

| Hex | Rareza | Y también |
|---|---|---|
| `#4ade80` | Única | `--verde`: pestaña activa, cifra «ya te alcanza», «Alta», «buena», títulos |
| `#fbbf24` | Épica | `--ámbar`: «Te faltan N ADN», «sin crear», «sale ×N», «Media-alta», borde de aviso |
| `#f87171` | Legendaria | `--rojo`: cifra de déficit, «mala: quema la más escasa», «Baja» |
| `#60a5fa` | Rara | `--azul`: borde del aviso informativo |

**Las píldoras de estado se movieron a cian** (`--pill: #22d3ee`, 188°, 8,9:1) por decisión de
n30: eran el sitio donde el choque se veía dentro de la misma fila (una criatura Única con la
píldora «raíz» del mismo verde). Ahora el color de rareza no se usa en ninguna píldora.

**El resto del choque sigue ahí, y está medido.** En la pantalla del árbol hay **37 elementos
que no son etiquetas** y llevan el hex de una rareza: 14 en verde, 18 en ámbar, 4 en azul y 1
en rojo. `probar_rareza.py` los lista uno a uno y **falla si aparece uno nuevo que no esté
declarado**, para que el choque no se pueda volver a esconder detrás de un «todo OK».

**Y hay tres sitios donde el color de rareza se usa a propósito, con la criatura nombrada.** No
son colisiones: son la función. Los tres los comprueba `probar_ui.py` **criatura por criatura**,
no solo que el color exista:

| Dónde | Qué se pinta |
|---|---|
| Etiqueta de rareza (`.tag`) | la ficha con fondo del 12%, en el árbol, la ficha y el informe |
| **Nombre en el informe del árbol** | el nombre **es** la columna de rareza desde que se quitó la suya |
| **Nombres de «Lleva a»** | el color dice a qué rareza lleva cada rama superior |

Que un nombre y una cifra compartan verde se distingue por la forma: el nombre pulsable lleva
el color de su rareza y **subrayado al pasar por encima**; la cifra es texto suelto. Regla de
lectura, ya completa: **insignia con fondo = rareza; nombre coloreado = la criatura y su
rareza; texto suelto = estado.**

**La etiqueta de rareza lleva fondo, y por eso ya no se confunde con un número.** Decisión de
n30: un tinte del **12% de su propio color** (`background: color-mix(in srgb, currentColor 12%,
transparent)`). Con eso la regla de lectura queda: **insignia con fondo = rareza; texto suelto =
estado**. El verde de `ADN NECESARIO` no lleva fondo; la etiqueta `ÚNICA` sí.

**El 12% no es un número al azar.** El tinte sube la luminosidad justo debajo del texto, así que
**baja** el contraste. Medido sobre el panel más claro (`#1d212c`):

| Tinte | Peor contraste (rojo de Legendaria) | |
|---|---|---|
| 0% | 5,81:1 | el de antes |
| **12%** | **4,89:1** | **elegido: sigue por encima de AA** |
| 16% | 4,56:1 | demasiado justo |
| 18% | 4,44:1 | **suspende AA** |

El valor lo vuelve a medir `probar_rareza.py` en el navegador —compone el fondo translúcido sobre
el primer ancestro opaco y calcula el contraste WCAG— en vez de fiarse del número escrito aquí.

**El CSS no pinta ninguna foto con el color de su rareza. Pero las fotos sí llevan un marco de
color, y viene dentro del fichero.** Las dos frases son verdad a la vez y hubo que medir las dos
para no escribir una mentira.

1. **Lo que pinta el CSS es neutro.** Medido con `getComputedStyle`: `.arbol .foto` tiene borde
   `#272c3a` en las cinco fotos, y `.arbol .nodo` también (salvo la raíz, `#2f4a3a`, que es su
   fondo verde oscuro y no está en la paleta). Ninguna regla de la hoja usa `--r-*` para un borde.
2. **Lo que se ve es un marco de color, y lo trae el WebP de paleo.gg ya dibujado.** Medido sobre
   las **518 imágenes** (el anillo exterior de cada una, agrupado por rareza):

| Rareza | n | Marco de la imagen | Familia de tono | Etiqueta | Diferencia |
|---|---|---|---|---|---|
| Común | 48 | `#404040` | neutro | `#f1f5f9` | — |
| Rara | 85 | `#002080` | azul | `#60a5fa` | 12° |
| Épica | 105 | `#802000` | naranja | `#fbbf24` | 28° |
| Legendaria | 100 | `#800000` | rojo | `#f87171` | 0° |
| Única | 92 | `#002000` | verde | `#4ade80` | 22° |
| Apex | 55 | `#000000` | neutro | `#c084fc` | — |
| Omega | 33 | `#c0e0e0` | neutro | `#f472b6` | — |

Son los colores de rareza **del juego**, en versión oscura y apagada. En tono **coinciden** con
los que pidió n30, así que el marco y la etiqueta se refuerzan en vez de pelearse. En Apex y
Omega el marco es negro y casi blanco: su foto no dice la rareza, y la única señal es la
etiqueta.

**Consecuencia práctica:** no se puede cambiar el marco desde el CSS, porque no es del CSS. Si
alguna vez molesta, hay que recortar o retocar los 518 WebP, no la hoja de estilos.

`probar_rareza.py` mide las dos capas y **falla si dejan de contar lo mismo**: si las imágenes de
una misma rareza dejan de compartir familia de tono (el marco ya no se podría leer como rareza) o
si el tono del marco se aleja más de 60° del de la etiqueta (la misma fila diría dos rarezas
distintas). La frase que antes había aquí —«las fotos no llevan el color de la rareza»— salió de
mirar solo la primera capa, y era falsa.

### «Creada» o «sin crear»

Es la distinción que más se equivoca al calcular a mano. Una criatura que **no existe
todavía** cuesta, además de su escalera, el ADN de crearla:

| Rareza | Nace en | Crear cuesta |
|---|---|---|
| Común | 1 | 50 |
| Rara | 6 | 100 |
| Épica | 11 | 150 |
| Legendaria | 16 | 200 |
| Única | 21 | 250 |
| Apex | 26 | 300 |
| Omega | 1 | 100 |

Por eso cada nodo tiene la casilla **Creada**. Destildada, el cálculo suma el ADN de
creación y la criatura se trata como nivel 0. Al volver a tildarla, sube a su nivel de
nacimiento.

Ojo con una consecuencia que sorprende si no se sabe: **el nivel no puede bajar del de
nacimiento sin que la criatura deje de estar creada.** Si en la calculadora escribes un nivel
por debajo (una única no puede estar en nivel 18: nace en 21), al salir del campo el número se
corrige a 0 y la criatura queda como «sin crear», que es lo que de verdad se guarda. Lo mismo
con el ADN: no se admiten negativos.

### Nivel máximo obtenible

Debajo del nivel objetivo, y también en cada nodo del árbol, la herramienta dice hasta
qué nivel llegas **con el ADN que tienes ahora**, cuánto gastarías y cuánto te sobraría.
El cálculo es: pagar la creación si hace falta, y luego subir peldaño a peldaño mientras
el siguiente quepa en el ADN disponible. No es una estimación: es la escalera real.


## El modelo de costes, y por qué me fío de él

Todo esto está **contrastado**, no supuesto. La validación principal: el modelo reproduce
**exactamente** los tres números que paleo.gg muestra en su propio calculador (ADN del
híbrido, monedas de subida, monedas de fusión) en **221 fichas de híbrido**, sin una sola
discrepancia.

### Escalera de ADN

Una **sola** escalera compartida por todas las rarezas. Lo único que cambia es el nivel al
que nace cada criatura:

| Rareza | Nace en | Crear cuesta | Tope de ADN |
|---|---|---|---|
| Común | 1 | 50 | 850.000 |
| Rara | 6 | 100 | 250.000 |
| Épica | 11 | 150 | 85.000 |
| Legendaria | 16 | 200 | 25.000 |
| Única | 21 | 250 | 8.000 |
| Apex | 26 | 300 | 3.000 |
| Omega | 1 | 100 | 60.000 |

El coste de subir del nivel `a` al `b` es la suma de la escalera entre esos niveles.
**El coste de creación va aparte** — es lo que hace paleo.gg: "de 16 a 20" son 700 ADN, sin
contar los 200 de crear.

Totales de referencia (ADN):

| Rareza | 1→30 | 30→35 | 1→35 |
|---|---|---|---|
| Común | 346.800 | 500.000 | 846.800 |
| Rara | 116.850 | 150.000 | 266.850 |
| Épica | 34.400 | 50.000 | 84.400 |
| Legendaria | 11.450 | 15.000 | 26.450 |
| Única | 3.250 | 5.000 | 8.250 |
| Apex | 1.000 | 2.000 | 3.000 |
| Omega | 41.700 | 22.500 | 64.200 |

### Fusión

El ADN que consume cada fusión depende **solo del salto de rareza** entre el ingrediente y
el híbrido. Verificado sin ambigüedad en 191 híbridos: cada combinación observada da un
único valor.

| Salto | ADN por fusión | Ejemplo |
|---|---|---|
| 1 | 50 | épica → legendaria |
| 2 | 200 | rara → legendaria |
| 3 | 500 | rara → única |
| 4 | 2.000 | común → única (Velociraptor → Indoraptor) |

Monedas por fusión, según la rareza del **híbrido**: rara 20 · épica 100 · legendaria 200 ·
única 1.000 · apex 2.000.

Nivel mínimo de los ingredientes: **uno menos que el nivel de creación del híbrido**.
Para un híbrido único (nace en 21) los ingredientes van a **nivel 20**.

### La media de 22 ADN por fusión

Es una **media**, no un valor fijo: cada fusión da una cantidad aleatoria. Los tres
coinciden en que 22 es la cifra de trabajo:

- paleo.gg lo dice literalmente: *"Assuming an average of 22 DNA per fuse"*.
- La tabla de probabilidades de la wiki da una esperanza de **22,228** (1,03% de desviación).
- Tu dato medido en el juego: 22.

Consecuencia práctica: **las fusiones calculadas son una estimación**. Puede hacerte falta
alguna más.

### Los ingredientes: dos criterios

El árbol tiene una casilla, **marcada por defecto**:

- **Marcada** — cuenta también el ADN de **subir los ingredientes** al nivel que exige la
  fusión. Es lo que de verdad hay que reunir.
- **Desmarcada** — imita a paleo.gg, que asume que los ingredientes *"ya están listos para
  fusionar"* y solo cuenta el ADN que se consume en las fusiones.

Los dos criterios están verificados contra paleo.gg. Ejemplo, Alankydactylus de 26 a 30:

| | Desmarcada (paleo.gg) | paleo.gg dice |
|---|---|---|
| Alankydactylus | 700 ADN · 32 fusiones · 64.000 mon. | 700 · 64.000 ✓ |
| Dreadactylus | 6.400 ADN · 291 fus. · 58.200 mon. | 6.400 · 58.200 ✓ |
| Preondactylus | 58.200 ADN | 58.200 ✓ |
| Dreadnoughtus | 58.200 ADN | 58.200 ✓ |
| Alankyloceratops | 1.600 ADN · 73 fus. · 73.000 mon. | 1.600 · 73.000 ✓ |

La casilla manda también en el **informe del árbol completo**, y el informe **dice cuál de
los dos criterios está usando** (con un aviso azul cuando es el de paleo.gg). Sin ese aviso,
la misma pantalla daba dos respuestas distintas según una casilla que está en otra pestaña, y
ninguna de las dos se identificaba. Ejemplo con Indoraptor 21→30 e Indominus Rex a medias:

| | Casilla marcada | Casilla desmarcada |
|---|---|---|
| ADN que falta en total | 281.250 | 262.100 |
| A recolectar | 274.400 | 255.950 |
| Monedas | 1.380.200 | 1.248.800 |
| Columna «Nivel» de un ingrediente | `16 → 20` | `20` |

Con la casilla desmarcada, la columna «Nivel» de un ingrediente enseña **solo el nivel que le
exige la fusión**: no se paga su subida, así que un rango haría creer que sí. La raíz es la
excepción y conserva su rango, porque su escalera siempre se paga.

## Fiabilidad de cada dato

| Dato | Confianza | Por qué |
|---|---|---|
| Escalera de ADN 1→30 | **Alta** | Reproduce los 14 totales conocidos y las 221 fichas de paleo.gg |
| Tramo 31→35 | **Alta** | Comunicado oficial de la 3.22 |
| Coste por fusión (50/200/500/2000) | **Alta** | Unánime en 191 híbridos |
| Monedas por fusión | **Alta** | Coincide con paleo.gg y con el código de la app |
| Nivel mínimo de ingredientes | **Alta** | Regla explícita en la wiki |
| Topes de inventario de ADN | **Alta** | Fuente **oficial**, 31-ago-2026 |
| Media de 22 ADN por fusión | **Alta en la media** | Cada fusión concreta es aleatoria |
| Los 6 stats de cada criatura | **Alta** | Son de nivel 26 (lo declara la ficha) y coinciden con el JSON y con el texto renderizado: 3.108 números |
| Que los stats sean de nivel 26 | **Alta** | El enlace «Compare Creatures» de las 518 fichas lleva `__26` |
| Los 735 pasos de las mejoras | **Alta** | Coinciden con las **dos** copias que trae la ficha (`enhancements` y `evolutionData`) |
| `MULT_NIVEL` (tabla de niveles) | **Alta** | Copiada **verbatim** del bundle de paleo.gg; la forma cerrada se midió y **no** la reproduce |
| +2 / +2,5 % por punto de mejora | **Media-alta** | Es la función `i(e,t,a)` del módulo 88475 de paleo.gg |
| Escalera del Omega | **Media-alta** | Base de datos del juego, con una corrección de patrón |
| Tasas de catalizadores | **Baja** | Terceros; el juego no las publica |

## Dos cosas que conviene saber

**El tope de ADN te obliga a hacer tandas.** Si necesitas más ADN del tope de esa rareza,
la calculadora te lo avisa y te dice en cuántas tandas tendrás que reunirlo. Una única
criatura no puede pasar de 8.000 de ADN, así que un Indoraptor a nivel 35 (8.250) exige dos
tandas sí o sí.

**Los catalizadores son otro eje.** No sirven para subir de nivel: son para las **mejoras
(enhancements)**. La pestaña de catalizadores usa los pesos y las recetas observadas por
idgt902 (guía de ago-2025) porque **el juego no publica las tasas**. Trátalos como
orientativos.

## Sobre las criaturas de la 3.22

paleo.gg marca **9 criaturas con versión v3.22**, mientras que las notas oficiales solo
anuncian **2** (Cryolophosaurus Mattel y Stomatosuchus Mattel). Las otras siete son:

| Criatura | Rareza | Tipo |
|---|---|---|
| Aliorasuchus | Única | gigahíbrido |
| Arsinoitherium | Rara | sin híbrido |
| Arsionosaurus | Épica | híbrido |
| Indoraptor Mattel | Apex | sin híbrido |
| Koolatrax | Única | superhíbrido |
| Koolatrodon | Épica | híbrido |
| Paralidactylus | Apex | megahíbrido |

Las tres de Mattel salen de un evento, no de las notas de la versión.

## Lo que está descargado y sin usar: los iconos de clase

`img/clase/` tiene **7 iconos** —`cunning` · `cunning_fierce` · `cunning_resilient` · `fierce` ·
`fierce_resilient` · `resilient` · `wild_card`—, **42.733 bytes** en total, y **el HTML no los cita
ni una vez** (`grep -c "img/clase" plantilla.html` → 0). Son exactamente las **7 clases** que trae
el dato: `data/jwa-3.22.json` → `criaturas[u].clase` existe en **las 518 criaturas** y solo toma
esos 7 valores (resilient 111 · cunning 105 · fierce 75 · fierce_resilient 63 · wild_card 59 ·
cunning_fierce 55 · cunning_resilient 50).

O sea: **el dato está, los iconos están, y la interfaz no enseña ninguno de los dos.** Se
descargaron para un panel de clase que no llegó a hacerse. No se han borrado (regla de la casa:
no se borra, se avisa), y no ocupan nada en el entregable porque nadie los referencia.

Si algún día se enseña la clase, el sitio natural es el **panel de stats**, al lado de la rareza,
que ya tiene su propia fila de seis iconos. Y hay que decidir antes si se enseña la clase **en
palabras o en icono**: el icono solo funciona si el usuario ya sabe qué es «Cunning», así que
probablemente haga falta el nombre además del dibujo.

## Re-generar los datos

    python3 scrape_paleo.py     # vuelve a bajar el dinodex (usa la caché, solo lo que falte)
    python3 modelo.py           # autocomprobación del modelo (40 comprobaciones)
    python3 build.py            # regenera el HTML

`scrape_paleo.py --refetch` vuelve a bajarlo todo. Comprueba la integridad del grafo:
referencias rotas, huérfanos y ciclos.

## Pruebas

- `python3 modelo.py` — 40 comprobaciones del modelo, **más 767 casos de nivel máximo**
  comprobados por invariantes de ida y vuelta (si dice que llegas al nivel N, `coste_adn`
  hasta N tiene que caber en el ADN y hasta N+1 no). **Todo correcto.**
- `python3 verificar_motor.py` — **la prueba fuerte.** Primero pasa `node --check` a todos
  los bloques `<script>`; luego extrae el motor *real* del HTML entregable (no la
  plantilla, no una copia) y lo ejecuta en Node comparando cada cifra contra `modelo.py`.
  **960/960 campos de coste y 9.408/9.408 campos de nivel máximo, idénticos.** Sin
  capturas ni lectura visual: si algo difiere, falla con código 1.
  Además hace dos comprobaciones que no son de cálculo, y que existen porque las dos
  fallaron de verdad: **reconstruye el HTML a un temporal y exige que el fichero en disco
  sea exactamente eso** (un editor había reescrito el entregable por encima, y una
  plantilla editada sin reconstruir da el mismo síntoma), y **recalcula los tamaños que
  afirma este LEEME** para que un número escrito a mano no envejezca en silencio.
- `python3 verificar_arbol.py` — igual pero para el **árbol de fusión**: 15 casos con
  inventarios simulados, los dos criterios (coste real y criterio de paleo.gg), los dos
  estados de cada criatura (creada y sin crear) y datos heredados sin el campo `creado`.
  **64 nodos × 13 campos + 15 totales, todos idénticos.**
- `python3 probar_ui.py` — prueba de interfaz en Firefox headless: que los campos existan y
  respondan al teclado, que el foco no se pierda al repintar, que se guarde, y que **las
  imágenes referenciadas carguen y decodifiquen** (`naturalWidth > 0`, que es la única
  forma de distinguir «hay un `<img>`» de «se ve el dinosaurio»). Incluye el **tecleo dígito a
  dígito** con comprobación de la posición del cursor en cada paso —el fallo que ninguna otra
  prueba podía ver—, la **regla de la lista** (teclear en el árbol no añade criaturas, y
  Guardar añade exactamente una), **la tira de fotos** (que cada foto cargue, sea pulsable y
  cargue su criatura), **«Lleva a»** (que el cierre transitivo cuadre, que no se repita nadie
  aunque el grafo tenga diamantes, que cada nombre lleve el color de su rareza y que pulsarlo
  navegue), **los nombres del informe** (mismo color, misma navegación, y que **ni la columna
  «Rareza» ni la «Veces» vuelvan**: las dos se retiraron a petición de n30, el 25-sep-2026) y
  **la zona** (que la píldora diga lo que dice el modelo, criatura por
  criatura, que «se recolecta» no aparezca ya en ninguna parte, y que **la píldora solo salga
  cuando dice algo**: las 270 sin ingredientes la llevan siempre, y de los 248 híbridos solo
  la lleva el que de verdad sale en el mapa —Purrolyth, en Strike Towers—, porque a un híbrido
  no se le busca, se fusiona). **128 comprobaciones en la primera pasada y 3 en la segunda.**
  Desde el 25-sep cubre además el buscador y su teclado: que viva en la franja de las pestañas
  y **fuera** de la calculadora, que la ficha esté **a la par** de los stats, que la lista
  **no se despliegue sola** al tocar el árbol (era un defecto real, ver la trampa 21), que ↓
  resalte la primera y **una sola**, que ↑ y ↓ muevan el resaltado sin salirse por los
  extremos, que **no se traguen** las demás teclas, que el resaltado **siga a la vista** tras
  25 pulsaciones, que **Enter lleve a la calculadora** aunque se pulse desde otra pestaña y
  elija justo la criatura resaltada, que **Escape cierre sin elegir**, y que
  `aria-expanded`/`aria-activedescendant` acompañen al estado.
  Desde el 25-sep cubre además el panel de stats: que el filtro de rareza ya no esté, que los
  seis números sean **los del dato a nivel 26 escritos como literales** (no los del modelo),
  que solo vida y daño escalen, que los puntos se guarden, que el tope por stat corte en 20,
  que un import pasado de tope se acote **y se guarde acotado**, que el paso 3 del Apex dé +2
  y el de la Única no, que por debajo de 30 la pista se acote a 0 **también en el inventario**,
  que los 13 colores de rareza y semánticos sean idénticos en los dos temas mientras la marca y
  el fondo cambian, y que el favicon sea un `data:image/svg+xml` **y cargue**.
- `python3 verificar_fuentes.py` — **el mapa de zonas no es folclore.** Vuelve a extraer las
  etiquetas de `cache/` (el HTML de paleo.gg) y las compara con las que lleva el entregable:
  cada código usado tiene que tener **la misma etiqueta** que en el juego, ninguno puede ser
  dardeo y combate a la vez sin declararlo, y el reparto de las 518 se afirma **categoría por
  categoría** (146 dardeo · 107 combate · 2 ambos · 4 santuario · 259 sin fuente). **30
  comprobaciones.** Se comprobó que **falla de verdad**, y de dos formas: cambiando
  `local_area_1` por «Zona 1» a mano acusa la discrepancia, y quitándole el santuario a una de
  las cuatro criaturas que solo se consiguen ahí, dice cuál y sale con código 1.
  Y desde el 25-sep comprueba además una **invariante del modelo, no del mapa**: que el nivel que
  exige una fusión **nunca quede por debajo del nivel de nacimiento del ingrediente**, en los
  **496 pares** padre→ingrediente de los datos (margen mínimo **+4**, máximo **+19**). Existe
  porque de eso depende que el suelo de `nivelFusion` no tenga que actuar: si algún día actuara,
  el botón `criar` pondría la criatura en su nacimiento en vez de en el nivel pedido, en silencio.
- `python3 probar_estres.py` — la que cubre lo que las demás no: **el árbol más grande del
  juego** (Rajadorixis, 15 nodos) con su profundidad de anidamiento real y su tiempo de
  repintado (0,5 ms, o 8,8 ms por tecla en un campo del fondo); el aviso del **techo de ADN**
  cuando el déficit supera el tope de la criatura; **las cifras del modelo** (coste por fusión,
  topes, niveles de nacimiento, ADN para crear, monedas) contra los valores **documentados**;
  el **bloque de nivel máximo de cada nodo**, contrastado con `nivelMaximo()`; **exportar /
  borrar / importar pulsando los botones de verdad**, con un `FileReader` doble y sincrónico,
  incluido el caso del fichero que no vale; **el salto de «Mis criaturas» a la calculadora**
  (que un clic deje elegida esa criatura con su nivel, su ADN y su objetivo guardados, que la
  página pida volver arriba **y quede arriba de verdad**, y que la × borre sin navegar); el
  **ingrediente compartido** (que su ADN se sume por ramas y tu reserva se descuente una sola
  vez); **el nivel objetivo por criatura** (que no se herede al cambiar de dino, que se vea en
  las dos vistas, que el árbol no se quede con el viejo, que teclear en el árbol no lo borre y
  que sobreviva a recargar); y el **interruptor de «subir los ingredientes»**, que es la única
  comprobación del proyecto que no es un espejo del código. Desde el 25-sep cubre además el
  **criar desde el informe**: que ninguna fila lleve «sin crear» detrás del nombre, que la píldora
  siga en la pestaña del árbol, que una criatura sin crear lleve el botón `criar` y una creada no,
  que el atajo «Criar a todas» esté en Total × Nivel, que pulsar `criar` la deje **en el nivel que
  exige la fusión**, y que el atajo deje igual **la raíz** y **las que ya están en ese nivel o por
  encima**, mientras **sube las creadas que se quedaron cortas** y **crea las que faltan** en ese
  mismo nivel; que el botón desaparezca cuando no queda nada por hacer y que el nivel quede
  **guardado** en el inventario. **136 comprobaciones.** El escenario monta los cuatro casos a la
  vez y **se comprueba a sí mismo antes de pulsar** (ver la trampa 20). Todas las celdas de
  las tablas se localizan **por el nombre de su columna**, no por su posición: ver la trampa 16.
- `python3 verificar_stats.py` — **los stats del dino no son folclore.** El mismo cierre que
  `verificar_fuentes.py` hizo para las zonas, pero para los números que enseña el panel. Vuelve
  a leer las 518 fichas de `cache/` y comprueba: los **3.108 números** (518 × 6) contra el campo
  `health/damage/speed/armor/crit/critm` **y** contra el **texto renderizado** de la ficha —dos
  copias independientes dentro del mismo fichero—; que el nivel declarado por la fuente sea 26
  en las 518; los **735 pasos** de las mejoras contra las dos copias del caché; que el orden de
  los pasos sea el de `MEJORA_ORDEN` por rareza y que los dos órdenes sean **distintos**; que
  `MULT_NIVEL` tenga 35 entradas, sea estrictamente creciente y valga 1e9 exacto en el 26; que
  la forma cerrada **coincida** hasta el nivel 30 y **no** coincida del 31 al 35; y los dominios
  que la interfaz da por hechos (5 tipos de premio, 4 recursos, y un icono en disco para cada
  uno, cotejado con el mapa que declara la plantilla). **35 comprobaciones.** Se comprobó que
  **falla de verdad**, de cuatro formas: desincronizando un stat del JSON (2 fallos), dándole a
  la Única el orden del Apex (1), poniendo los cinco últimos niveles como `1,05^(L-26)` (3) y
  pidiendo en la plantilla un icono que no existe (1).
- `python3 probar_rareza.py` — los colores de rareza, en dos pasos. Primero monta una muestra
  con el CSS **extraído del entregable** (no copiado) y comprueba el color **calculado** por el
  navegador de cada etiqueta contra el declarado en `--r-*`: leer el fichero solo demuestra que
  el texto está escrito, leer `getComputedStyle` demuestra que el navegador lo aplica. Después
  **audita la herramienta real**: recorre todos los elementos y lista cuáles llevan alguno de
  los siete colores, agrupados por selector, para que no se quede ninguno con la paleta vieja.
  **Falla si aparece un selector nuevo que use un color de rareza sin declararlo** — así el
  choque no puede crecer escondido detrás de un «todo OK». Mide además el **contraste real del
  tinte** de las etiquetas sobre su fondo compuesto y el **marco de las 518 fotos**, que lo trae
  el WebP. Con `--visual` genera la muestra sin el informe encima, para juzgar el tono a ojo.
  **16 comprobaciones en la muestra y 15 en la auditoría.**
- `python3 captura.py` — seis PNG de las vistas (la calculadora, la del informe con el
  criterio de paleo.gg, el tema `yellow`, el árbol, «Mis criaturas» y **el buscador con una
  fila resaltada**), para revisar el aspecto
  a ojo. Limpia `INV`, `MIS` y el tema al empezar: el perfil de Firefox es el mismo entre
  pasadas, así que `localStorage` sobrevive y una captura salía con los puntos de la anterior
  (ponía `+10` donde el guion ponía 5).
  La vista `buscar` va la **última** y **pulsa la flecha de verdad**: pulsar una pestaña cierra
  el desplegable (el manejador de clic de fuera lo cierra), y el resaltado no existe hasta que
  se pulsa ↓, de modo que sin eso la imagen no podría demostrar que el teclado funciona.
- `python3 captura_informe.py [yellow] [--despues]` — el séptimo encuadre, que a `captura.py` le
  falta: **solo el informe del árbol**, que en una captura de página entera se pierde entre el
  buscador y los campos. Dos cosas que hay que respetar y que costaron una captura **en blanco**:
  el informe **no** vive en la pestaña «Árbol» (`#informeArbol` está dentro de `#s-calc`, así que
  `irA("arbol")` esconde justo lo que se quiere mirar), y esconder los hermanos con
  `display:none` no basta si un ancestro lleva la clase `on`/`off` de las pestañas. Se resuelve
  llevando el informe a un body limpio con sus `<style>`.
  El escenario de partida lleva un ingrediente **creado por debajo** del nivel que exige la fusión
  (T-Rex a 11 cuando la fusión pide 15), y `--despues` **pulsa el atajo antes de fotografiar**:
  sin las dos cosas la captura no enseñaría nada nuevo, porque con todo sin crear el número que se
  ve es el mismo antes y después del cambio.
- `python3 equivalencia.py` — la complementaria de `verificar_motor.py`, y por el camino
  opuesto. `verificar_motor.py` **saca** el motor del HTML y lo corre en Node: comprueba las
  funciones puras. Esta deja el motor **dentro de la página** y llama a `costeADN` / `costeMon`
  / `nFus` en el navegador, que es el camino que recorre el usuario; si alguien rompe cómo la
  página *entrega* los datos (no lo que calcula), esta es la que se entera. 12 criaturas ×
  {30, 35} contra la referencia de `modelo.py`. **24 filas.**

Todas devuelven **código de salida 0 solo si pasan**, e imprimen su informe por stdout. Un
informe que solo existe dentro de un PNG hay que leerlo a ojo, y «lo he mirado y estaba
verde» no es una prueba: es una impresión. Peor, si la prueba revienta la captura sale igual
de bonita. El mecanismo está en `informe_browser.py`: la página manda el informe con un
`XMLHttpRequest` **sincrónico** a un servidor local de un solo uso. Sincrónico a propósito,
porque Firefox toma la captura justo después de `load` y se marcha; un `fetch` asincrónico
lanzado en ese instante puede no llegar a salir. (Por el camino se probó `--dump-dom`, que en
Firefox 156 **se cuelga**.)

En el mismo módulo vive **`comprobar_scripts()`**, que las tres pruebas de navegador llaman
**antes de abrir el navegador**: junta todos los bloques `<script>` de la página en un fichero
y los compila juntos con `node --check`. Es lo que caza una colisión de nombres en el ámbito
global entre la aplicación y el diagnóstico, que validando los bloques por separado no se ve
—y que en el navegador deja el diagnóstico **sin compilar y sin ejecutar, en silencio**. Ver
la trampa 21.

Los verificadores son la garantía de que el archivo que abres se comporta igual que el
modelo que validé: si alguien edita el HTML a mano y rompe el motor, `verificar_motor.py`
lo detecta antes de que lo notes tú.

### Cuatro trampas que costaron tiempo, por si hay que tocar esto

1. **`node --check` hay que pasarlo DESPUÉS de cada edición.** Una vez se editó el HTML
   después de pasarlo, y el error de sintaxis no apareció hasta abrir la página. Por eso
   ahora el chequeo está *dentro* de `verificar_motor.py`: es imposible que se quede atrás.
2. **Un elemento dentro de una sección `display:none` no puede recibir el foco.** Probar
   el árbol sin activar antes su pestaña hace que `.focus()` falle en silencio y que
   cualquier prueba de foco dé un falso fallo. Hay que pulsar la pestaña primero. (Y si un
   apartado de la prueba cambia de pestaña, el siguiente tiene que **volver** a activarla.)
3. **`loading="lazy"` retrasa las imágenes** hasta que entran en pantalla, y en un
   contenedor oculto ni se piden. Comprobar `naturalWidth` justo después de pintarlas da 0
   siempre. En la prueba se clonan como `<img>` ansiosos y ocultos, que sí bloquean el
   evento `load`.
4. **Los campos del árbol son `type="text"`, no `type="number"`, y es a propósito.** En
   Firefox, un `<input type="number">` **no deja leer ni fijar el cursor**:
   `setSelectionRange` lanza `InvalidStateError` y `selectionStart` es `null`. Como el árbol
   se repinta entero en cada tecla, el cursor caía al principio y **teclear «1500» guardaba
   51**. Con `type="text"` el cursor se lee y se devuelve, y `inputmode="numeric"` mantiene el
   teclado numérico en el móvil. Lo que el `number` filtraba solo (letras, signos) lo quita
   `limpiarNumero()`, recolocando el cursor por lo que haya quitado **por delante** de él. Lo
   que se pierde: las flechitas de subir/bajar del campo, que aquí no servían para nada
   (¿subir 30.000 de ADN de uno en uno?). Y **no se puede volver a `type="number"`** sin
   romper el tecleo: lo vigila `probar_ui.py`, que teclea dígito a dígito y comprueba la
   posición del cursor en cada paso.

### Veintiuna formas de escribir una prueba que no prueba nada

Todas dieron **verde**, y todas eran mentira.

1. **Una aserción floja sobre el texto de toda una pestaña.** La primera versión
   comprobaba `ok("la tabla cita el tramo 31-35", /31/.test(txt("s-ref")) && /35/.test(...))`.
   Eso lo cumple hasta una tabla vacía: los números 31 y 35 están en cualquier parte de la
   pestaña. Se arregló comparando **celda por celda contra el modelo** (210/210), que es la
   única forma de que la tabla que lee el usuario sume lo mismo que calcula el motor. Cuando
   esa pestaña se quitó (25-sep-2026) la comprobación **se reescribió**, no se borró: ahora
   contrasta las cifras del modelo contra los valores documentados, que es la mitad que
   seguía teniendo sentido sin tabla.
2. **Replicar la lógica del botón en vez de pulsarlo.** La primera versión hacía
   `INV = {}` y `Object.assign(...)` para «probar» borrar e importar: probaba mi copia de la
   lógica, no el botón. Se arregló pulsando `#btnExport`, `#btnBorrar` e `#btnImport` de
   verdad, interceptando `URL.createObjectURL` para quedarse con el fichero que se habría
   guardado, y sustituyendo solo la API del navegador (`FileReader`) por un doble
   **sincrónico** — necesario además porque Firefox hace la captura justo tras `load`, así
   que un informe pintado después de un `await` saldría en blanco.
3. **Un espejo que comparte el malentendido del original.** `verificar_arbol.py` compara el
   HTML contra un espejo Python, y los dos estaban de acuerdo en **15 de 15 totales**… siendo
   falsos. Los dos sumaban la escalera de todas las criaturas ignorando el interruptor de
   «subir los ingredientes», porque el espejo se escribió desde la misma lectura del problema
   que el original. **Cuando la prueba y el código se escriben desde la misma lectura, un
   malentendido común pasa en verde.** Un espejo demuestra que las dos implementaciones no se
   han separado; **no** demuestra que sean correctas, y su salida ahora lo dice en voz alta.
   Lo que sí lo demuestra es el apartado 12 de `probar_estres.py`, que es el enunciado de lo
   que espera quien usa la página («apagar la casilla tiene que cambiar la cifra») y no una
   copia de cómo está implementado.
4. **Media foto del estado A y media del estado B.** El apartado 12 leía las filas del
   informe como datos y la fila Total del DOM en vivo, y entre las dos lecturas volvía a
   encender la casilla. Resultado: comparaba la suma de las filas sin la casilla (293.500)
   contra el Total con la casilla (312.650) y acusaba a la página de un fallo que era de la
   prueba. Ahora las dos cosas se capturan en el mismo instante, en la misma función.
5. **Extraer un bloque de CSS y pegarlo sin su selector.** Para montar la muestra de colores
   se sacaba `:root{…}` con una expresión regular y se pegaba el grupo capturado —que son
   **solo las declaraciones**— en la hoja. Sin el `:root{`, las variables quedan sin dueño,
   `var(--panel)` no resuelve y la página sale **en blanco**. Se vio porque la muestra salió
   blanca, pero la comprobación que lo habría cazado sola es leer el color **calculado**
   (`getComputedStyle`) en vez del declarado, que es lo que hace ahora `probar_rareza.py`.
   Regla: al extraer un fragmento, comprobar que sigue siendo válido en su contexto.
6. **Escribir el valor entero de golpe en vez de teclearlo.** La prueba hacía
   `el.value = "1500"; dispatchEvent(new Event("input"))`, y así el campo **nunca pasa por un
   estado intermedio**. Por eso el fallo del cursor estuvo ahí sin que ninguna prueba lo
   viera: teclear de verdad, dígito a dígito, guardaba **51** en vez de 1500. Se arregló con
   `teclearTecla()`, que usa `document.execCommand("insertText")` —lo único que inserta **en el
   cursor** y dispara `input` como una tecla de verdad—, y ahora se comprueba el valor **y la
   posición del cursor** en cada paso.
7. **Heredar el estado de la pasada anterior.** El perfil de Firefox conserva `localStorage`
   entre ejecuciones, así que la prueba arrancaba con el inventario de la vez anterior. Peor:
   `probar_estres.py` limpiaba `INV` pero no `MIS`, de modo que **el número de fallos cambiaba
   de una pasada a otra** (10, luego 8) — la señal más clara de que una prueba no está
   midiendo lo que crees. Ahora las dos pruebas limpian `INV` y `MIS` antes de empezar.
8. **Calcular la referencia y no compararla nunca.** La peor de todas, porque **no puede
   fallar**. `equivalencia.py` hacía lo más difícil —la referencia en Python, criatura por
   criatura, y la misma cuenta dentro del navegador— y luego volcaba la salida del navegador
   a un `<pre>`, la capturaba en un PNG, imprimía los valores esperados por stdout y **ahí lo
   dejaba**. Sin `if`, sin `raise`, sin código de salida. Pasara lo que pasara, terminaba en 0.
   Y como su informe salía por pantalla con las cifras bien, parecía que comprobaba algo.
   Arreglado con el mismo mecanismo que las demás: el navegador entrega su salida por el XHR
   síncrono, Python compara fila a fila y **sale con 1 si algo discrepa, 2 si el navegador no
   entregó nada**. Comprobado por sabotaje: cambiando `monedasFusion.apex` de 2000 a 2500 en
   el entregable, la prueba acusa las 4 filas afectadas y devuelve 1.
   **Lección:** una prueba hay que verla fallar al menos una vez. Si nunca la has visto en
   rojo, no sabes si mira algo. Sabotear el dato y comprobar que se entera cuesta un minuto.
9. **Medir dentro del propio evento `load`.** Para comprobar que las fotos de la tira cargaban
   se pintaba la tira **dentro** del `load` y se leía `naturalWidth` en el acto. Daba `0x0`
   con `loading="lazy"` **y también con `eager`**: no distinguía nada, y por eso la primera
   medición no encontró el fallo (que era real: con `lazy` no cargaban nunca). Un `<img>`
   insertado después del `load` todavía no ha cargado. Hay que **sembrar el estado antes del
   script principal** —`localStorage` con la lista ya puesta— y medir en el arranque real, que
   es el camino del usuario. Está en la segunda pasada de `probar_ui.py`.
10. **El elemento guardado antes de un repintado queda muerto.** `refrescar()` rehace el panel
    de la calculadora con `innerHTML`, así que un `const boton = document.getElementById(...)`
    cogido antes del repintado apunta a un nodo que ya no está en el documento. Su `.click()`
    **no hace nada, no lanza error y no avisa**. Se descubrió porque la captura de «Mis
    criaturas» salía con **una** fila en vez de dos y el PNG pesaba exactamente lo mismo que
    antes: el segundo guardado nunca se pulsó. Hay que **volver a buscar el elemento cada vez**.
11. **Firefox no crea el directorio del perfil.** `--profile /ruta/nueva` con el directorio
    inexistente muere con `Could not find profile folder`, **no genera la captura y no escribe
    nada en stderr**. El síntoma que ves es «el navegador no entregó el informe», que apunta a
    la prueba y no al perfil. Al copiar la estructura de otra prueba se quedó fuera el
    `os.makedirs(PERFIL)`.
12. **Medir una capa y creer que eran todas.** En una captura del árbol parecía que las fotos
    llevaban el borde de su rareza. Se midió el CSS (`getComputedStyle`) y salió neutro: se
    escribió como «falso». Pero la captura seguía enseñando el marco, porque **el marco viene
    dibujado dentro del WebP de paleo.gg**. El dato que faltaba era el **píxel de la imagen**.
    El error no fue mirar una captura: fue medir **una** de las dos capas y creer que eran
    todas. Ahora `probar_rareza.py` mide las dos y comprueba que cuentan lo mismo.
13. **Una prueba cuyo criterio comparte el malentendido del dato.** La peor variante de la
    primera. Se dejó escrito en este LEEME que «ninguna de las 518 criaturas tiene el santuario
    como única fuente: 0 casos, comprobado», y la comprobación que lo respaldaba era
    `{loc} == {"sanctuary"}`. **Las cuatro criaturas que sí lo tienen traen `[sanctuary, none]`**,
    así que el conjunto nunca era igual y el recuento salía 0. La aserción pasaba en verde
    diciendo justo lo contrario de lo que dicen los datos, y con ella se escribió una frase
    falsa en la documentación. Ahora se **resta `none`** antes de preguntar —porque `none` no es
    una fuente, es «no sale en el mapa»— y los cinco recuentos se afirman uno a uno. Regla:
    cuando una prueba confirma una afirmación que ya das por buena, **reescribe la pregunta en
    términos de lo que el dato significa**, no de la forma en que lo tienes guardado.
14. **Renombrar una variable no cambia el color que se pinta.** El «+165» de los puntos de
    mejora iba con `--marca`. Al ver que `--marca` vale `#4ade80` en `default` —o sea,
    `--r-unica`— se creó la variable `--marca` para separar «marca» de «alcanza», se argumentó
    que un número verde y una etiqueta verde nunca se confundirían, y se dio el asunto por
    resuelto. **No lo estaba:** el hex seguía siendo el mismo, y lo que ve el usuario es el hex.
    Lo cazó `probar_rareza.py`, que mide `getComputedStyle` y exige que todo elemento con un
    color de rareza esté declarado; y la captura lo confirmó: el nombre `indoraptor` en verde y
    el `+165` en el mismo verde, en la misma pantalla. **El nombre de una variable es una
    afirmación sobre la intención; el valor calculado es el único hecho sobre lo que se ve.**
    Y una nota de método: al arreglarlo apareció **otro** elemento con el mismo defecto
    (`span.st-cq`, la línea del coste) que hasta entonces quedaba tapado por el primero. Una
    auditoría que falla por un sitio suele tener más de uno detrás.
15. **Un número escrito en un comentario también envejece, y nada lo caza.** Aquí decía que la
    forma cerrada `1,05^(L-26)` difería de `MULT_NIVEL` «en hasta 5e-5 relativo, ~0,3 puntos de
    vida». Al medirlo entero para escribir `verificar_stats.py` resultó que del 31 al 35 la
    tabla se separa un **3,68 %**: 314 puntos de vida en una criatura de 6.000, **mil veces**
    lo afirmado. El número estaba en un comentario, con toda la apariencia de un dato medido, y
    **ninguna prueba lo miraba** — una afirmación del proyecto que no es un dato, en el mismo
    sentido que el caso del santuario. Ahora la prueba mide las dos direcciones (coincide hasta
    el 30, no coincide del 31 al 35) y el comentario lleva los números que la prueba sujeta.
    **Regla: si un número importa, tiene que haber una prueba que lo vuelva a calcular; si no,
    es folclore con decimales.**
    **Y la misma trampa, dos veces más ese mismo día, en versiones aún más tontas:**
    - Aquí decía que el icono de la pestaña «a 16 px se sigue leyendo». **No se había renderizado a
      16 px.** Al hacerlo —y al probar seis variantes— resultó que la primera versión se convertía en
      una mancha. **Una afirmación sobre cómo se VE algo exige mirarlo a ese tamaño exacto.**
    - Y aquí decía que el nombre de la herramienta sale «al `<title>`, al `<h1>` y al pie». **No se
      había contado.** Son **dos** sitios: el pie no lo lleva. **Una afirmación sobre cuántos hay
      exige contarlos.** (No se le añadió el nombre al pie para que la frase cuadrara: eso sería
      ajustar el producto a la nota. Se corrigió la frase.)
    - Y aquí decía que el HTML «pesa 139 KB». Se corrigió a una cifra medida, y **esa cifra
      también envejeció**: primero porque el fichero crecía con cada cambio, y luego —peor— porque
      **la medida se había tomado sobre un fichero que no era el entregable** (ver la trampa 19).
      Al anotar los iconos de clase se escribió «60 KB» copiando `du -sh`, que **cuenta bloques de
      8 KB**: son **42.733 bytes**. **`du` miente sobre el tamaño de un fichero** — sirve para saber
      cuánto ocupa en disco. Para bytes: `os.path.getsize` o `stat -c %s`. Es la misma trampa que el
      «5e-5»: un número sin prueba que lo recalcule, y encima leído de la herramienta equivocada.
    Las tres del mismo día —esta, la del icono y la del recuento— **no las cazó ninguna prueba; las
    cazó ir a mirar.** «Se verá bien» y «estará en tres sitios» no son mediciones: son esperanzas.
    Y la cifra del tamaño ya no se escribe a mano sin red: `verificar_motor.py` la **recalcula**.
16. **Leer una celda de una tabla por su POSICIÓN.** Dos comprobaciones de `probar_estres.py`
    preguntaban por `tr.querySelectorAll("td")[5]` y `[6]` queriendo preguntar «el nivel máximo de
    esa fila» y «su objetivo guardado». Cuando la tabla de «Mis criaturas» ganó la columna
    **Mejoras**, los dos índices siguieron apuntando a donde apuntaban y empezaron a leer **otra
    columna**: la del nivel máximo comparaba `4.321` (el ADN) contra `31`, y la del objetivo leía
    la celda de al lado. Estuvieron **rojas** desde entonces. Lo peligroso no es que se pusieran
    rojas —eso se ve—, es que **habrían podido quedarse verdes**: si la columna nueva se hubiera
    insertado detrás, los índices seguirían siendo válidos y la prueba habría pasado midiendo lo
    correcto por casualidad, hasta el día en que alguien insertara otra columna en medio. Un
    índice es una afirmación sobre la **maquetación**; el nombre de la cabecera es una afirmación
    sobre el **significado**. Ahora se localiza la columna por su `<th>` (normalizando tildes y
    espacios) y, si la columna no existe o un `colspan` desplaza la fila, la función devuelve un
    texto que **no es un número** y que se lee en el detalle del fallo: `(no hay columna «X»)`,
    en vez de un número de otra columna. Comprobado por sabotaje en los dos modos: pidiendo una
    columna que no existe, y pidiendo una columna que sí existe pero es la equivocada.
    **Regla: en una prueba, una celda se busca por lo que dice su columna, nunca por el sitio que
    ocupa.** (Y la nota de método que ya vale para toda esta lista: los dos fallos aparecieron
    mezclados con un cambio mío —quitar la columna «Veces»— y **parecían** culpa de ese cambio.
    Antes de tocar nada se midió la línea base: se volvieron a poner la plantilla y la prueba
    **anteriores** al cambio, se recompiló y salieron **los mismos dos fallos**. Sin esa medición
    habría «arreglado» el cambio equivocado.)
    **Y mordió en el cambio siguiente, que es la prueba de que la trampa era real:** al bajar el
    `colspan` de la fila Total de 2 a 1 (para meterle el botón «Criar a todas» en la columna
    «Nivel») esa fila pasó de 5 celdas a 6, y **cuatro aserciones** que la leían por posición
    (`celdasTotal[3]`, `cT[1]`, `cT[3]`, `nCeldasTotal === 5`) empezaron a leer **otra columna**:
    decían «total 300 vs suma 1.202.700» con las dos cifras correctas en pantalla. Documentar una
    trampa no la desactiva: lo único que la desactiva es quitar el índice.
17. **Buscar un SÍMBOLO en vez de una FIRMA.** La prueba del interruptor de ingredientes exigía
    que, con la casilla apagada, ninguna fila del informe enseñara un rango de niveles, y lo
    comprobaba con `/→/.test(...)`. Desde que existe el botón `criar`, la flecha se usa para
    **dos cosas**: el rango (`16 → 20`) y la acción (`criar → 20`). La prueba empezó a acusar a la
    página de enseñar un rango donde lo que había era un botón. Lo importante: **el arreglo no
    fue quitar la comprobación**, fue cambiar el patrón por la firma completa del rango —un
    número, la flecha y otro número— que es **más preciso que antes**: `/→/` daba por rango
    cualquier cosa con una flecha. Cuando una prueba falla por un cambio legítimo, la pregunta no
    es «¿cómo la callo?» sino «¿qué quería decir exactamente, y lo dice?».
18. **Una prueba cuyo CONTROL no puede fallar.** La prueba de «Criar a todas» comparaba el nivel
    de las criaturas ya creadas antes y después. La primera versión tenía dos defectos que la
    dejaban pasando en verde hiciera lo que hiciera el código: (a) al llegar a esa altura solo
    quedaba **una** criatura pendiente, así que estaba probando el singular disfrazado de plural;
    y (b) la criatura de control estaba en **21**, que es justo el nivel de nacimiento de su
    rareza, de modo que un «Criar a todas» que **reiniciara también las creadas** no habría
    cambiado el número y la prueba no lo habría visto. Se arregló haciendo el control
    **degenerado a propósito**: la raíz se pone a **25** (su mínimo es 21) y se dejan los tres
    ingredientes sin crear, con una aserción previa que **exige** que se cumplan las dos
    condiciones —varias pendientes y un control fuera de su mínimo— antes de dar por buena la
    comprobación. Sabotaje para verlo: añadiendo al manejador un bucle que reinicia el nivel de
    todas las criaturas, la prueba caza `indoraptor: 25 → 21`. **Un control que ya está en el
    valor que el error produciría no controla nada.**
19. **El fichero que mides no es el que entregas.** La comprobación del tamaño del LEEME
    comparaba el número escrito contra `os.path.getsize` del HTML, y seguía dando verde. Al
    reconstruir salió **otra** cifra, con el mismo `plantilla.html` y un `build.py`
    determinista (dos builds, el mismo md5). La causa no era el cálculo: el HTML en disco
    llevaba **133 atributos `data-page-node-id` inyectados por un editor** —5.719 bytes de
    más—, y **la cifra del LEEME se había medido sobre ese fichero contaminado**. Se demostró
    que el producto era el mismo quitándolos: **byte a byte idéntico** al build limpio, y las
    capturas salieron con el mismo número de bytes (esos atributos no se renderizan). Lo que
    se sabe y lo que no, medido:
    - **No lo hace ningún script del proyecto.** Están listados *todos* los destinos de
      escritura de los quince scripts: ninguno apunta al entregable. Y la batería completa,
      corrida dos veces seguidas, **no lo reproduce** — apareció una vez y no otras dos.
      O sea: es **externo e intermitente**, y no se ha identificado el proceso. El síntoma es
      el atributo, que es la firma de un editor de HTML con seguimiento de nodos.
      (Ampliado el 25-sep, con más mediciones: los nueve scripts se probaron **uno a uno**
      comprobando el `md5` después de cada uno —`modelo`, `equivalencia`, los cinco
      `verificar_*`, `probar_ui`, `probar_estres`, `probar_rareza`, `captura`— y **ninguno lo
      toca**. Tampoco cambia solo: dejando el fichero quieto **90 s** no se movió. Y cuando
      aparece, **pesa siempre exactamente lo mismo** (267.879 bytes con 134 atributos), o sea
      que el proceso es determinista y no acumula. Sigue sin identificarse.)
    - **Comparar el tamaño no caza esto**, porque el contaminado simplemente pesa más y el
      número «cuadra» con lo que diga el LEEME. Hay que comparar el **contenido**.
    - **Un dato medido sobre el artefacto equivocado es un dato falso aunque la medición sea
      correcta.** El error no fue medir mal: fue medir otra cosa.
    Ahora `verificar_motor.py` **reconstruye el HTML a un temporal y exige que el fichero en
    disco sea exactamente eso**, y cuando falla **dice cuántos atributos de editor lleva**. De
    paso caza la misma familia de fallo por otro camino: editar la plantilla y olvidar
    reconstruir. La rutina cuando salta es: `python3 build.py` y volver a pasar la prueba.
    Y una nota de método: **el arnés de sabotaje también necesita una aserción.** Un sabotaje
    que «pasó» resultó no haber cambiado el texto —llevaba un espacio donde el fichero tiene un
    salto de línea—, o sea que estaba probando el fichero intacto. Ahora el arnés aborta si el
    reemplazo no modifica nada. **Una prueba vacía también es una prueba que no prueba nada.**
    Y otra del mismo día, sobre patrones: **un `re.search` sin ancla no comprueba que el dato
    esté DECLARADO, comprueba que hay alguna línea con esa forma.** El LEEME tenía dos —la
    declaración y la narración de esta misma trampa, citando el valor viejo—; medido, el patrón
    sin ancla **pasaba** con la declaración duplicada y contradictoria, y también con la
    declaración reescrita o ausente. Ahora se ancla a la frase y se exige que aparezca **una
    sola vez**.

20. **Una aserción protegida por dos cosas a la vez: parece muerta y no lo está.** La prueba
    del atajo exige que **no baje** una criatura que ya estaba por encima del nivel exigido
    (Indominus Rex a 30, cuando solo se le piden 20). Al sabotear el código, esa aserción no
    fallaba nunca — y eso es la señal de alarma de la trampa 18. Pero antes de darla por muerta
    había que averiguar **quién la estaba protegiendo**, y eran dos cosas independientes:
    (a) el filtro deja fuera lo que ya está en el nivel o por encima, y (b) el objetivo de un
    nodo **nunca baja de donde ya está** (`objetivoIng = max(nivelIng, nivelActual)`), así que
    su objetivo es 30, no 20, y ponerla «en su objetivo» no la mueve. Con un sabotaje que rompe
    **las dos** —filtro abierto y el nivel tomado del mínimo-como-ingrediente de la propia
    criatura— la aserción **sí** falla: `indominus_rex: 30 → 0`. Lección: cuando un sabotaje no
    hace fallar una comprobación, no se borra ni se deja «por si acaso»: se busca qué invariante
    la está tapando y **se comprueba ese invariante por separado** (aquí, que el nivel exigido
    nunca baje del nacimiento: `verificar_fuentes.py`, margen mínimo **+4** en 496 pares).
    **Y el mismo sabotaje destapó un efecto destructivo que no se veía:** `fijar(u, "nivel", n)`
    marca la criatura como **no creada** si `n` queda por debajo de su nivel de nacimiento —para
    no guardar un nivel imposible—, de modo que un objetivo demasiado bajo no la deja «en un
    nivel raro»: la **borra** (`creado: false, nivel: 0`). Por eso el suelo `max(objetivo,
    minLv)` de `nivelFusion` no es defensa de más: es lo único que separa «subir al nivel de la
    fusión» de «descrear la criatura». **Una API que ante un valor inválido destruye el dato en
    vez de rechazarlo obliga a que todos sus llamantes lleven el suelo.**

Y un detalle que hizo fallar dos aserciones correctas: **`innerText` devuelve el texto ya
transformado por CSS.** El planificador de catalizadores escribe «Sobran» / «Faltan», pero
`.cifra .k` lleva `text-transform:uppercase`, así que `innerText` da «SOBRAN» / «FALTAN» y
las regex en minúsculas fallan. Hay que comparar sin distinguir mayúsculas.

Otro, del mismo tipo: **`indexOf` sobre un array de rótulos exige coincidencia exacta.** Al
pasar la cifra del informe de «ADN que falta» a «ADN que falta en total», la búsqueda devolvió
`-1` y la aserción falló diciendo «cifra undefined». El fallo estaba en la prueba. Ahora se
busca con `indiceEtiqueta(id, /^ADN que falta/i)`.

21. **Los bloques `<script>` de una página comparten el ámbito global, y una colisión de
    nombres mata el script ENTERO en silencio.** Al mover el buscador añadí `let res = []` a la
    aplicación. El diagnóstico de `probar_estres.py` declara `var res = txt("resultado")`, así
    que el script del diagnóstico dejó de **compilar**: no se ejecutó ni una línea suya, y el
    único síntoma fue «el navegador no entregó el informe», que no dice ni qué pasó ni dónde.
    Tres cosas que conviene separar:
    - **`node --check` no lo ve**, porque valida cada bloque por separado. Y `verificar_motor.py`
      hacía exactamente eso: los comprobaba uno a uno, y todos pasaban. La colisión solo existe
      **al juntarlos**, que es lo que hace el navegador.
    - **No hay aviso de error.** Ni `window.onerror` ni el cazador de errores del arnés
      recogieron nada: el script simplemente no existe. Un `SyntaxError` de compilación en un
      `<script>` posterior no pasó por `window.__errores`.
    - **El arnés sí falló, y por eso se cazó:** `veredicto()` devuelve 2 («no juzgable») cuando
      no llega informe, en vez de dar verde. Un fallo mudo, pero no un falso verde.
    Arreglo en dos partes. **Renombrar** `res` a `resBusqueda` (y la regla de fondo: en una
    aplicación que comparte ámbito con scripts ajenos, **un nombre genérico como `res`, `q` o
    `data` es una mina**), y **`comprobar_scripts()` en `informe_browser.py`**, que junta todos
    los bloques en un fichero y los compila juntos **antes de abrir el navegador**. Ahora la
    misma colisión sale así, con nombre y línea, en milisegundos:

    ```
    probar_estres.py: los bloques de script NO compilan juntos -> Identifier 'res' has
    already been declared (linea 1944 del conjunto). Suele ser una colision de nombres en el
    ambito global entre la aplicacion y el diagnostico; renombra el de la aplicacion con un
    nombre especifico.
    ```

    Y una nota de método que vale para cualquier diagnóstico inyectado: **una prueba que no
    entrega su informe no es una prueba que pasa; es una prueba que no corrió.** La diferencia
    entre «verde» y «no juzgable» tiene que estar en el código de salida, no en la esperanza.

---

Herramienta no oficial. Sin relación con Ludia ni con paleo.gg.
Datos de criaturas e imágenes: paleo.gg, actualizados el 23-sep-2026.
Las imágenes son arte del juego, usadas aquí solo para identificar criaturas.
