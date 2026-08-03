# Cambios

[English](CHANGELOG.md) · [Русский](CHANGELOG.ru.md)

Todas las versiones y lo que apareció en cada una. Las mismas listas se ven
dentro de la aplicación tras actualizar.


## 1.4 — 2026-08-03

- La pizarra ya no pierde el archivo: la escritura es atómica, un archivo dañado se aparta en vez de sobrescribirse y al cerrar se pregunta en lugar de guardar en silencio. Y autoguardado cada minuto
- Las figuras por fin tienen tiradores: las esquinas cambian el tamaño y un tirador aparte las gira. Shift mantiene el cuadrado cuadrado, Alt las ajusta a los puntos de la hoja
- Selección por marco: varios elementos se mueven, se bloquean y se borran a la vez; Ctrl+L pone el candado
- Búsqueda en la pizarra (Ctrl+F) y Guardar como imagen — la imagen ahora incluye las tarjetas y los papeles, no solo el dibujo
- Corregidos diecinueve fallos, entre ellos: la rueda moría sobre una tarjeta, un elemento seguía al ratón tras soltarlo y mover o redimensionar no se podía deshacer


## 1.3 — 2026-08-03

- Tarjetas de fórmulas: eliges una de 58, rellenas las casillas, pulsas Resolver — sale un papel con el desarrollo paso a paso, en matemática pura (Ctrl+G)
- Si rellenas algo que la fórmula no admite, el botón se apaga y debajo se enciende la condición incumplida, también en matemáticas
- «Ver la fórmula» en una solución reabre la fórmula de la que salió
- Nuevo aspecto: todo lo que se pulsa tiene altura, y una marca completada se hunde en vez de solo cambiar de color
- El icono está redibujado y ya no se ve borroso en pantallas grandes
- El color se elige en la propia tarjeta y en el propio papel


## 1.2 — 2026-08-02

- Recortar un trozo de tus apuntes a la pizarra: eliges archivo, seleccionas con el cursor, eliges color — cae como un papel (Ctrl+T)
- El papel guarda el markdown original con sus fórmulas; edítalo cuanto quieras, el archivo no se toca
- «Ver el origen» en el papel reabre el archivo del que salió
- La sincronización está en pruebas y por ahora está desactivada


## 1.1 — 2026-08-02

- Pizarra: una hoja punteada infinita en su propia ventana — pluma, marcador, figuras, rótulos, Ctrl+D. Solo en el escritorio
- «Cómo se escribe»: eliges una fracción, una integral, una matriz, rellenas las casillas y copias el LaTeX — 115 entradas en 18 secciones, Ctrl+M
- El catálogo se busca en inglés, ruso y español a la vez, por nombre y por palabras clave
- La pizarra y el asistente de escritura no llegaban a los paquetes de Arch y Flatpak — corregido


## 1.0.2 — 2026-07-31

- Edición del archivo dentro de la aplicación: texto plano con colores, comprobación al vuelo, botones e instrucciones con barra
- Las fórmulas rotas se subrayan mientras escribes; el contador de abajo lleva a la primera
- Crear un archivo sin salir de la aplicación
- Enlace de contacto en los ajustes


## 1.0.1 — 2026-07-31

- El identificador de escritorio cambió a io.github.volkinstridov.MathMark, la forma que exige Flathub
- El identificador de Android y la consulta desde la terminal no cambian


## 1.0 — 2026-07-31

- Primera versión: lectura de archivos .md con fórmulas dibujadas por KaTeX, sin internet
- Tareas y temas, cada uno con tres estados; marcar cambia exactamente un byte
- Carpetas, índice, cuatro iconos según lo que hay dentro del archivo
- Versión de escritorio: dos paneles, búsqueda, impresión, vigilancia de la carpeta
- English, Русский, Español

