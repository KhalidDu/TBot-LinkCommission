from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from database.models import SettlementRecord, CommissionRecord

class CommissionStrategy(ABC):
    @abstractmethod
    def execute_settlement(self, user_id: str, available: float, db: Session) -> SettlementRecord:
        pass

# 示例：默认结算策略（直接标记已结算）
class DefaultSettlementStrategy(CommissionStrategy):
    def execute_settlement(self, user_id: str, available: float, db: Session) -> SettlementRecord:
        settlement = SettlementRecord(user_id=user_id, total_amount=available)
        db.add(settlement)
        db.flush()
        # 扩展点：未来可添加分润逻辑（如平台抽成）
        db.query(CommissionRecord) \
          .filter(CommissionRecord.inviter_id == user_id) \
          .filter(CommissionRecord.is_settled == 0) \
          .update({CommissionRecord.is_settled: 1})
        return settlement

# 示例：阶梯式结算
class StepSettlementStrategy(CommissionStrategy):
    def execute_settlement(self, user_id: str, available: float, db: Session) -> SettlementRecord:
        # 阶梯计算逻辑（如超过1000元部分额外奖励5%）
        # 这里需要实现具体的逻辑
        settlement = SettlementRecord(user_id=user_id, total_amount=available)
        db.add(settlement)
        db.flush()
        # 标记佣金为已结算
        db.query(CommissionRecord) \
          .filter(CommissionRecord.inviter_id == user_id) \
          .filter(CommissionRecord.is_settled == 0) \
          .update({CommissionRecord.is_settled: 1})
        return settlement

# 更新工厂函数
def get_commission_strategy(strategy_name: str) -> CommissionStrategy:
    strategies = {
        'default': DefaultSettlementStrategy(),
        'step': StepSettlementStrategy()  # 仅需添加新策略
    }
    return strategies.get(strategy_name, DefaultSettlementStrategy())