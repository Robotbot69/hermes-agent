import json
import pytest
from agent.display import _detect_tool_failure
from agent.tool_guardrails import classify_tool_failure


@pytest.mark.parametrize('classifier', [_detect_tool_failure, classify_tool_failure])
@pytest.mark.parametrize('data,failed', [
    ({'results': [{'url': 'https://example.test', 'content': 'Fetched content', 'error': None}]}, False),
    ({'error': None, 'message': 'Fetched content'}, False),
    ({'failed': False, 'content': 'Fetched content'}, False),
    ({'results': [{'content': 'Good', 'error': None}, {'error': 'HTTP 404'}]}, True),
    ({'results': [{'error': 'HTTP 404'}]}, True),
    ({'success': False, 'message': 'Request failed'}, True),
    ({'error': 'Request failed'}, True),
])
def test_null_errors_are_success_but_real_errors_remain_failures(classifier, data, failed):
    assert classifier('web_extract', json.dumps(data))[0] is failed
