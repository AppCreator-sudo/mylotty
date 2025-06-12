import aiohttp
from uuid import uuid4
from typing import Optional, Dict
import logging
import traceback

logger = logging.getLogger(__name__)

class CryptoPay:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {"Crypto-Pay-API-Token": self.token}

    async def create_invoice(
        self,
        amount: float,
        currency: str = "TON",
        description: Optional[str] = None,
        payload: Optional[str] = None,
        expires_in: Optional[int] = 3600
    ) -> Dict:
        """Создание инвойса для пополнения"""
        params = {
            "asset": currency,
            "amount": str(amount),
            "description": description,
            "payload": payload,
            "expires_in": expires_in
        }
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/createInvoice",
                    data=params,
                    headers=self.headers
                ) as response:
                    data = await response.json()
                    logger.info(f"create_invoice response: {data}")
                    return data
        except Exception as e:
            logger.error(f"create_invoice error: {e}\n{traceback.format_exc()}")
            return {"ok": False, "error": repr(e)}

    async def transfer(
        self,
        user_id: int,
        amount: float,
        currency: str = "TON",
        comment: Optional[str] = None
    ) -> Dict:
        """Вывод средств пользователю"""
        params = {
            "user_id": user_id,
            "asset": currency,
            "amount": str(amount),
            "spend_id": str(uuid4()),
            "comment": comment
        }
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.base_url}/transfer",
                    params=params,
                    headers=self.headers
                ) as response:
                    data = await response.json()
                    logger.info(f"transfer response: {data}")
                    return data
        except Exception as e:
            logger.error(f"transfer error: {e}\n{traceback.format_exc()}")
            return {"ok": False, "error": repr(e)}

    async def check_invoice(self, invoice_id: str) -> Dict:
        """Проверка статуса инвойса"""
        params = {"invoice_ids": invoice_id}
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.base_url}/getInvoices",
                    params=params,
                    headers=self.headers
                ) as response:
                    data = await response.json()
                    logger.info(f"check_invoice response: {data}")
                    if not data.get("ok") or not isinstance(data.get("result"), list) or not data["result"]:
                        return {"ok": False, "error": "Invoice not found"}
                    return data
        except Exception as e:
            logger.error(f"check_invoice error: {e}\n{traceback.format_exc()}")
            return {"ok": False, "error": repr(e)}