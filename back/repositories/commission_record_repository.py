from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from ..database.models import InviteLinkTree, CommissionRecord, SettlementRecord
from ..schemas.commission import PageRequest
from typing import Tuple, List
from datetime import datetime

class CommissionRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    # 1. 总计链接创建数
    def get_total_link_count(self) -> int:
        return self.db.query(func.count(InviteLinkTree.link_code.distinct())).scalar()

    # 3. 当日产生的佣金金额
    def get_today_commission(self) -> float:
        today = datetime.today().date()
        result = self.db.query(func.round(func.sum(CommissionRecord.amount), 2)) \
                   .filter(func.date(CommissionRecord.created_at) == today) \
                   .scalar()
        return float(result) if result is not None else 0.0

    # 4. 当日已结算的佣金金额
    def get_today_settled_commission(self) -> float:
        today = datetime.today().date()
        result = self.db.query(func.round(func.sum(SettlementRecord.total_amount), 2)) \
                   .filter(func.date(SettlementRecord.completed_at) == today) \
                   .scalar()
        return float(result) if result is not None else 0.0

    # 5. 个人创建的链接列表（分页）
    def get_user_links(
        self, user_id: str, page_req: PageRequest
    ) -> Tuple[List[InviteLinkTree], int]:
        query = self.db.query(InviteLinkTree).filter(InviteLinkTree.inviter_id == user_id)
        # 关键字过滤（假设搜索link_code）
        if page_req.keyword:
            query = query.filter(InviteLinkTree.link_code.like(f'%{page_req.keyword}%'))
        # 时间范围过滤
        if page_req.start_date:
            query = query.filter(InviteLinkTree.created_at >= page_req.start_date)
        if page_req.end_date:
            query = query.filter(InviteLinkTree.created_at <= page_req.end_date)
        total = query.count()
        records = query.order_by(InviteLinkTree.created_at.desc()).offset((page_req.page - 1) * page_req.page_size).limit(page_req.page_size).all()
        return records, total

    # 6. 单条链接的佣金记录
    def get_link_commission_detail(self, link_code: str) -> dict:
        # 总佣金
        total = self.db.query(func.sum(CommissionRecord.amount)).filter(CommissionRecord.link_code == link_code).scalar() or 0.0
        # 已结算佣金
        settled = self.db.query(func.sum(SettlementRecord.total_amount)).join(CommissionRecord, SettlementRecord.id == CommissionRecord.settlement_id).filter(CommissionRecord.link_code == link_code).scalar() or 0.0
        return {
            'link_code': link_code,
            'total_commission': total,
            'settled_commission': settled,
            'unsettled_commission': total - settled
        }

    # 7. 所有链接信息（分页+关键字+时间）
    def get_all_links(
        self, page_req: PageRequest
    ) -> Tuple[List[dict], int]:
        # 子查询：统计每个链接的邀请人数
        invitee_count = self.db.query(
            InviteLinkTree.link_code,
            func.count(InviteLinkTree.invitee_id).label('invitee_count')
        ).group_by(InviteLinkTree.link_code).subquery()

        # 主查询：关联佣金和结算数据
        query = self.db.query(
            InviteLinkTree.link_code,
            InviteLinkTree.inviter_id,
            InviteLinkTree.created_at,
            invitee_count.c.invitee_count,
            func.sum(CommissionRecord.amount).label('total_commission'),
            func.sum(SettlementRecord.total_amount).label('settled_commission')
        ).outerjoin(CommissionRecord, InviteLinkTree.link_code == CommissionRecord.link_code).outerjoin(SettlementRecord, CommissionRecord.settlement_id == SettlementRecord.id).join(invitee_count, InviteLinkTree.link_code == invitee_count.c.link_code).group_by(InviteLinkTree.link_code, invitee_count.c.invitee_count)

        # 关键字过滤（link_code或inviter_id）
        if page_req.keyword:
            query = query.filter(
                or_(
                    InviteLinkTree.link_code.like(f'%{page_req.keyword}%'),
                    InviteLinkTree.inviter_id.like(f'%{page_req.keyword}%')
                )
            )
        # 时间范围过滤
        if page_req.start_date:
            query = query.filter(InviteLinkTree.created_at >= page_req.start_date)
        if page_req.end_date:
            query = query.filter(InviteLinkTree.created_at <= page_req.end_date)

        total = query.count()
        records = query.order_by(InviteLinkTree.created_at.desc()).offset((page_req.page - 1) * page_req.page_size).limit(page_req.page_size).all()
        # 转换为字典列表
        return [{
            'link_code': r.link_code,
            'inviter_id': r.inviter_id,
            'created_at': r.created_at,
            'invitee_count': r.invitee_count,
            'total_commission': r.total_commission or 0.0,
            'settled_commission': r.settled_commission or 0.0,
            'unsettled_commission': (r.total_commission or 0.0) - (r.settled_commission or 0.0)
        } for r in records], total

    def get_paginated_settlement_history(
        self, user_id: str, page: int, page_size: int
    ) -> Tuple[list, int]:
        # 单一职责：封装分页查询逻辑
        query = self.db.query(SettlementRecord).filter(SettlementRecord.user_id == user_id).order_by(SettlementRecord.created_at.desc())
        total = query.count()
        records = query.offset((page - 1) * page_size).limit(page_size).all()
        return records, total

    def get_available_commission(self, user_id: str) -> float:
        # 单一职责：仅负责数据查询
        return self.db.query(func.sum(CommissionRecord.amount)).filter(CommissionRecord.inviter_id == user_id).filter(CommissionRecord.is_settled == 0).scalar() or 0.0