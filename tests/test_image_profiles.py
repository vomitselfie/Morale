import pytest
from PySide6.QtGui import QImage,QColor,QColorSpace
from morale.raster_trace import srgb_image,trace_image


def test_linear_rgb_conversion_matches_known_transfer_and_keeps_alpha():
    image=QImage(4,4,QImage.Format.Format_RGBA8888)
    image.fill(QColor(128,64,0,173));image.setColorSpace(QColorSpace.NamedColorSpace.SRgbLinear)
    converted,info=srgb_image(image);color=converted.pixelColor(0,0)
    assert (color.red(),color.green(),color.blue(),color.alpha())==(188,137,0,173)
    assert image.pixelColor(0,0)==QColor(128,64,0,173)
    assert info['converted'] and not info['assumed']
    assert converted.colorSpace()==QColorSpace(QColorSpace.NamedColorSpace.SRgb)


def test_untagged_and_srgb_colors_are_unchanged():
    image=QImage(4,4,QImage.Format.Format_ARGB32);image.fill(QColor(34,91,127,128))
    for tagged in (False,True):
        if tagged:image.setColorSpace(QColorSpace.NamedColorSpace.SRgb)
        result,info=srgb_image(image)
        assert result.pixelColor(0,0)==image.pixelColor(0,0)
        assert info['assumed']==(not tagged) and not info['converted']


@pytest.mark.parametrize('method',['pixels','smooth'])
def test_embedded_profile_is_applied_before_color_reduction(tmp_path,method):
    image=QImage(32,32,QImage.Format.Format_RGB32);image.fill(QColor(128,64,0))
    image.setColorSpace(QColorSpace.NamedColorSpace.SRgbLinear)
    path=tmp_path/'linear.png';assert image.save(str(path));before=path.read_bytes()
    project,sampled,stats=trace_image(path,width=20,colors=1,method=method)
    assert path.read_bytes()==before
    assert sampled.pixelColor(10,10)==QColor(188,137,0)
    assert project.objects[0].color=='#bc8900'
    assert stats['color_profile']['converted']


@pytest.mark.parametrize('profile',[QColorSpace.NamedColorSpace.DisplayP3,QColorSpace.NamedColorSpace.AdobeRgb])
def test_tagged_png_roundtrip_preserves_intended_srgb_colors(tmp_path,profile):
    # Start with sRGB values within both gamuts, encode to another profile, then
    # verify the file-based tracing path returns the intended sRGB swatch.
    original=QImage(32,32,QImage.Format.Format_RGB32);original.fill(QColor(100,130,170))
    original.setColorSpace(QColorSpace.NamedColorSpace.SRgb)
    encoded=original.convertedToColorSpace(profile);path=tmp_path/'wide.png';encoded.save(str(path))
    _,sampled,stats=trace_image(path,colors=1)
    color=sampled.pixelColor(0,0)
    assert (color.red(),color.green(),color.blue())==pytest.approx((100,130,170),abs=2)
    assert stats['color_profile']['converted']
