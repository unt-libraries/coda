import pytest

from .. import views


pytestmark = pytest.mark.django_db()


def test_index_returns_ok(rf):
    request = rf.get('/')
    response = views.index(request)
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/xml'


def test_index_with_verb_returns_ok(rf):
    request = rf.get('/?verb=Identify')
    response = views.index(request)

    assert b"""<Identify>
    <repositoryName>example.com</repositoryName>
    <baseURL>http://example.com/oai/</baseURL>
    <protocolVersion>2.0</protocolVersion>
    <adminEmail>mark.phillips@unt.edu</adminEmail>
    <earliestDatestamp>2004-05-19T00:00:00Z</earliestDatestamp>
    <deletedRecord>transient</deletedRecord>
    <granularity>YYYY-MM-DDThh:mm:ssZ</granularity>
    <description>
      <toolkit xmlns="http://oai.dlib.vt.edu/OAI/metadata/toolkit"\
 xsi:schemaLocation="http://oai.dlib.vt.edu/OAI/metadata/toolkit\
 http://oai.dlib.vt.edu/OAI/metadata/toolkit.xsd">
        <title>pyoai</title>
        <version>2.5.0</version>
        <URL>http://infrae.com/products/oaipack</URL>
      </toolkit>
    </description>
  </Identify>""" in response.content

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/xml'
