import pytest
from morale.perceptual_color import oklab,distance_squared
from morale.model import Project,DesignObject
from morale.trace_threads import match_trace_threads


@pytest.mark.parametrize('color,expected',[
    ('#000000',(0,0,0)),('#ffffff',(1,0,0)),
    ('#ff0000',(.62795536,.22486306,.12584630)),
    ('#00ff00',(.86643961,-.23388757,.17949848)),
    ('#0000ff',(.45201372,-.03245698,-.31152815))])
def test_reference_primary_coordinates(color,expected):
    assert oklab(color)==pytest.approx(expected,abs=1e-7)


@pytest.mark.parametrize('color',['#0a0b0c','#123456','#808080','#deadbe','#fedcba'])
def test_published_inverse_recovers_linear_srgb(color):
    # Independently apply Ottosson's published inverse, then compare with the
    # expected decoded sRGB. Includes channels on either side of the gamma knee.
    L,a,b=oklab(color)
    l=(L+.3963377774*a+.2158037573*b)**3
    m=(L-.1055613458*a-.0638541728*b)**3
    s=(L-.0894841775*a-1.291485548*b)**3
    actual=(4.0767416621*l-3.3077115913*m+.2309699292*s,
            -1.2684380046*l+2.6097574011*m-.3413193965*s,
            -.0041960863*l-.7034186147*m+1.707614701*s)
    encoded=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    expected=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in encoded]
    assert actual==pytest.approx(expected,abs=2e-7)


def test_distances_and_metric_metadata():
    assert distance_squared('#abcdef','#ABCDEF')==0
    assert distance_squared('#fff000','#012345')==distance_squared('#012345','#fff000')
    source=Project(objects=[DesignObject(color='#00aaff')])
    for metric in ('oklab','rgb'):
        result,matches=match_trace_threads(source,'PEC fixed palette',metric)
        assert matches[0]['metric']==metric and matches[0]['distance']>=0
        assert result.objects[0].thread
    with pytest.raises(ValueError): match_trace_threads(source,'','unsupported')


def test_perceptual_and_rgb_matching_can_choose_different_threads():
    source=Project(objects=[DesignObject(color='#cc8833')])
    perceptual,_=match_trace_threads(source,'PEC fixed palette','oklab')
    comparison,_=match_trace_threads(source,'PEC fixed palette','rgb')
    assert perceptual.objects[0].color=='#ba9800'
    assert comparison.objects[0].color=='#b27624'
