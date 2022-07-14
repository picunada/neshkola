from fastapi import FastAPI, Request
import aiohttp
import uvicorn
import aioredis

from core import Settings

app = FastAPI()
AMO_URL = "https://bbintegration.amocrm.ru"
settings = Settings()
redis = aioredis.from_url("redis://localhost")


async def authorization(session: aiohttp.ClientSession, client_id: str,
                        client_secret: str, auth_code: str, redirect_uri: str) -> dict:
    amo_request = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri
    }
    async with session.post(AMO_URL + '/oauth2/access_token', json=amo_request) as response:
        return await response.json()


async def refresh_jwt(session: aiohttp.ClientSession, client_id: str,
                      client_secret: str, refresh_token: str, redirect_uri: str) -> dict:
    req = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": redirect_uri
    }
    async with session.post(AMO_URL + '/oauth2/access_token', json=req) as response:
        return await response.json()


@app.on_event("startup")
async def startup():
    access_token = await redis.get('access_token')
    refresh_token = await redis.get('refresh_token')

    async with aiohttp.ClientSession() as session:
        if not access_token:
            response = await authorization(session=session, client_id=settings.client_id,
                                           client_secret=settings.client_secret,
                                           auth_code=settings.auth_code, redirect_uri=settings.redirect_uri)
            print(response)
            await redis.set('access_token', response['access_token'])
            await redis.set('refresh_token', response['refresh_token'])
        headers = {'Authorization': 'Bearer ' + access_token.decode()}
        async with session.get(AMO_URL + '/api/v4/leads', headers=headers) as response:
            res = await response.json()
            try:
                if res['title'] == 'Unauthorized':
                    new_tokens = await refresh_jwt(session=session, client_id=settings.client_id,
                                                   client_secret=settings.client_secret,
                                                   refresh_token=refresh_token.decode(),
                                                   redirect_uri=settings.redirect_uri)
                    await redis.set('access_token', new_tokens['access_token'])
                    await redis.set('refresh_token', new_tokens['refresh_token'])
            except KeyError:
                print('Access token is okay')


@app.post("/amo_crm")
async def post_amo(request: Request):
    access_token = await redis.get('access_token')
    headers = {'Authorization': 'Bearer ' + access_token.decode()}
    body = await request.json()
    del body['COOKIES']
    async with aiohttp.ClientSession(headers=headers) as session:
        req = {
            {
                "created_by": 0,
                "_embedded": {
                    "contacts": [
                        {
                            "name": body['name'],

                        }
                    ]
                },
                "custom_fields_values": [
                    {
                        "field_code": "UTM_SOURCE",
                        "values": [
                            {
                                "value": body['utm_source']
                            }
                        ]
                    },
                    {
                        "field_code": "UTM_MEDIUM",
                        "values": [
                            {
                                "value": body['utm_medium']
                            }
                        ]
                    },
                    {
                        "field_code": "UTM_CAMPAIGN",
                        "values": [
                            {
                                "value": body['utm_campaign']
                            }
                        ]
                    }
                ]
            }
        }
        async with session.post(AMO_URL + '/api/v4/leads', json=req) as response:
            print(await response.json())


@app.get("/get_amo_objects")
async def amo_objects():
    access_token = await redis.get('access_token')
    headers = {'Authorization': 'Bearer ' + access_token.decode()}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(AMO_URL + '/api/v4/leads/custom_fields') as response_one:
            async with session.get(AMO_URL + '/api/v4/contacts/custom_fields') as response_two:
                return {
                    'fields': await response_one.json(),
                    'contacts': await response_two.json()
                }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
