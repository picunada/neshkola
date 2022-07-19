from fastapi import FastAPI, Request
import aiohttp
import uvicorn
import aioredis

from core import Settings

app = FastAPI()
AMO_URL = "https://amoadminneshkolacom.amocrm.ru"
settings = Settings()
redis = aioredis.from_url("redis://localhost")
keys_lst = ["utm_content", "utm_medium", "utm_campaign", "utm_source", "utm_term", "utm_referrer", "utm_campaign", "referer"]
town_lst = ["Курск", "Новороссийск", "Королев", "Тула", "Тверь", "Астрахань", "Уфа", "Екатеринбург", "Новосибирск", "Владивосток"]


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
        print("refresh", await response.json())
        return await response.json()


@app.on_event("startup")
async def startup():
    access_token = await redis.get('access_token')
    refresh_token = await redis.get('refresh_token')
    print("token", access_token)

    async with aiohttp.ClientSession() as session:
        if not access_token:
            response = await authorization(session=session, client_id=settings.client_id,
                                           client_secret=settings.client_secret,
                                           auth_code=settings.auth_code, redirect_uri=settings.redirect_uri)
            print("response", response)
            await redis.set('access_token', response['access_token'])
            await redis.set('refresh_token', response['refresh_token'])
        curr_access_token = await redis.get('access_token')
        headers = {'Authorization': 'Bearer ' + curr_access_token.decode()}
        print("headers", headers)
        # async with session.get(AMO_URL + '/api/v4/leads/36637175', headers=headers) as response:
        #     print("STATUS_ID:!!!!!!!!!!!!!!!", await response.json())
        async with session.get(AMO_URL + '/api/v4/leads', headers=headers) as response:
            res = await response.json()
            print("res", res)
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
    keys_from_body = body.keys()
    print(body)

    if "test" in keys_from_body:
        print("test")
        return
    try:
        if body['COOKIES']:
            del body['COOKIES']
    except Exception as e:
        print(e)
    async with aiohttp.ClientSession(headers=headers) as session:
        for i in keys_lst:
            if i not in keys_from_body:
                body[i] = None
        print(body)
        if "town" not in keys_from_body:
            body["town"] = body["Selectbox"]
            body["phone"] = body["Phone"]

        if body["town"] in town_lst:
            req = [
                {
                    "name": "Нешкола барабанов",
                    "pipeline_id": 5337868,
                    "status_id":  47510455,
                    "_embedded": {
                        # "metadata": {
                        #     "category": "forms",
                        #     "form_page": "ne-shkola.com",
                        #     "form_id": body["formid"],
                        #     "form_name": body["formname"],
                        # },
                        "contacts": [
                            {
                                "name": body["name"],
                                "custom_fields_values": [
                                    {
                                        "field_id": 33210,
                                        "values": [
                                            {
                                                "enum_id": 77028,
                                                "value": body["phone"]
                                            }
                                        ]
                                    },
                                    {
                                        "field_id": 601145,
                                        "values": [
                                            {
                                                "value": body["town"]
                                            }
                                        ]
                                    }
                                ]
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
                    ],
                }
            ]
            # async with session.get(AMO_URL + '/api/v4/leads/36637175') as response:
            #     print(await response.json())
            async with session.post(AMO_URL + '/api/v4/leads/complex', json=req) as response:
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
