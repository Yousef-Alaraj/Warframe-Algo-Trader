import json
import requests
from bs4 import BeautifulSoup
import time
import config
import pandas as pd
import customLogger

def get_id_to_url_map():
    # 1. Load the CSV
    df = pd.read_csv("allItemData.csv")
    
    # 2. Drop rows where item_id or url_name might be missing (safety check)
    df = df.dropna(subset=['item_id', 'url_name'])
    
    # 3. Create the dictionary: { "item_id": "url_name" }
    # We cast to string to ensure the ID matches the format you get from the API
    id_map = dict(zip(df["item_id"].astype(str), df["url_name"]))
    
    return id_map

url_name_lookup = get_id_to_url_map()

class WarframeApi:
    def __init__(self):
        self.t0 = time.time()
        self.jwt_token = config.jwt_token
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "auth_type": "header",
            "platform": config.platform,
            "language": "en",
            "Authorization": self.jwt_token,
            'User-Agent': 'Warframe Algo Trader/1.3.4',
        }
        self.lastRequestTime = 0
        self.timeBetweenRequests = 3

    def waitUntilDelayEnds(self):
        if (time.time() - self.lastRequestTime) < self.timeBetweenRequests:
            time.sleep(self.lastRequestTime - time.time() + self.timeBetweenRequests)
        
    def get(self, link, headers=None):
        t0 = time.time()
        self.waitUntilDelayEnds()
        self.lastRequestTime = time.time()
        r = requests.get(link, headers=self.headers)
        #print(time.time()-t0)
        return r
    def post(self, link, json, headers=None):
        t0 = time.time()
        self.waitUntilDelayEnds()
        self.lastRequestTime = time.time()
        r = requests.post(link, headers=self.headers, json=json)
        #print(time.time()-t0)
        return r
    def delete(self, link, headers=None):
        t0 = time.time()
        self.waitUntilDelayEnds()
        self.lastRequestTime = time.time()
        r = requests.delete(link, headers=self.headers)
        #print(time.time()-t0)
        return r
    def put(self, link, json, headers=None):
        t0 = time.time()
        self.waitUntilDelayEnds()
        self.lastRequestTime = time.time()
        r = requests.put(link, headers=self.headers, json=json)
        #print(time.time()-t0)
        return r
    def patch(self, link, json, header=None):
        t0 = time.time()
        self.waitUntilDelayEnds()
        self.lastRequestTime = time.time()
        r = requests.patch(link, headers=self.headers, json=json)
        #print(time.time()-t0)
        return r

        

# Old v1 api path 
# WFM_API = "https://api.warframe.market/v1"
WFM_API = "https://api.warframe.market/v2"

warframeApi = WarframeApi()

def login(
    user_email: str, user_password: str, platform: str = "pc", language: str = "en"
):
    """
    Used for logging into warframe.market via the API.
    Returns (User_Name, JWT_Token) on success,
    or returns (None, None) if unsuccessful.
    """
    raise NotImplementedError("This login endpoint is deprecated and disallowed by v2 API.")
    content = {"email": user_email, "password": user_password, "auth_type": "header"}
    response = warframeApi.post(f"{WFM_API}/auth/signin", data=json.dumps(content))
    customLogger.writeTo(
        "wfmAPICalls.log",
        f"POST:{WFM_API}/auth/signin\tResponse:{response.status_code}"
    )
    if response.status_code != 200:
        return None, None
    return (response.json()["payload"]["user"]["ingame_name"], response.headers["Authorization"])

