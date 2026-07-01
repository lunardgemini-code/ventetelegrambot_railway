from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.post("/api/products/reorder")
async def test_route():
    return {"status": "ok"}

client = TestClient(app)
response = client.post("//api/products/reorder")
print("Status:", response.status_code)
