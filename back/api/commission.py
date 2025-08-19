from ..main import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..main import app
from ..services.commission_service import CommissionService
from ..repositories.commission_record_repository import CommissionRecordRepository
from ..repositories.settlement_record_repository import SettlementRecordRepository 
from ..schemas.commission import (
    PageRequest, LinkStatsResponse, PageResponse, UserLinkResponse,
    LinkCommissionDetail, AllLinkInfoResponse, CommissionSettleRequest, CommissionSettleResponse
)

# 邀请链接统计路由
link_router = APIRouter(prefix='/link', tags=['邀请链接统计'])

# 佣金管理路由
commission_router = APIRouter(prefix='/commission', tags=['佣金管理'])

def get_commission_service(db: Session = Depends(get_db)):
    commission_repo = CommissionRecordRepository(db)
    settlement_repo = SettlementRecordRepository(db)
    return CommissionService(db, commission_repo, settlement_repo)  # 匹配构造函数参数顺序

# 1-4 统计接口
@link_router.get('/stats', response_model=LinkStatsResponse)
async def get_link_stats(service: CommissionService = Depends(get_commission_service)):
    return service.get_link_stats()

# 5. 个人创建的链接列表
@link_router.get('/user-links', response_model=PageResponse[UserLinkResponse])
async def get_user_links(
    user_id: str,
    page_req: PageRequest = Depends(),
    service: CommissionService = Depends(get_commission_service)
):
    return service.get_user_links(user_id, page_req)

# 6. 单条链接佣金详情
@link_router.get('/commission-detail/{link_code}', response_model=LinkCommissionDetail)
async def get_link_commission_detail(
    link_code: str,
    service: CommissionService = Depends(get_commission_service)
):
    return service.get_link_commission_detail(link_code)

# 7. 所有链接信息（分页）
@link_router.get('/all', response_model=PageResponse[AllLinkInfoResponse])
async def get_all_links(
    page_req: PageRequest = Depends(),
    service: CommissionService = Depends(get_commission_service)
):
    return service.get_all_links(page_req)

# 佣金结算接口
@commission_router.post('/settle', response_model=CommissionSettleResponse)
async def settle_commission(
    request: CommissionSettleRequest,
    service: CommissionService = Depends(get_commission_service)
):
    # 仅负责请求转发，业务逻辑由服务层处理
    result = service.settle_commission(user_id=request.user_id)
    return CommissionSettleResponse(**result)