def postOrder(item, order_type, platinum, quantity, visible, modRank, itemName):
    # if order_type == "buy":
    #     visible = False
    json_data = {
        "itemId": str(item),
        "type": str(order_type),
        "platinum": int(platinum),
        "quantity": int(quantity),
        "visible": bool(visible),
        "subtype": "regular"
    }
    if modRank:
        json_data["rank"] = int(modRank)

    if subtype and str(subtype).lower() != "nan":
        json_data["subtype"] = str(subtype)
    
    # print(json_data.keys())
    print(f"RAW JSON PAYLOAD: {json.dumps(json_data)}")
    
    response = warframeApi.post(f'{WFM_API}/order', json=json_data)
    print(response.text)

    customLogger.writeTo(
        "wfmAPICalls.log",
        f"POST:{WFM_API}/order\tResponse:{response.status_code}\tItem:{itemName}\tOrder Type:{order_type}\tPlatinum:{platinum}\tQuantity:{quantity}\tVisible:{visible}\tRank:{modRank}"
    )

    if response.status_code == 200:
        customLogger.writeTo(
            "orderTracker.log",
            f"POSTED\tItem:{itemName}\tOrder Type:{order_type}\tPlatinum:{platinum}\tQuantity:{quantity}\tVisible:{visible}"
        )
    else:
        if 'perTrade' in response.text:
            json_data["perTrade"] = 1
            response = warframeApi.post(f'{WFM_API}/order', json=json_data)
            if response.status_code == 200:
                customLogger.writeTo(
                    "wfmAPICalls.log",
                    f"POST:{WFM_API}/order\tResponse:{response.status_code}\tItem:{itemName}\tOrder Type:{order_type}\tPlatinum:{platinum}\tQuantity:{quantity}\tVisible:{visible}\tRank:{modRank}"
                )

    return response
    

def deleteOrder(orderID):
    r = warframeApi.delete(f'{WFM_API}/order/{orderID}')
    customLogger.writeTo(
        "wfmAPICalls.log",
        f"DELETE:{WFM_API}/profile/orders/{orderID}\tResponse:{r.status_code}"
    )
    if r.status_code == 200:
        customLogger.writeTo(
            "orderTracker.log",
            f"DELETED\tOrder ID: {orderID}"
        )
    
def getOrders():
    # Old v1 get of my profile orders
    # r = warframeApi.get(f"{WFM_API}/profile/{config.inGameName}/orders")
    r = warframeApi.get(f"{WFM_API}/orders/my", headers=warframeApi.headers)
    v2_response = r.json()["data"]
    # print(v2_response[0])
    v1_formatted_response = {
        "sell_orders": [],
        "buy_orders": [],
    }

    for v2_item in v2_response:
        slug = url_name_lookup.get(str(v2_item["itemId"]))
        translated_item = {
            "visible": v2_item["visible"],
            "quantity": v2_item["quantity"],
            "perTrade": v2_item.get("perTrade", None),
            "rank": v2_item.get("rank", None),
            "platinum": v2_item["platinum"],
            "id": v2_item["id"],
            "creation_date": v2_item["createdAt"],
            "updatedAt": v2_item["updatedAt"],
            "itemId": v2_item.get("itemId", None),
            "item": {
                "url_name": slug
            }
        }
        if(v2_item["type"] == "sell"):
            v1_formatted_response["sell_orders"].append(translated_item)
        else:
            v1_formatted_response["buy_orders"].append(translated_item)
    customLogger.writeTo(
        "wfmAPICalls.log",
        f"GET:{WFM_API}/orders/my\tResponse:{r.status_code}"
    )
    return v1_formatted_response

def updateListing(listing_id, platinum, quantity, visibility, itemName, order_type):
    # if order_type == "buy":
    #     visibility = False
    try:
        url = WFM_API + "/order/" + listing_id
        contents = {
            "platinum": int(platinum),
            "quantity": int(quantity),
            "visible": bool(visibility)
        }
        response = warframeApi.patch(url, json=contents)
        if response.status_code != 200:
            print(f"DEBUG: API returned {response.status_code}")
            print(f"DEBUG: API Error Body: {response.text}") # <--- ADD THIS
            print(f"DEBUG: Response Body={response.text}")
        customLogger.writeTo(
            "wfmAPICalls.log",
            f"PATCH:{WFM_API}/profile/orders/{listing_id}\tResponse:{response.status_code}\tItem:{itemName}\tOrder Type:{order_type}\tPlatinum:{platinum}\tVisible:{visibility}"
        )  
        response.raise_for_status()  # Raises an exception for non-2xx status codes
        if response.status_code == 200:
            customLogger.writeTo(
                "orderTracker.log",
                f"UPDATED\tItem:{itemName}\tOrder Type:{order_type}\tPlatinum:{platinum}\tVisible:{visibility}"
            )
        return True
    except requests.exceptions.RequestException as e:
        print(f"update_listing: {e}")
        return False
    
if __name__ == "__main__":
    r = warframeApi.post(
        f'{WFM_API}/profile/orders',
        {
            "item": "5bc1ab93b919f200c18c10ef",
            "platinum": 1,
            "order_type": "buy",
            "quantity": 1,
            "rank": 1,
            "visible": False
        }
    )
    print(r.status_code)
