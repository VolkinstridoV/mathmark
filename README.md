<div align="center">

<img src="shots/icon.png" width="96" alt="MathMark">

# MathMark

**A reader for maths written in Markdown — for the phone and the desktop.**

Formulas look the way they look in textbooks.
Marking a task changes exactly one byte in your file.

[Русский](README.ru.md) · [Español](README.es.md)

[What changed in every version](CHANGELOG.md)

<img src="shots/phone-01-list.png" width="230"> <img src="shots/phone-02-doc.png" width="230"> <img src="shots/phone-03-doc-light.png" width="230">

<img src="shots/20-desktop-doc.png" width="750">

</div>

---

> **Obsidian is a knowledge base that also renders formulas. This is a tracker for
> going through maths, living inside your own files.** If a knowledge base is what
> you need — take Obsidian, it is good at that.

## Why

Maths is comfortable to *write* as plain text — by hand or with a language model. Reading it back is where it falls apart.

Plain Markdown readers show `\int_0^1 \frac{dx}{x}` as a row of backslashes. Note systems like Obsidian or Joplin do render formulas, but they want to own your notes: a vault, a database, an account. A PDF built from LaTeX is typeset for a sheet of A4 — on a phone you pinch and drag it forever.

MathMark does two things and refuses to do more: **show the maths properly, and let you mark what you have done.**

## Download

