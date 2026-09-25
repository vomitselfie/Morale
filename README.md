<p align="center">
  <img src="Morale_Logo.svg" alt="Morale logo: an M made of four sewing needles" width="120">
</p>

<h1 align="center">Morale</h1>

<p align="center"><strong>A free embroidery design program for your computer.</strong><br>
Draw designs, turn pictures into stitches, add lettering, and save files for your embroidery machine.</p>

<p align="center">
  <a href="https://github.com/vomitselfie/Morale/releases/latest"><strong>Download Morale</strong></a> ·
  <a href="docs/USER_GUIDE.md">User guide</a> ·
  <a href="docs/FEATURES.md">Everything it can do</a>
</p>

![The Morale window showing the wildflower example design, with the list of stitched parts on the left, the design in the middle and its settings on the right](docs/images/main-window.png)

## What Morale does

- **Turns pictures into embroidery.** Open a logo, clip-art or drawing and Morale
  works out the stitches for you. You can review and change everything before sewing.
- **Adds lettering** in any font on your computer, sewn with smooth satin stitches.
- **Lets you draw your own designs** with simple shapes, lines and satin borders.
- **Opens and saves machine files** for Brother, Bernina, Janome, Husqvarna,
  Singer and most other home machines.
- **Shows the design being stitched** on screen before you use any thread.
- **Works without the internet.** There is no account, no subscription and no
  advertising. Your designs stay on your computer.

Morale is new and still growing. It is free to use and share.

## Download and install

Go to the **[download page](https://github.com/vomitselfie/Morale/releases/latest)**
and pick the file for your computer.

### Windows 10 or 11

1. Download the file ending in **`-windows-x86_64-setup.exe`**.
2. Double-click it to install.
3. Windows may show a blue box saying *"Windows protected your PC"*. This appears
   for small free programs that have not paid for a publisher certificate. Click
   **More info**, then **Run anyway**.
4. Morale appears in your Start menu.

### Mac (Apple M1 or newer)

1. Download the file ending in **`-macos-arm64.dmg`** and double-click it.
2. Drag **Morale** into the **Applications** folder.
3. The first time, **right-click** Morale in Applications and choose **Open**, then
   **Open** again. (A normal double-click will say the developer cannot be verified,
   because Morale is not registered with Apple.) After that it opens normally.

### Linux

Download the file ending in **`.AppImage`**. Right-click it, open **Properties**,
allow it to run as a program, then double-click it.

## Your first design in five steps

1. **Open Morale.** A flower example is already on screen to explore.
2. **Choose your hoop** from the menu above the design, for example *100 mm × 100 mm*.
3. **Make a design:** click a shape button at the top and drag in the hoop, use
   **Edit → Add lettering…**, or turn a picture into stitches with
   **File → Digitize artwork…**.
4. **Press ▶ Preview** at the bottom to watch it stitch on screen.
5. **Click Export stitches ↗** (top right), choose your machine's file type, and
   copy the file to your machine as you normally would (usually a USB stick).

Also use **File → Save project** to keep a copy you can change later. Machine files
only hold stitches, so they are hard to edit.

The [user guide](docs/USER_GUIDE.md) explains each step with more detail.

## Which file type does my machine use?

| Your machine | Choose |
| --- | --- |
| Brother, Baby Lock, Deco | **PES** (if an older machine refuses it, choose PES version 1) |
| Bernina | **EXP** |
| Janome, Elna, Kenmore | **JEF** |
| Husqvarna Viking, Pfaff | **VP3**. It has a known problem that can move some jumps, so test first; many of these machines also accept **DST** |
| Singer | **XXX** |
| Commercial and most other machines | **DST** |

Not sure? Check your machine's manual for "embroidery file formats", or try
**DST**, which most machines read. DST files do not store thread colours, so keep
the colour list: **File → Export thread chart…**.

## Good to know

- **Always test on scrap fabric first.** Morale's stitches have not yet been
  tested on many machines. Use the same fabric and stabilizer you plan to use.
- **Your work is protected.** If Morale or your computer closes unexpectedly,
  Morale offers to bring your design back next time. You can also use
  **File → Recover interrupted session…**.
- **Undo** is always there: **Edit → Undo**, or Ctrl+Z (⌘Z on a Mac).
- **Larger text:** Morale follows your computer's text size setting.

## Getting help

- Read the **[user guide](docs/USER_GUIDE.md)**, which also explains common embroidery words.
- See **[everything Morale can do](docs/FEATURES.md)**, with each feature's limits.
- Found a problem or have an idea? Tell us on the
  **[issues page](https://github.com/vomitselfie/Morale/issues)**. A photo of the
  stitched result and your machine's name help a lot.

## For developers

Building from source, running the tests and publishing releases are covered in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Release notes are in
[CHANGELOG.md](CHANGELOG.md).

Morale is free software under the [MIT license](LICENSE). It uses other open-source
projects, listed in [third-party notices](THIRD_PARTY_NOTICES.md).
