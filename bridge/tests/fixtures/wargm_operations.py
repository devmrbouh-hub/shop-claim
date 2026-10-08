"""Sample WarGM operations API response for parser tests."""

SAMPLE_OPERATIONS_LIST = [
    {
        "operation_id": 1001,
        "offer_id": 5001,
        "steam_id": "76561198000000001",
        "server_id": 68109,
        "status": "pending",
        "claimed": 0,
    }
]

SAMPLE_OPERATIONS_WRAPPED = {
    "operations": [
        {
            "id": "1002",
            "offerId": 5002,
            "steamId": "76561198000000002",
            "serverId": 68109,
        }
    ]
}

# WarGM API v1.1 — top-level status, flat operations in response.data
SAMPLE_WARGM_V11_ENVELOPE = {
    "status": "ok",
    "limit": 499,
    "response": {
        "data": {
            "7758693": {
                "id": 7758693,
                "server_id": 10001,
                "offer_id": 264775,
                "user_steam_id": "76561198000000001",
                "status": "pending",
                "delivery": "api",
            }
        },
    },
}

# v1.1 nested: server_id on parent group
SAMPLE_WARGM_V11_NESTED = {
    "status": "ok",
    "response": {
        "data": {
            "10001": {
                "server_id": 10001,
                "operations": [
                    {
                        "id": 7758694,
                        "offer_id": 264776,
                        "user_steam_id": "76561198000000002",
                        "status": "pending",
                        "delivery": "online",
                    }
                ],
            }
        },
    },
}

SAMPLE_WARGM_V1_VERSION_ERROR = {
    "responce": {
        "status": "error",
        "msg": "Called API version not supported. wargm.ru/docs_api",
    }
}

# Real WarGM API shape (operations keyed by id inside responce.data)
SAMPLE_WARGM_ENVELOPE = {
    "responce": {
        "status": "ok",
        "data": {
            "7758693": {
                "id": 7758693,
                "server_id": 10001,
                "offer_id": 264775,
                "user_steam_id": 76561198000000001,
                "status": "pending",
                "delivery": "api",
            }
        },
    }
}