| | |
|---|---|
| **Android** | [Releases](../../releases) → the `.apk` file |
| **Arch Linux** | `yay -S mathmark` — [AUR](https://aur.archlinux.org/packages/mathmark) |
| **Any Linux** | [Releases](../../releases) → the `.flatpak` file, just the one, installs with `flatpak install ./mathmark-*.flatpak` |
| **From source** | see [Desktop](#desktop) below |

No account, no network, no telemetry. The formula engine ships inside the app.

## How a file looks

Ordinary Markdown. Formulas in LaTeX between dollar signs.

```markdown
# Calculus — derivatives

## Topics

- ( ) Difference quotient
- (x) Table of derivatives
- (~) Chain rule

$$f'(x) = \lim_{\Delta x \to 0} \frac{f(x + \Delta x) - f(x)}{\Delta x}$$

## Problems

- [x] Differentiate $f(x)=\sqrt{x^3}$
- [ ] Prove $\dfrac{\partial}{\partial x}(x^{\top}Ax) = 2Ax$

The answer can be hidden: ||$f'(x) = \tfrac{3}{2}\sqrt{x}$|| — tap to reveal.
```

**The brackets carry meaning.**
`[ ]` is a **problem** — you do it once, and a finished one gets struck through.
`( )` is a **topic** — you study it, and a finished topic is *not* struck through, it only dims. Knowledge does not get crossed out.

Both have **three states**: `[ ]` untouched, `[~]` in progress, `[x]` done. Tapping the mark cycles them.

You never declare what a file is. The app counts the lines and picks the icon itself: problem list, topic list, both, or a reference sheet.

## What it does

<div align="center">
<img src="shots/phone-04-hidden.png" width="195"> <img src="shots/phone-05-search.png" width="195"> <img src="shots/phone-11-editor.png" width="195"> <img src="shots/phone-09-stats.png" width="195"> <img src="shots/phone-07-sheet.png" width="195">
</div>

- **Formulas, properly.** Fractions, roots of any degree, multiple and contour integrals, sums and products with limits, matrices and determinants, systems, aligned derivations, Greek letters, set and logic symbols, tensor indices, continued fractions, braces under a group of terms. Rendered by [KaTeX](https://katex.org) in Computer Modern — the typeface your textbooks are set in.
- **Hidden text.** Wrap anything in `||double bars||` and it becomes a plate you tap to reveal. Answers, hints, definitions — whatever you want to recall before you peek.
- **Editing inside the app.** A pencil button turns the page into plain text with colours: headings, marks, formulas, hidden parts and drawings each get their own. Broken formulas are underlined **while you type** — the check asks the formula engine itself, so it is exact. Insert buttons and slash commands (`/int`, `/matrix`, `/sigma` — forty of them) put in LaTeX you cannot type on a keyboard. What you typed is saved byte for byte; nothing is reformatted.
- **Search across every file**, by name and by content, showing the line that matched.
- **Table of contents** built from `##` headings — how you navigate a long cheat sheet.
- **Progress.** What you closed today, this week, this month, how many days in a row, and a thirty-day chart. Counted from a journal of marks, so it records *when you solved it*, not when you happened to sync.
- **Reminders** attached to a file, never written into it. Your own wording, daily / weekly / once. Tapping the notification opens that file.
- **Sync through GitHub**, one button. Marks made on two devices merge, and the more advanced state wins. A genuine text conflict is never resolved behind your back: your version stays, theirs is saved beside it.
- **Diagrams** as inline `<svg>`, so a plot travels inside the file itself.
- **A board and a writing helper** — an endless dotted sheet to think on, and a builder that types the LaTeX for you: pick a matrix, fill the boxes, copy. Desktop only, [described below](#the-board).
- **Three interface languages**: English, Русский, Español.

## The rule that shapes everything

The app **never rewrites your file.** Marking finds the byte offset of the character between the brackets and replaces that single byte: space → `~` → `x` → space. Every other byte — indentation, blank lines, letter case, the order of lines — stays untouched, and the file length does not change.

This matters if you also edit those files from a terminal, an editor or an assistant. A program that parsed the file into a model and wrote it back would normalise your formatting and quietly undo work done elsewhere.

The logic lives in `MdItems.kt` and `md_items.py` and is covered by unit tests — including one that asserts exactly one byte differs in the UTF-8 output after a mark.

## Nothing is hidden from the terminal

There is no database. Everything the app knows lives in files you can read and edit:

| What | Where |
|---|---|
| marks | inside your own `.md` files |
| settings | `~/.config/mathmark/mathmark.conf`, plain text |
| the file list | the folder itself — there is no internal registry |
| journal of marks | `journal.log`, append-only text |
| reminders | `reminders.conf`, plain text |

So anything you can do by hand, a script or an assistant working through the terminal can do too — and the other way round. Edit a file from outside and the open document reloads by itself.

The app also hands out its own writing guide on request, so a tool can learn the format without you copying anything:

```bash
content query --uri content://dev.yury.mathmark/prompt
```

On the desktop the same text sits under a button in the settings. It explains the brackets, the three states, hidden text, formulas and diagrams — give it to a language model and the files it writes will render correctly the first time.

## Desktop

<div align="center">
<img src="shots/25-desktop-editor.png" width="370"> <img src="shots/21-desktop-search.png" width="370">

<img src="shots/22-desktop-stats.png" width="370"> <img src="shots/26-desktop-light.png" width="370">
</div>

The desktop build is the same program, and it draws through the very same page as the phone: `shared/reader/` is used by both, so the two cannot drift apart.

What the bigger screen adds: two panes, search across all files, keyboard navigation (`j`/`k` or arrows to move, space to mark), printing and saving a cheat sheet as PDF, and a folder watcher — edit a file in your editor and the window updates on its own. The text column keeps a readable width: widen the window and the margins grow, not the line.

### The board

<div align="center"><img src="shots/27-desktop-board.png" width="750"></div>

A second window (`Ctrl+D`): an endless sheet ruled in dots — the paper you think on, not the page you read. Pen, highlighter, eraser, straight lines, arrows, rectangles, ellipses, triangles. Double-click anywhere and type a label; double-click it again to change it. Copy, paste, duplicate, undo. Pan and zoom, and the dot grid steps its density so the dots neither clot nor drift apart.

A board is saved as plain readable JSON in the same folder as your notes, under a `.board` name. Same rule as everywhere else here: nothing is locked inside the program.

### How to write it

<div align="center"><img src="shots/28-desktop-write.png" width="750"></div>

The one question that stops people is not *what* to write but *how do I type that?* Press `Ctrl+M`: pick a fraction, an integral, a matrix, a system — **115 entries in 18 sections** — and it appears already drawn, with empty boxes where your numbers go. Fill the boxes, press Copy, paste it anywhere.

Every entry carries its own settings: a matrix asks for brackets, rows and columns and gives you a grid of fields; a vector asks for its dimension and whether it lies in a row or a column; an integral asks for its limits and variable. Search runs in English, Russian and Spanish at once, over names and keywords alike. A second button copies the LaTeX without the dollar signs, for pasting inside a formula you already have.

Both the board and the helper are desktop-only, on purpose.

On Arch it is one command:

```bash
yay -S mathmark
```

Anywhere else, straight from the source tree:

```bash
./desktop/install.sh     # a launcher in ~/.local/bin, plus icon and menu entry
mathmark
```

Needs `gtk4`, `libadwaita`, `webkitgtk-6.0`, `python-gobject`.

## Building

**Android** — JDK 21 and the Android SDK (platform 37):

```bash
cd android
gradle :app:testDebugUnitTest
gradle :app:assembleRelease
adb install -r app/build/outputs/apk/release/app-release.apk
```

The app reads an ordinary folder in shared storage, so it asks for all-files access once. With root you can grant it silently:

```bash
adb shell 'su -c "appops set io.github.volkinstridov.MathMark MANAGE_EXTERNAL_STORAGE allow"'
```

**Desktop** — `python3 -m pytest desktop/tests`

Both sides carry the same 51 tests: identical rules for parsing, marking, merging, statistics and reminders. If the two implementations ever disagree, the tests fail.

## Layout

```
shared/          used by both builds
  reader/        the reading page, its typography and KaTeX
  prompt/        the writing guide handed to language models
  i18n/          translations, one JSON per language
android/         Kotlin, Jetpack Compose
desktop/         Python, GTK4, libadwaita
```

## Feedback

Something broken, something missing — [open an issue](https://github.com/VolkinstridoV/mathmark/issues).
If it is easier to just write, the author is on Telegram: [@Volkinstridoff](https://t.me/Volkinstridoff).

## License

MIT. Do what you like with it.
