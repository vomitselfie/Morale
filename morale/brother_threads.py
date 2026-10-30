"""Brother Embroidery thread numbers by color.

The chart Brother's Artspira app uses, from Respira's BrotherColor.json
(Apache-2.0, Copyright Jan-Henrik Bruhn) by way of ZigZag (Apache-2.0); see
THIRD_PARTY_NOTICES.md. The PEC palette's colors are these threads, so names
come from the PEC palette where colors match. Numbers are as published by
those projects and have not been checked against physical spools.
"""

BROTHER_NUMBERS = [
    ("#f0f0f0", "001"),
    ("#efe3b9", "843"),
    ("#ffffb3", "010"),
    ("#e3f35b", "027"),
    ("#a8ddc4", "542"),
    ("#a8deeb", "017"),
    ("#b2afd4", "804"),
    ("#fdd9de", "124"),
    ("#fcbbc4", "079"),
    ("#d8ccc6", "399"),
    ("#fee3c5", "307"),
    ("#a8a8a8", "005"),
    ("#fff08d", "812"),
    ("#f0f970", "202"),
    ("#9ed67d", "502"),
    ("#66ba49", "509"),
    ("#2584bb", "019"),
    ("#915fac", "612"),
    ("#e49acb", "810"),
    ("#f993bc", "085"),
    ("#f64a8a", "086"),
    ("#d0a660", "348"),
    ("#878787", "817"),
    ("#feb343", "126"),
    ("#ffff00", "205"),
    ("#70bc1f", "513"),
    ("#008777", "534"),
    ("#095ba6", "420"),
    ("#686ab0", "607"),
    ("#913697", "620"),
    ("#f73866", "807"),
    ("#d15400", "339"),
    ("#ba9800", "328"),
    ("#4f5556", "704"),
    ("#fe9e32", "209"),
    ("#ffd911", "206"),
    ("#2f7e20", "515"),
    ("#00673e", "507"),
    ("#0a55a3", "405"),
    ("#4b6baf", "070"),
    ("#770176", "869"),
    ("#c70156", "107"),
    ("#fe370f", "030"),
    ("#7d6f00", "330"),
    ("#293133", "707"),
    ("#e8a900", "214"),
    ("#feba35", "208"),
    ("#435607", "517"),
    ("#134a46", "415"),
    ("#0b3d91", "406"),
    ("#4e2990", "614"),
    ("#6a1c8a", "613"),
    ("#b54c64", "333"),
    ("#ed171f", "800"),
    ("#d15c00", "337"),
    ("#000000", "900"),
    ("#2a1301", "058"),
    ("#b27624", "323"),
    ("#132b1a", "519"),
    ("#003822", "808"),
    ("#0e1f7c", "007"),
]


def brother_catalog():
    from pyembroidery.EmbThreadPec import get_thread_set
    from .catalogs import ThreadEntry
    names = {thread.hex_color().lower(): thread.description for thread in get_thread_set() if thread is not None}
    return [ThreadEntry(color, {"brand": "Brother", "catalog_number": number,
                                "description": names.get(color, f"Brother {number}"), "chart": "Brother Embroidery"})
            for color, number in BROTHER_NUMBERS]
