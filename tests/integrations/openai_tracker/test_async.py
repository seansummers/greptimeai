import time
import uuid

import pytest

from greptimeai.openai_patcher import _collector

from ..database.db import get_trace_data, truncate_tables
from ..openai_tracker import async_client


@pytest.fixture
def _truncate_tables():
    truncate_tables()
    yield


@pytest.mark.asyncio
async def test_chat_completion(_truncate_tables):
    user_id = str(uuid.uuid4())
    model = "gpt-3.5-turbo"
    resp = await async_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "1+1=",
            }
        ],
        model=model,
        user=user_id,
        seed=1,
    )
    assert resp.choices[0].message.content == "2"

    _collector._collector._force_flush()

    trace = get_trace_data(user_id)
    retry = 0
    while retry < 3 and not trace:
        retry += 1
        time.sleep(2)
        trace = get_trace_data(user_id)

    assert trace is not None

    assert "openai" == trace.get("resource_attributes", {}).get("service.name")
    assert "openai_completion" == trace.get("span_name")

    assert ["client.chat.completions.create[async]", "end"] == [
        event.get("name") for event in trace.get("span_events", [])
    ]

    assert resp.model == trace.get("model")
    assert resp.model.startswith(model)

    assert resp.usage
    assert resp.usage.prompt_tokens == trace.get("prompt_tokens")
    assert resp.usage.completion_tokens == trace.get("completion_tokens")