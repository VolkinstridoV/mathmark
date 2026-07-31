<div align="center">

<img src="shots/icon.png" width="96" alt="MathMark">

# MathMark

**A reader for maths written in Markdown — for the phone and the desktop.**

Formulas look the way they look in textbooks.
Marking a task changes exactly one byte in your file.

[Русский](README.ru.md) · [Español](README.es.md)

<img src="shots/phone-01-list.png" width="230"> <img src="shots/phone-02-doc.png" width="230"> <img src="shots/phone-03-doc-light.png" width="230">

<img src="shots/20-desktop-doc.png" width="750">

</div>

---

## Why

Maths is comfortable to *write* as plain text — by hand or with a language model. Reading it back is where it falls apart.

Plain Markdown readers show `\int_0^1 \frac{dx}{x}` as a row of backslashes. Note systems like Obsidian or Joplin do render formulas, but they want to own your notes: a vault, a database, an account. A PDF built from LaTeX is typeset for a sheet of A4 — on a phone you pinch and drag it forever.

MathMark does two things and refuses to do more: **show the maths properly, and let you mark what you have done.**

## Download

| | |
|---|---|
| **Android** | [Releases](../../releases) → `mathmark-1.0.apk` |
| **Linux** | [Releases](../../releases) → `mathmark-1.0.flatpak`, or run from source |

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
<img src="shots/phone-04b-hidden-open.png" width="195"> <img src="shots/phone-05-search.png" width="195"> <img src="shots/phone-09-stats.png" width="195"> <img src="shots/phone-10-reminder.png" width="195">
</div>

- **Formulas, properly.** Fractions, roots of any degree, multiple and contour integrals, sums and products with limits, matrices and determinants, systems, aligned derivations, Greek letters, set and logic symbols, tensor indices, continued fractions, braces under a group of terms. Rendered by [KaTeX](https://katex.org) in Computer Modern — the typeface your textbooks are set in.
- **Hidden text.** Wrap anything in `||double bars||` and it becomes a plate you tap to reveal. Answers, hints, definitions — whatever you want to recall before you peek.
- **Search across every file**, by name and by content, showing the line that matched.
- **Table of contents** built from `##` headings — how you navigate a long cheat sheet.
- **Progress.** What you closed today, this week, this month, how many days in a row, and a thirty-day chart. Counted from a journal of marks, so it records *when you solved it*, not when you happened to sync.
- **Reminders** attached to a file, never written into it. Your own wording, daily / weekly / once. Tapping the notification opens that file.
- **Sync through GitHub**, one button. Marks made on two devices merge, and the more advanced state wins. A genuine text conflict is never resolved behind your back: your version stays, theirs is saved beside it.
- **Diagrams** as inline `<svg>`, so a plot travels inside the file itself.
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
<img src="shots/21-desktop-search.png" width="370"> <img src="shots/22-desktop-stats.png" width="370">
</div>

The desktop build is the same program, and it draws through the very same page as the phone: `shared/reader/` is used by both, so the two cannot drift apart.

What the bigger screen adds: two panes, search across all files, keyboard navigation (`j`/`k` or arrows to move, space to mark), printing and saving a cheat sheet as PDF, and a folder watcher — edit a file in your editor and the window updates on its own. The text column keeps a readable width: widen the window and the margins grow, not the line.

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
adb shell 'su -c "appops set dev.yury.mathmark MANAGE_EXTERNAL_STORAGE allow"'
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

## License

MIT. Do what you like with it.
