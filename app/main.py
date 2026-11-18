import hmac
import os
import sqlite3
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.core import workflow

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title='FieldDesk Copilot', version='1.0.0')


def connect():
    db = sqlite3.connect(os.getenv('DATABASE_PATH', str(ROOT / 'fielddesk.db')))
    db.execute('CREATE TABLE IF NOT EXISTS turns (session TEXT, tenant TEXT, question TEXT, answer TEXT, created REAL)')
    return db


def identity(key: str | None):
    keys = {'acme': os.getenv('ACME_API_KEY', 'demo-acme'), 'nova': os.getenv('NOVA_API_KEY', 'demo-nova')}
    for tenant, expected in keys.items():
        if key and hmac.compare_digest(key, expected):
            return tenant
    raise HTTPException(401, 'Invalid API key')


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), max_length=100, pattern=r'^[a-zA-Z0-9-]+$')


@app.get('/')
def home():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/health')
def health():
    return {'status': 'ok', 'mode': os.getenv('MODEL_MODE', 'demo')}


@app.post('/api/chat')
def chat(body: ChatRequest, x_api_key: str | None = Header(default=None)):
    tenant = identity(x_api_key)
    started = time.perf_counter()
    question = body.question.strip()
    if len(question) < 2:
        raise HTTPException(422, 'Question must contain at least two non-space characters')
    with connect() as db:
        rows = db.execute('SELECT question FROM turns WHERE session=? AND tenant=? ORDER BY rowid DESC LIMIT 3',
                          (body.session_id, tenant)).fetchall()
    try:
        state = workflow.invoke({'question': question, 'tenant': tenant, 'history': [r[0] for r in reversed(rows)]})
    except Exception:
        raise HTTPException(502, 'Model workflow failed; verify model configuration or use demo mode')
    with connect() as db:
        db.execute('INSERT INTO turns VALUES (?, ?, ?, ?, ?)',
                   (body.session_id, tenant, question, state['answer'], time.time()))
    return {'session_id': body.session_id, 'answer': state['answer'], 'status': state['status'],
            'sources': state['sources'], 'mode': state['mode'], 'context': state['context'],
            'metrics': {'latency_ms': round((time.perf_counter()-started)*1000),
                        'context_chars': state['context_chars'], 'history_turns': len(rows)}}


@app.post('/api/ticket')
def ticket(body: ChatRequest, x_api_key: str | None = Header(default=None)):
    tenant = identity(x_api_key)
    with connect() as db:
        row = db.execute('SELECT question, answer FROM turns WHERE session=? AND tenant=? ORDER BY rowid DESC LIMIT 1',
                         (body.session_id, tenant)).fetchone()
    if not row:
        raise HTTPException(404, 'No conversation found')
    return {'title': row[0][:80], 'tenant': tenant, 'status': 'draft',
            'description': f'客户问题：{row[0]}\n\n已有排查依据：{row[1]}\n\n待补充：影响范围、发生时间、日志。'}
