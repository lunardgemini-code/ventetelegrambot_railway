from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.post("/test")
async def test_route(data: dict):
    return {"data": data}

client = TestClient(app)
response = client.post("/test", json={"orders": [{"id": 1, "sort_order": 0}]})
print(response.status_code)
print(response.json())
