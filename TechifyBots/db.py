from typing import Any
from config import DB_URI, DB_NAME
from motor import motor_asyncio

client: motor_asyncio.AsyncIOMotorClient[Any] = motor_asyncio.AsyncIOMotorClient(DB_URI)
db = client[DB_NAME]

_BOTS_DOC_ID = 0  # sentinel user_id for the extra-bots config document

class Techifybots:
    def __init__(self):
        self.users = db["users"]
        # NOTE: we intentionally do NOT create a separate "extra_bots" collection.
        # Extra bot tokens are stored inside the existing "users" collection as a
        # special document with user_id=0. This avoids Atlas "cannot create collection"
        # auth errors that occur when the DB user lacks collection-creation rights.
        self.cache: dict[int, dict[str, Any]] = {}

    async def add_user(self, user_id: int, name: str) -> dict[str, Any] | None:
        try:
            user: dict[str, Any] = {"user_id": user_id, "name": name, "session": None}
            await self.users.insert_one(user)
            self.cache[user_id] = user
            return user
        except Exception as e:
            print("Error in add_user:", e)

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        try:
            if user_id in self.cache:
                return self.cache[user_id]
            user = await self.users.find_one({"user_id": user_id})
            if user:
                self.cache[user_id] = user
            return user
        except Exception as e:
            print("Error in get_user:", e)
            return None

    async def set_session(self, user_id: int, session: Any) -> bool:
        try:
            result = await self.users.update_one(
                {"user_id": user_id},
                {"$set": {"session": session}}
            )
            if user_id in self.cache:
                self.cache[user_id]["session"] = session
            return result.modified_count > 0
        except Exception as e:
            print("Error in set_session:", e)
            return False

    async def get_session(self, user_id: int) -> Any | None:
        try:
            user = await self.get_user(user_id)
            return user.get("session") if user else None
        except Exception as e:
            print("Error in get_session:", e)
            return None

    async def get_all_users(self) -> list[dict[str, Any]]:
        try:
            users: list[dict[str, Any]] = []
            async for user in self.users.find():
                users.append(user)
            return users
        except Exception as e:
            print("Error in get_all_users:", e)
            return []

    async def delete_user(self, user_id: int) -> bool:
        try:
            result = await self.users.delete_one({"user_id": user_id})
            self.cache.pop(user_id, None)
            return result.deleted_count > 0
        except Exception as e:
            print("Error in delete_user:", e)
            return False

    # ── Extra bot management (stored in "users" collection, user_id=0) ──────────

    async def _get_bots_doc(self) -> dict[str, Any]:
        doc = await self.users.find_one({"user_id": _BOTS_DOC_ID})
        if doc is None:
            return {"user_id": _BOTS_DOC_ID, "bots": []}
        return doc

    async def upsert_extra_bot(self, token: str, username: str) -> str | None:
        """
        Add or update an extra bot token in the existing users collection.
        Returns None on success, or an error string on failure.
        """
        try:
            doc = await self._get_bots_doc()
            bots: list[dict[str, Any]] = doc.get("bots", [])

            # Update username if token already exists
            for b in bots:
                if b.get("token") == token:
                    b["username"] = username
                    break
            else:
                bots.append({"token": token, "username": username})

            await self.users.update_one(
                {"user_id": _BOTS_DOC_ID},
                {"$set": {"user_id": _BOTS_DOC_ID, "bots": bots}},
                upsert=True
            )
            return None
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            print("Error in upsert_extra_bot:", err)
            return err

    async def remove_extra_bot(self, token: str) -> bool:
        try:
            doc = await self._get_bots_doc()
            bots: list[dict[str, Any]] = doc.get("bots", [])
            new_bots = [b for b in bots if b.get("token") != token]
            if len(new_bots) == len(bots):
                return False  # token not found
            await self.users.update_one(
                {"user_id": _BOTS_DOC_ID},
                {"$set": {"bots": new_bots}},
                upsert=True
            )
            return True
        except Exception as e:
            print("Error in remove_extra_bot:", e)
            return False

    async def get_all_extra_bots(self) -> list[dict[str, Any]]:
        try:
            doc = await self._get_bots_doc()
            return doc.get("bots", [])
        except Exception as e:
            print("Error in get_all_extra_bots:", e)
            return []

tb = Techifybots()
