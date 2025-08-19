from sqlalchemy.orm import Session
from database.models import SettlementRecord  # 假设存在 SettlementRecord 模型

class SettlementRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: str):
        return self.db.query(SettlementRecord).filter(SettlementRecord.user_id == user_id).all()