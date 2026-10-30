# Third-party software

Morale source code is licensed under GPL-3.0-or-later; see LICENSE. It uses these separately
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
installers; installed dependency license texts are collected into the bundle’s dependency-licenses directory. Its manifest lists missing texts. Complete dependency/native-library and source/relinking review remains part of release work.

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

## ZigZag

Some satin and travel-routing techniques in `morale/satin_geometry.py` and
`morale/fill_travel.py` are adapted from ZigZag (https://github.com/simpsoka/zigzag),
an embroidery studio by its contributors, licensed under the Apache License,
Version 2.0. Morale reimplements them in Python with changes noted in the code:
staggered satin split points, and travel stitches that follow the inside of a
fill's outline. The license text follows.

```

                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS
```

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

## tinycss2 1.5.1 license

BSD 3-Clause License

Copyright (c) 2013-2020, Simon Sapin and contributors.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## cssselect2 0.10.1 license

BSD 3-Clause License

Copyright (c) 2012-2018, Simon Sapin and contributors (see AUTHORS).
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## webencodings 0.6.1 license

BSD 3-Clause License

Copyright (c) 2012, Simon Sapin
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
