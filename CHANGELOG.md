# Changelog

[Русский](CHANGELOG.ru.md) · [Español](CHANGELOG.es.md)

Every version and what appeared in it. The same lists are shown inside the app
after an update.


## 1.4.1 — 2026-08-05

- An opened hidden block now stays marked: a thin frame remains in its place, so you can see it was hidden text and that tapping it closes it again. Before, an opened answer looked exactly like ordinary text while still being clickable
- Fixed a bug in how the program wrote its own version: the About screen had been showing 1.0.2 for four releases while everything else was already at 1.4. The line lives in the translations and nothing rebuilt it at release time. Corrected, and the packaging check now watches it so it cannot drift again


## 1.4 — 2026-08-03

- The board no longer loses a file: writing is atomic, a damaged file is set aside instead of being overwritten, and closing asks instead of saving silently. Plus autosave once a minute
- Shapes finally have handles: corners resize, a separate handle rotates. Shift keeps a square square, Alt snaps to the dots of the sheet
- Select several with a rubber band and move, lock or delete them together; Ctrl+L locks so nothing shifts while you draw beside it
- Search across the board (Ctrl+F) and Save as image — the image now contains the cards and notes, not just the drawing
- Fixed nineteen faults, among them: the wheel died over a card, an item kept following the mouse after release, and moving or resizing could not be undone at all


## 1.3 — 2026-08-03

- Formula cards: pick from a catalogue of 58, fill the fields, press Solve — a note slides out with the worked steps, in pure mathematics (Ctrl+G)
- Fill in what the formula cannot take and the button goes dark, with the broken condition lit underneath as maths
- «Show formula» on a solution reopens the formula it came from
- New look: everything you press now has height, and a completed mark sinks in instead of just changing colour
- The icon is redrawn and no longer blurs on large screens
- Colour can be chosen on the card and on the note itself


## 1.2 — 2026-08-02

- Cut a piece of your notes onto the board: pick a file, select with the cursor, choose a colour — it lands as a note (Ctrl+T)
- The note keeps the original markdown, formulas and all; edit it freely, the file is never touched
- «Show source» on a note reopens the file it came from
- Sync is being tested and is switched off for now


## 1.1 — 2026-08-02

- Board: an endless dotted sheet in a window of its own — pen, highlighter, shapes, labels, Ctrl+D. Only on the desktop
- How to write it: pick a fraction, an integral, a matrix, fill the boxes and copy the LaTeX — 115 entries in 18 sections, Ctrl+M
- The catalogue is searched in English, Russian and Spanish at once, by name and by keywords
- The board and the writing helper were missing from the Arch and Flatpak packages — fixed


## 1.0.2 — 2026-07-31

- Edit files right in the app: plain text with colours, live checking, insert buttons and slash commands
- Broken formulas are underlined while you type — the counter at the bottom jumps to the first one
- Create a new file without leaving the app
- Feedback link in the settings


## 1.0.1 — 2026-07-31

- Desktop application id changed to io.github.volkinstridov.MathMark, the form Flathub requires
- The Android package id and the terminal query are unchanged


## 1.0 — 2026-07-31

- First release: reading .md files with formulas rendered by KaTeX, offline
- Problems and topics with three states each; marking changes exactly one byte
- Folders, table of contents, four icons picked by what is inside a file
- Desktop build: two panes, search across files, printing, folder watching
- English, Русский, Español

