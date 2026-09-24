# Third-party software

Morale source code is licensed under the MIT License. It uses these separately
licensed projects:

- **Qt for Python / PySide6 and Shiboken6** — The Qt Company and contributors.
  Available under LGPLv3/GPLv3/commercial terms, depending on components.
  https://doc.qt.io/qtforpython-6/licenses.html
- **Qt** — The Qt Company and contributors. Qt modules have their own licensing
  terms. Morale uses Qt Core, Gui, Widgets, and Svg via dynamically loaded libraries.
  https://www.qt.io/licensing/open-source-lgpl-obligations
- **pyembroidery** — EmbroidePy contributors, MIT License.
  https://github.com/EmbroidePy/pyembroidery
- **svgelements** — meerk40t contributors, MIT License.
  https://github.com/meerk40t/svgelements
- **VTracer 1.0.0-alpha.4** — TSANG, Hao Fung and contributors, MIT License.
  https://github.com/visioncortex/vtracer
- **Python** — Python Software Foundation License.
  https://docs.python.org/3/license.html
- **PyInstaller** (build tool and bundled bootloader) — GPL with an exception
  allowing bundled applications to use their own licenses.
  https://pyinstaller.org/en/stable/license.html

Before distributing binaries, include the applicable dependency license texts,
copyright notices, and the corresponding-source/relinking provisions required by
the versions bundled. This file is an inventory, not a substitute for those texts.
The current packaging workflow produces development artifacts, not release-ready
installers; a dependency-license collection step remains part of release work.

## svgelements license

MIT License

Copyright (c) 2019 meerk40t

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## VTracer license

MIT License

Copyright (c) 2024 TSANG, Hao Fung

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Oklab reference equations

The Oklab implementation follows Björn Ottosson’s reference conversion, offered
in the public domain (also available under MIT terms):
https://bottosson.github.io/posts/oklab/

The sRGB transfer function is described at:
https://bottosson.github.io/posts/colorwrong/

## pyembroidery license

The PEC command encoder in `morale/writer_text.py` is adapted from
pyembroidery 1.5.1. The following license text is reproduced from that installed
distribution.

MIT License

Copyright (c) 2018

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
