"""Per-pattern normalization that retains explicit source trim commands."""
from copy import deepcopy
from pyembroidery import EmbPattern
from pyembroidery.EmbEncoder import Transcoder


def preserve_explicit_trims(pattern, preserve_pause_state=False):
    class ExplicitNormalizer(Transcoder):
        def tie_off_and_trim_if_needed(self):
            # Called for a source TRIM, including one after a color change.
            if self.state_trimmed:self.trim_here()
            else:super().tie_off_and_trim_if_needed()

        def stop_here(self):
            trimmed=self.state_trimmed
            super().stop_here()
            if preserve_pause_state:self.state_trimmed=trimmed

    class ExplicitPattern(EmbPattern):
        def get_normalized_pattern(self,encode_settings=None):
            normal=EmbPattern();ExplicitNormalizer(encode_settings).transcode(self,normal)
            return normal

    cloned=ExplicitPattern();cloned.__dict__.update(deepcopy(pattern.__dict__))
    return cloned
