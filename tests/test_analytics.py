from hermes_school.analytics.grades import subject_averages
from hermes_school.models.normalize import plain_text


def test_weighted_subject_average_requires_coefficients():
    items = [{'id': i, 'subject': 'Maths', 'kind': 'grades', 'data': {'out_of_20': score, 'coefficient': coefficient}} for i, (score, coefficient) in enumerate([(10, 1), (20, 3)])]
    assert subject_averages(items)[0]['average'] == 17.5
    items[0]['data']['coefficient'] = None
    assert subject_averages(items)[0]['average'] is None


def test_html_remains_untrusted_text():
    assert plain_text('<p>Exercice &amp; révision</p><script>steal()</script>') == 'Exercice & révision'
