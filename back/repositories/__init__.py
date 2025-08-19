from sqlalchemy.orm import Session
from .commission_record_repository import CommissionRecordRepository
from .settlement_record_repository import SettlementRecordRepository

# 依赖函数：生成CommissionRecordRepository实例
async def get_commission_record_repo(db: Session = Depends(get_db)):
    return CommissionRecordRepository(db)

# 依赖函数：生成SettlementRecordRepository实例
async def get_settlement_record_repo(db: Session = Depends(get_db)):
    return SettlementRecordRepository(db)