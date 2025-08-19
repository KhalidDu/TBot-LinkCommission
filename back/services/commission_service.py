from sqlalchemy.orm import Session
from ..repositories import CommissionRecordRepository, SettlementRecordRepository
from ..schemas.commission import PageRequest, LinkStatsResponse, UserLinkResponse, LinkCommissionDetail, AllLinkInfoResponse, PageResponse
from ..utils.commission_strategies import get_commission_strategy
from math import ceil

class CommissionService:
    def __init__(self,
                 db: Session,
                 commission_repo: CommissionRecordRepository,
                 settlement_repo: SettlementRecordRepository):
        self.db = db
        self.commission_repo = commission_repo
        self.settlement_repo = settlement_repo

    def settle_commission(self, user_id: str):
        # 职责：协调数据查询、策略计算、事务提交
        available = self.commission_repo.get_available_commission(user_id)
        if available <= 0:
            raise ValueError('无可用结算佣金')
        # 调用策略计算
        strategy = get_commission_strategy('default')
        settlement = strategy.execute_settlement(
            user_id=user_id,
            available=available,
            db=self.db
        )
        return {'settlement_id': settlement.id, 'amount': available}


    # 1-4 统计接口
    def get_link_stats(self) -> LinkStatsResponse:
        return LinkStatsResponse(
            total_created=self.commission_repo.get_total_link_count(),
            today_clicks=0,
            today_commission=self.commission_repo.get_today_commission(),
            today_settled=self.commission_repo.get_today_settled_commission()
        )

    # 5. 个人创建的链接列表
    def get_user_links(self, user_id: str, page_req: PageRequest) -> PageResponse[UserLinkResponse]:
        records, total = self.commission_repo.get_user_links(user_id, page_req)
        formatted = [UserLinkResponse(
            link_code=str(r.link_code),
            created_at=r.created_at,
            invitee_count=r.invitee_count,
            total_commission=r.total_commission,
            settled_commission=r.settled_commission,
            unsettled_commission=r.unsettled_commission
        ) for r in records]
        return PageResponse(
            data=formatted,
            total=total,
            page=page_req.page,
            page_size=page_req.page_size,
            total_pages=ceil(total / page_req.page_size)
        )

    # 6. 单条链接佣金详情
    def get_link_commission_detail(self, link_code: str) -> LinkCommissionDetail:
        detail = self.commission_repo.get_link_commission_detail(link_code)
        return LinkCommissionDetail(**detail)

    # 7. 所有链接信息（分页）
    def get_all_links(self, page_req: PageRequest) -> PageResponse[AllLinkInfoResponse]:
        records, total = self.commission_repo.get_all_links(page_req)
        return PageResponse(
            data=[AllLinkInfoResponse(**r) for r in records],
            total=total,
            page=page_req.page,
            page_size=page_req.page_size,
            total_pages=ceil(total / page_req.page_size)
        )