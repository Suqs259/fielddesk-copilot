import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import retrieve, workflow


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'test.db'))
    monkeypatch.setenv('MODEL_MODE', 'demo')
    monkeypatch.setenv('ACME_API_KEY', 'demo-acme')
    monkeypatch.setenv('NOVA_API_KEY', 'demo-nova')
    return TestClient(app)


def test_authorization_before_retrieval():
    docs = retrieve('Nova NOVA-PRIVATE-7788 专线 E101', 'acme')
    assert all(d['tenant'] in ('public', 'acme') for d in docs)
    assert 'NOVA-PRIVATE-7788' not in str(docs)


def test_unknown_question_abstains():
    s = workflow.invoke({'question': 'zzzzqqqqxxxx', 'tenant': 'acme', 'history': []})
    assert s['status'] == 'needs_clarification'
    assert s['sources'] == []


def test_chat_citations_budget_and_ticket(client):
    headers = {'X-API-Key': 'demo-acme'}
    body = {'question': 'Atlas E101 网络故障', 'session_id': 'shared-session'}
    result = client.post('/api/chat', json=body, headers=headers)
    assert result.status_code == 200
    data = result.json()
    assert data['sources']
    assert data['metrics']['context_chars'] <= 3600
    assert all(f"[{d['id']}]" in data['answer'] for d in data['sources'])
    ticket = client.post('/api/ticket', json=body, headers=headers)
    assert ticket.json()['status'] == 'draft'
    other = client.post('/api/ticket', json=body, headers={'X-API-Key': 'demo-nova'})
    assert other.status_code == 404
    followup = client.post('/api/chat', json=body, headers={'X-API-Key': 'demo-nova'}).json()
    assert followup['metrics']['history_turns'] == 0


def test_auth_and_validation(client):
    assert client.post('/api/chat', json={'question': 'E101'}).status_code == 401
    assert client.post('/api/chat', json={'question': ' '}, headers={'X-API-Key':'demo-acme'}).status_code == 422
    assert client.get('/').status_code == 200


def test_bounded_history():
    s = workflow.invoke({'question':'E202', 'tenant':'acme', 'history':['a'*10000]*20})
    assert len(s['query']) <= 910


@pytest.mark.parametrize('answer,status', [('请检查电源 [public-01]', 'answered'), ('无引用的回答', 'needs_review'), ('请重置 [fake-99]', 'needs_review')])
def test_live_citation_guard(monkeypatch, answer, status):
    from types import SimpleNamespace
    import langchain_openai
    monkeypatch.setenv('MODEL_MODE', 'live')
    class FakeModel:
        def __init__(self, **kwargs):
            pass
        def invoke(self, messages):
            return SimpleNamespace(content=answer)
    monkeypatch.setattr(langchain_openai, 'ChatOpenAI', FakeModel)
    s = workflow.invoke({'question':'Atlas E101', 'tenant':'acme', 'history':[]})
    assert s['status'] == status
