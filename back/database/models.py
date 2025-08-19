from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index, Boolean  # 新增Index导入
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
default=datetime.now

Base = declarative_base()

# 配置表（存储佣金比例、有效期等全局配置）
class CommissionConfig(Base):
    __tablename__ = 'commission_config'
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, comment='配置键（如\'base_rate\'）')
    value = Column(String(255), comment='配置值（如\'0.1\'表示10%佣金）')
    description = Column(String(255), comment='配置说明')
    created_at = Column(DateTime, default=datetime.now)

# 链接分享记录表（树结构，使用邻接表存储层级关系）
class InviteLinkTree(Base):
    __tablename__ = 'invite_link_tree'
    id = Column(Integer, primary_key=True, autoincrement=True)
    inviter_id = Column(String(50), comment='邀请者ID（Telegram用户ID）')
    invitee_id = Column(String(50), unique=True, comment='被邀请者ID（Telegram用户ID）')
    parent_id = Column(Integer, ForeignKey('invite_link_tree.id'), comment='父节点ID（层级关系）')
    link_code = Column(String(50), comment='邀请链接唯一码')
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_inviter_created', 'inviter_id', 'created_at'),  # 已修正：使用导入的Index类
        Index('idx_link_code', 'link_code', unique=True),
    )

# 结算记录表（用户主动发起的结算操作）
class SettlementRecord(Base):
    __tablename__ = 'settlement_records'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), index=True, comment='发起结算的用户ID')  # 修复重复定义
    amount = Column(Float)
    settled_at = Column(DateTime, default=datetime.utcnow)
    total_amount = Column(Float, comment='本次结算总金额')
    status = Column(String(20), default='processing', comment='状态（processing/completed/failed）')
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True, comment='完成时间')
    __table_args__ = (
        # 加速当日已结算统计（按completed_at过滤）
        Index('idx_completed_at', 'completed_at'),
    )

# 佣金比例历史表（记录每次管理员设置的比例及生效时间）
class CommissionRateHistory(Base):
    __tablename__ = 'commission_rate_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(String(50), comment='操作的管理员ID')
    rate = Column(Float, comment='设置的佣金比例（如0.01表示1%）')
    effective_at = Column(DateTime, default=datetime.now, comment='生效时间')
    created_at = Column(DateTime, default=datetime.now)
    description = Column(String(255), nullable=True, comment='备注说明')

# 佣金记录表
class CommissionRecord(Base):
    __tablename__ = 'commission_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    inviter_id = Column(String(50), comment='邀请者ID')
    invitee_id = Column(String(50), comment='被邀请者ID')
    amount = Column(Float, comment='佣金金额')
    order_id = Column(String(100), comment='关联订单ID')
    status = Column(String(20), default='pending', comment='状态（pending/confirmed）')
    created_at = Column(DateTime, default=datetime.now)
    is_settled = Column(Integer, default=0, comment='0-未结算，1-已结算')
    used_rate = Column(Float, comment='计算该笔佣金时使用的比例')
    link_code = Column(String(50), ForeignKey('invite_link_tree.link_code'), comment='关联邀请链接码')  # 新增外键字段
    __table_args__ = (
        # 加速当日佣金统计（按created_at过滤）
        Index('idx_created_at', 'created_at'),
        # 加速单链接佣金统计（按link_code过滤）
        Index('idx_link_code', 'link_code'),
    )

# 用户表
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String(50), unique=True, index=True, comment='Telegram用户ID')
    username = Column(String(100), nullable=True, comment='Telegram用户名')
    first_name = Column(String(100), nullable=True, comment='名字')
    last_name = Column(String(100), nullable=True, comment='姓氏')
    created_at = Column(DateTime, default=datetime.now, comment='注册时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    is_active = Column(Boolean, default=True, comment='是否激活')
    
    __table_args__ = (
        Index('idx_telegram_id', 'telegram_id'),
        Index('idx_created_at', 'created_at'),
    )