from fastapi import Depends
from .commission_service import CommissionService
from ..repositories import (get_commission_record_repo,
                             get_settlement_record_repo)

# 依赖函数：生成CommissionService实例
async def get_commission_service(
    commission_repo: CommissionRecordRepository = Depends(get_commission_record_repo),
    settlement_repo: SettlementRecordRepository = Depends(get_settlement_record_repo),
    db: Session = Depends(get_db)
):
    return CommissionService(
        db=db,
        commission_repo=commission_repo,
        settlement_repo=settlement_repo
    )