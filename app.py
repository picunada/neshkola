from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()
AMO_URL = "https://bbintegration.amocrm.ru"


async def authorization(session, client_id: str, client_secret: str, auth_code: str, redirect_uri: str) -> dict:
    amo_request = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri
    }
    async with session.post(AMO_URL + '/oauth2/access_token', json=amo_request) as response:
        return await response.json()


@app.post("/")
async def post_amo(request: Request):
    print(request)
    print(f'query: {request.query_params}')
    print(f'path: {request.path_params}')
    print(f'headers: {request.headers}')
    print(f'cookies: {request.cookies}')
    print(f'body: {await request.json()}')


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
