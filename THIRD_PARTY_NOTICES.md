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

## Embroidery fonts

The embroidery fonts in `morale/fonts/` are converted from the
[Ink/Stitch embroidery font library](https://github.com/inkstitch/embroidery-fonts)
by `scripts/import_inkstitch_fonts.py`. Each font keeps its own license, which is
included beside it; fonts with non-commercial or no-derivatives licenses are not
included. SIL Open Font License fonts may not be sold on their own. Fonts under
CC BY-SA are adapted (converted to Morale's format) and shared under the same
license, crediting their authors as listed in each LICENSE file.

| Font | License | Based on | License file |
| --- | --- | --- | --- |
| Abécédaire AGS | SCC-BY-SA 4.0 |  cross stitch grid | `morale/fonts/abecedaire/LICENSE` |
|  Abécédaire AGS Small | SCC-BY-SA 4.0 | — | `morale/fonts/abecedaire_small/LICENSE` |
| AGS Γαραμου Garamond | SIL Open Font License v1.1 | EBGaramond12 | `morale/fonts/ags_garamond_latin_grec/LICENSE` |
| Alchemy | SIL Open Font License v1.1 | Ouroboros | `morale/fonts/alchemy/LICENSE` |
| Allegria 20 | SIL Open Font License v1.1 | Euphoria Script Regular Extended | `morale/fonts/allegria20/LICENSE` |
| Allegria 55 | SIL Open Font License v1.1 | Euphoria Script Regular Extended | `morale/fonts/allegria55/LICENSE` |
| Ambigüe | SIL Open Font License v1.1 | Ambidexter | `morale/fonts/ambigue/LICENSE` |
| Amitaclo | SIL Open Font License v1.1 | Amita | `morale/fonts/amitaclo/LICENSE` |
| Amitaclo small | SIL Open Font License v1.1 | Amita | `morale/fonts/amitaclo_small/LICENSE` |
| Animals Alphabet | SIL Open Font License v1.1 | Domine | `morale/fonts/animals/LICENSE` |
| Alphabet des animaux | SIL Open Font License v1.1 | Domine | `morale/fonts/animaux/LICENSE` |
| Apesplit | SIL Open Font License v1.1 | Gilda Display | `morale/fonts/apesplit/LICENSE` |
| Apex Lake | SCC-BY-SA 4.0 | Apex Lake | `morale/fonts/apex_lake/LICENSE` |
| Apex Simple AGS | SIL Open Font License v1.1 | Linux Libertine Regular display Bold | `morale/fonts/apex_simple_AGS/LICENSE` |
| Apex Simple Small AGS | SIL Open Font License v1.1 | Linux Libertine Regular display Bold | `morale/fonts/apex_simple_small_AGS/LICENSE` |
| Art Nouveau | SIL Open Font License v1.1 | Apollo ASM | `morale/fonts/art_nouveau/LICENSE` |
| Auberge Marif | SIL Open Font License v1.1 | Grand Hotel Marif | `morale/fonts/auberge_marif/LICENSE` |
| Auberge Small | SIL Open Font License v1.1 | Grand Hotel Marif | `morale/fonts/auberge_small/LICENSE` |
| Aventurina | SCC-BY-SA 4.0 | Aventurina | `morale/fonts/aventurina/LICENSE` |
| Barstitch Bold | SIL Open Font License v1.1 | Barlow Bold | `morale/fonts/barstitch_bold/LICENSE` |
| Barstitch cloudy | SIL Open Font License v1.1 | Barlow Bold | `morale/fonts/barstitch_cloudy/LICENSE` |
| Barstitch cloudy crosses | SIL Open Font License v1.1 | Barlow Bold | `morale/fonts/barstitch_crosses/LICENSE` |
| Barstitch Mandala | SIL Open Font License v1.1 | Barlow Bold | `morale/fonts/barstitch_mandala/LICENSE` |
| Barstitch regular | SIL Open Font License v1.1 | Barlow Regular | `morale/fonts/barstitch_regular/LICENSE` |
| Barstitch textured | SIL Open Font License v1.1 | Barlow Bold | `morale/fonts/barstitch_textured/LICENSE` |
| Bathaus FI | SIL Open Font License v1.1 | Baumans | `morale/fonts/bathaus_FI/LICENSE` |
| Bathaus FI Small | SIL Open Font License v1.1 | Baumans | `morale/fonts/bathaus_FI_Small/LICENSE` |
| Bluenesia Satin | SCC-BY-SA 4.0 | Bluenesia | `morale/fonts/bluenesia_satin/LICENSE` |
| BrailleCC | SCC-BY-SA 4.0 | — | `morale/fonts/braille/LICENSE` |
| Caesarus SC FI | SIL Open Font License v1.1 | Marcellus SC | `morale/fonts/caesarus_SC_FI/LICENSE` |
| Caffeine KOR | SIL Open Font License v1.1 | Espresso Dolce | `morale/fonts/caffeine_KOR/LICENSE` |
| Caffeine tiny | SIL Open Font License v1.1 | Espresso Dolce | `morale/fonts/caffeine_tiny/LICENSE` |
| Califragilistic | SIL Open Font License v1.1 | Ojuju | `morale/fonts/califragilistic/LICENSE` |
| Cats | SIL Open Font License v1.1 | Cat Font | `morale/fonts/cats/LICENSE` |
| Cherry for inkstitch | SCC-BY-SA 4.0 | Cherry AI 1 | `morale/fonts/cherryforinkstitch/LICENSE` |
| Cherry for Kaalleen | SCC-BY-SA 4.0 | Cherry AI 1 | `morale/fonts/cherryforkaalleen/LICENSE` |
| Chicken Little KOR | SIL Open Font License v1.1 | Henny Penny | `morale/fonts/chicken_little/LICENSE` |
| Chicken Little KOR Small | SIL Open Font License v1.1 | Henny Penny | `morale/fonts/chicken_little_small/LICENSE` |
| Chicken Scratch | SIL Open Font License v1.1 | Reenie Beanie | `morale/fonts/chicken_scratch/LICENSE` |
| Chopin Script | SCC-BY-SA 4.0 | Chopin Script | `morale/fonts/chopin/LICENSE` |
| Circular 3 Letters Monogram | SCC-BY-SA 4.0 | — | `morale/fonts/circular_3letters_monogram/LICENSE` |
| Cogs KOR | SCC-BY-SA 4.0 | Jack of Gears | `morale/fonts/cogs_KOR/LICENSE` |
| Colorful | SIL Open Font License v1.1 | Spicy Rice | `morale/fonts/colorful/LICENSE` |
| CooperMarif | SIL Open Font License v1.1 | Cooper* | `morale/fonts/cooper_marif/LICENSE` |
| Кирилиця | SIL Open Font License v1.1 | Roboto | `morale/fonts/cyrillic/LICENSE` |
| Decadent Flowers Monogram | SIL Open Font License v1.1 | Linux Libertine Bold | `morale/fonts/decadent_flowers_monogram/LICENSE` |
| Dejavu Serif | SCC-BY-SA 4.0 | Dejavu Serif Condensed | `morale/fonts/dejavufont/LICENSE` |
| Digory Doodles Bean | SIL Open Font License v1.1 | Digory Doodles | `morale/fonts/digory_doodles_bean/LICENSE` |
| DinoMouse72 | SCC-BY-SA 4.0 | DinoMouse | `morale/fonts/dinomouse72/LICENSE` |
| Egyptian | SIL Open Font License v1.1 | cairopixel | `morale/fonts/egyptian/LICENSE` |
| Egyptian Small | SIL Open Font License v1.1 | cairopixel | `morale/fonts/egyptian_small/LICENSE` |
| Ελληνικά — Greek satin font | SIL Open Font License 1.1 | Clara Bold | `morale/fonts/ellenika/LICENSE` |
| Eloquent | SIL Open Font License v1.1 | acsf expressive 5pt light | `morale/fonts/eloquent/LICENSE` |
| Eloquent Small | SIL Open Font License v1.1 | acsf expressive 5pt light | `morale/fonts/eloquent_small/LICENSE` |
| Emilio 20 | SCC-BY-SA 4.0 | Emilio 20 | `morale/fonts/emilio_20/LICENSE` |
| EMILIO_20_Applique | SCC-BY-SA 4.0 | Emilio 20 | `morale/fonts/emilio_20_applique/LICENSE` |
| EMILIO_20_Bold | SCC-BY-SA 4.0 | Emilio 20 | `morale/fonts/emilio_20_bold/LICENSE` |
| Emilio 20 Simple | SCC-BY-SA 4.0 | Emilio 20 | `morale/fonts/emilio_20_simple/LICENSE` |
| Emilio 20 Simple Small | SCC-BY-SA 4.0 | Emilio 20 | `morale/fonts/emilio_20_simple_small/LICENSE` |
| EMILIO_20_Tartan | SCC-BY-SA 4.0 | Emilio 20 | `morale/fonts/emilio_20_tartan/LICENSE` |
| EMILIO 20 TRICOLORE | SCC-BY-SA 4.0 | Emilio 20 | `morale/fonts/emilio_20_tricolore/LICENSE` |
| Excalibur KOR | Public Domain | Excalibur Nouveau | `morale/fonts/excalibur_KOR/LICENSE` |
| Excalibur small | Mublic Domain | Excalibur Nouveau | `morale/fonts/excalibur_small/LICENSE` |
| Geneva Simple Sans Rounded | SCC-BY-SA 2.5 | Hershey | `morale/fonts/geneva_rounded/LICENSE` |
| Geneva Simple Sans | SCC-BY-SA 2.5 | Hershey | `morale/fonts/geneva_simple/LICENSE` |
| gingo200 | SCC-BY-SA 4.0 | — | `morale/fonts/gingo200/LICENSE` |
| Glacial Tiny 60 AGS | SIL Open Font License v1.1 | Glacial Indifference | `morale/fonts/glacial_tiny/LICENSE` |
| Heavenly | SIL Open Font License v1.1 | acsf divine 5pt light | `morale/fonts/heavenly/LICENSE` |
| Heavenly Small | SIL Open Font License v1.1 | acsf divine 5pt light | `morale/fonts/heavenly_small/LICENSE` |
| Inclusif(ve) | SIL Open Font License v1.1 | Crozet.te font | `morale/fonts/inclusif_ve/LICENSE` |
| Initials XL | SIL Open Font License v1.1 | Sortefax | `morale/fonts/initials_XL/LICENSE` |
| Initials Medium  | SIL Open Font License v1.1 | Sortefax | `morale/fonts/initials_medium/LICENSE` |
| Ink/Stitch Masego | SIL Open Font License v1.1 | Masego | `morale/fonts/inkstitch_masego/LICENSE` |
| Jacquard 12 | SIL Open Font License v1.1 | Jacquard 12 | `morale/fonts/jacquard_12/LICENSE` |
| Jaquarda Bastarda 9 | SIL Open Font License v1.1 | Jaquarda Bastarda 9 | `morale/fonts/jaquarda_bastarda_9/LICENSE` |
| Jersey 15 | SIL Open Font License v1.1 | Jersey 15 | `morale/fonts/jersey_15/LICENSE` |
| Kum Tsoan AGS | SIL Open Font License v1.1 | Namskout | `morale/fonts/kum_tsoan_AGS/LICENSE` |
| Kum Tsoan Relief | SIL Open Font License v1.1 | Namskout | `morale/fonts/kum_tsoan_relief/LICENSE` |
| Kum Tsoan Tartan | SIL Open Font License v1.1 | Namskout | `morale/fonts/kum_tsoan_tartan/LICENSE` |
| Learning curve | SCC-BY-SA 4.0 | Learning Curve | `morale/fonts/learning_curve/LICENSE` |
| Magnolia KOR | SIL Open Font License v1.1 | Magnolia Script | `morale/fonts/magnolia_KOR/LICENSE` |
| Magnolia bicolor | SIL Open Font License v1.1 | Magnolia Script | `morale/fonts/magnolia_bicolor/LICENSE` |
| Magnolia Small | SIL Open Font License v1.1 | Magnolia Script | `morale/fonts/magnolia_small/LICENSE` |
| Magnolia tamed | SIL Open Font License v1.1 | Magnolia Script | `morale/fonts/magnolia_tamed/LICENSE` |
| Mai En Fleur AGS | SIL Open Font License v1.1 | Abril Fatface | `morale/fonts/mai_en_fleur/LICENSE` |
| MAM Script | SIL Open Font License v1.1 | Kaushan Script | `morale/fonts/mam_script/LICENSE` |
| Marifenda | SIL Open Font License v1.1 | Merienda-Bold | `morale/fonts/marifenda/LICENSE` |
| Ink/Stitch Medium Font | SIL Open Font License v1.1 | — | `morale/fonts/medium_font/LICENSE` |
| Millimarif-bold20 | SIL Open Font License v1.1 | Millimetre | `morale/fonts/milli_marif_bold/LICENSE` |
| Mimosa Large | SIL Open Font License v1.1 | Nose Transport | `morale/fonts/mimosa_large/LICENSE` |
| Mimosa Medium | SIL Open Font License v1.1 | Nose Transport | `morale/fonts/mimosa_medium/LICENSE` |
| Monicha | SCC-BY-SA 4.0 | Monicha | `morale/fonts/monicha/LICENSE` |
| Montecarlo | SIL Open Font License v1.1 | Montecarlo Regular | `morale/fonts/montecarlo/LICENSE` |
| Néon | SIL Open Font License v1.1 | Sportrop | `morale/fonts/neon/LICENSE` |
| Néon blinking | SIL Open Font License v1.1 | Sportrop | `morale/fonts/neon_blinking/LICENSE` |
| NickAinley | SCC-BY-SA 4.0 | Nick Ainley Script | `morale/fonts/nick_ainley/LICENSE` |
| Noble | SIL Open Font License v1.1 | acsf honorable 6pt light | `morale/fonts/noble/LICENSE` |
| Ondulamarif M | SIL Open Font License v1.1 | QumpellkaNo12 | `morale/fonts/ondulamarif_Medium/LICENSE` |
| Ondulamarif S | SIL Open Font License v1.1 | QumpellkaNo12 | `morale/fonts/ondulamarif_S/LICENSE` |
| Ondulamarif XL | SIL Open Font License v1.1 | QumpellkaNo12 | `morale/fonts/ondulamarif_XL/LICENSE` |
| Pacificlo | SIL Open Font License v1.1 | Pacifico | `morale/fonts/pacificlo/LICENSE` |
| Pacificlo tiny | SIL Open Font License v1.1 | Pacifico | `morale/fonts/pacificlo_tiny/LICENSE` |
| Paquerette | Public Domain | Coronaviral | `morale/fonts/paquerette/LICENSE` |
| Perspective tricolore KOR | SIL Open Font License v1.1 | Merriweather4 | `morale/fonts/perspective_tricolore_KOR/LICENSE` |
| Pisankris | SIL Open Font License v1.1 | Manuskript Gothisch | `morale/fonts/pisankris/LICENSE` |
| Pixel 10 | SIL Open Font License v1.1 | Jersey 10 Regular | `morale/fonts/pixel10/LICENSE` |
| Precious | SIL Open Font License v1.1 | Precious | `morale/fonts/precious/LICENSE` |
| Roaring Twenties KOR | SIL Open Font License v1.1 | Limelight | `morale/fonts/roaring_twenties_KOR/LICENSE` |
| Roaring Twenties KOR Small | SIL Open Font License v1.1 | Limelight | `morale/fonts/roaring_twenties_KOR_small/LICENSE` |
| Roman AGS | SIL Open Font License v1.1 | Latin Modern Roman 10 Bold Italic | `morale/fonts/roman_ags/LICENSE` |
| Roman bicolor AGS | SIL Open Font License v1.1 | Latin Modern Roman 10 Bold Italic | `morale/fonts/roman_ags_bicolor/LICENSE` |
| Sacramarif | SIL Open Font License v1.1 | Sacramento | `morale/fonts/sacramarif/LICENSE` |
| Ink/Stitch Small Font | SIL Open Font License v1.1 | — | `morale/fonts/small_font/LICENSE` |
| Stebor AGS | SIL Open Font License v1.1 | Lobster Two Bold Italic | `morale/fonts/stebor_AGS/LICENSE` |
| Sunset | SIL Open Font License v1.1 | Big Shoulders Inline | `morale/fonts/sunset/LICENSE` |
| Tieralphabet | SIL Open Font License v1.1 | Domine | `morale/fonts/tieralphabet/LICENSE` |
| TT Directors | SIL Open Font License v1.1 | TT Directors | `morale/fonts/tt_directors/LICENSE` |
| TT Masters | SIL Open Font License v1.1 | TT Masters | `morale/fonts/tt_masters/LICENSE` |
| Venezia | SIL Open Font License v1.1 | Andada Pro | `morale/fonts/venezia/LICENSE` |
| Venezia small | SIL Open Font License v1.1 | Andada Pro | `morale/fonts/venezia_small/LICENSE` |
| Violin Serif | SIL Open Font License v1.1 | Instrument Serif | `morale/fonts/violin_serif/LICENSE` |
| Western Light | SIL Open Font License v1.1 | Sancreek | `morale/fonts/western_light/LICENSE` |
