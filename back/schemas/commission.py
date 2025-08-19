from pydantic import BaseModel, constr, Field, Optional
from datetime import datetime
from typing import Generic, TypeVar, List

# 通用分页请求（已存在，此处补充扩展）
class PageRequest(BaseModel):
    page: int = 1
    page_size: int = 10
    keyword: Optional[str] = None  # 关键字查询
    start_date: Optional[datetime] = None  # 时间范围开始
    end_date: Optional[datetime] = None  # 时间范围结束

# 响应模型：链接统计摘要
class LinkStatsResponse(BaseModel):
    total_created: int  # 总计链接创建数
    today_clicks: int  # 当日点击数
    today_commission: float = Field(..., example=123.45)  # 当日产生佣金
    today_settled: float = Field(..., example=67.89)  # 当日已结算佣金

# 响应模型：个人创建的链接
class UserLinkResponse(BaseModel):
    link_code: str
    created_at: datetime
    invitee_count: int  # 该链接已邀请人数
    total_commission: float
    settled_commission: float
    unsettled_commission: float

# 响应模型：单条链接佣金详情
class LinkCommissionDetail(BaseModel):
    link_code: str
    total_commission: float
    settled_commission: float
    unsettled_commission: float
    records: List[dict]  # 具体佣金记录（简化示例）

# 响应模型：所有链接信息（分页）
class AllLinkInfoResponse(BaseModel):
    link_code: str
    inviter_id: str
    created_at: datetime
    invitee_count: int
    total_commission: float
    settled_commission: float
    unsettled_commission: float

# 请求模型：佣金结算
class CommissionSettleRequest(BaseModel):
    user_id: constr(min_length=1, max_length=50)  # 限制用户ID长度

# 响应模型：结算结果
class CommissionSettleResponse(BaseModel):
    settlement_id: int
    amount: float
    status: str = 'completed'
    created_at: datetime

# 扩展：佣金比例设置请求模型（管理员功能）
class CommissionRateSetRequest(BaseModel):
    rate: float
    description: str = ''

# 新增：通用分页响应（泛型）
from typing import Generic, TypeVar, List
T = TypeVar('T')
class PageResponse(BaseModel, Generic[T]):
    page: int
    page_size: int
    total: int
    total_pages: int
    data: List[T]