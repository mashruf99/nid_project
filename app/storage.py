#app/storage.py
import json
import os
from datetime import datetime, timezone
from filelock import FileLock

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATA_FILE = os.path.join(DATA_DIR, "data.json")


class StorageRepository:

     def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._lock = FileLock(DATA_FILE + ".lock")


     def _load(self) -> list:
        if not os.path.exists(DATA_FILE):
            return []

        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

     def _save(self, records: list):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

     def exists(self, nid_number: str) -> bool:
        records = self._load()

        return any(
            record.get("nidNumber") == nid_number
            for record in records
        )

     def save(self, data: dict):
        with self._lock:
            records = self._load()
            records.append({"extractedAt": datetime.now(timezone.utc).isoformat(), **data})
            self._save(records)



     def get(self, nid_number: str):  
        records = self._load()

        for record in records:
            if record.get("nidNumber") == nid_number:
                return record

        return None
 
     def update(self, nid_number: str, new_data: dict):
        with self._lock:
            records = self._load()
            for record in records:
                if record.get("nidNumber") == nid_number:
                    record.update(new_data)
                    self._save(records)
                    return True
            return False


repository = StorageRepository()