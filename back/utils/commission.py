from sqlalchemy.orm import Session
from ..database.models import CommissionRecord, InviteLinkTree, CommissionConfig, CommissionRateHistory, User
from datetime import datetime

def calculate_commission(db: Session, invitee_id: str, order_amount: float, order_time: datetime, order_id: str = None):
    """计算佣金并创建佣金记录
    
    Args:
        db: 数据库会话
        invitee_id: 被邀请者ID
        order_amount: 订单金额
        order_time: 订单时间
        order_id: 订单ID（可选）
    
    Returns:
        List[CommissionRecord]: 创建的佣金记录列表
    """
    # 获取被邀请者的层级路径（递归查询父节点）
    current_node = db.query(InviteLinkTree).filter(InviteLinkTree.invitee_id == invitee_id).first()
    if not current_node:
        return []
    
    # 获取佣金配置
    base_rate_config = db.query(CommissionConfig).filter(CommissionConfig.key == 'base_rate').first()
    max_level_config = db.query(CommissionConfig).filter(CommissionConfig.key == 'max_level').first()
    
    if not base_rate_config or not max_level_config:
        raise ValueError('佣金配置不完整')
    
    # 安全地转换配置值为正确的类型
    try:
        base_rate = float(str(base_rate_config.value))
        max_level = int(str(max_level_config.value))
    except (ValueError, TypeError) as e:
        raise ValueError(f'配置值格式错误: {e}')
    
    # 验证配置值的有效性
    if base_rate < 0 or base_rate > 1:
        raise ValueError('基础佣金比例必须在0-1之间')
    if max_level < 1 or max_level > 10:
        raise ValueError('最大层级必须在1-10之间')
    
    level = 0
    records = []
    
    # 获取被邀请者信息
    invitee = db.query(User).filter(User.telegram_id == invitee_id).first()
    if not invitee:
        # 如果用户不存在，使用默认时间
        invitee_created_at = datetime.now()
    else:
        invitee_created_at = invitee.created_at
    
    # 从当前节点开始向上遍历父节点
    while current_node and level < max_level:
        # 上级邀请者ID
        inviter_id = current_node.inviter_id
        
        # 计算当前层级佣金（每层级递减10%）
        commission = order_amount * base_rate * (0.9 ** level)
        
        # 确定计算佣金的时间基准
        calculate_time = max(order_time, invitee_created_at)
        
        # 查询该时间点最近生效的佣金比例
        rate_record = db.query(CommissionRateHistory) \
                        .filter(CommissionRateHistory.effective_at <= calculate_time) \
                        .order_by(CommissionRateHistory.effective_at.desc()) \
                        .first()
        
        if not rate_record:
            raise ValueError('无有效的佣金比例配置')
        
        # 使用历史比例计算佣金
        used_rate = rate_record.rate
        
        # 确保所有必填字段都有值
        safe_order_id = str(order_id) if order_id is not None else f'ORDER_{datetime.now().strftime("%Y%m%d%H%M%S")}'
        safe_link_code = str(current_node.link_code) if current_node.link_code else f'LINK_{inviter_id}'
        
        # 创建佣金记录
        record = CommissionRecord(
            inviter_id=str(inviter_id),
            invitee_id=str(invitee_id),
            amount=round(commission, 2),
            order_id=safe_order_id,
            status='confirmed',
            used_rate=used_rate,
            link_code=safe_link_code,
            is_settled=0
        )
        records.append(record)
        
        # 向上查找父节点
        parent_node = db.query(InviteLinkTree).filter(InviteLinkTree.id == current_node.parent_id).first()
        current_node = parent_node
        level += 1
    
    if records:
        db.add_all(records)
        db.commit()
    
    return records