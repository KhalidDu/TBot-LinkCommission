from fastapi import FastAPI
from sqlalchemy.orm import Session  # 新增：导入 Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, CommissionConfig, InviteLinkTree, CommissionRecord
from fastapi import Depends, HTTPException
from utils.commission import calculate_commission
from sqlalchemy import func
from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging
import traceback

app = FastAPI()

# 配置SQLite数据库（自动创建db文件在back目录下）
DATABASE_URL = 'sqlite:///./back.db'
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有表（首次运行时执行）
Base.metadata.create_all(bind=engine)

# 示例路由：获取佣金配置
@app.get('/commission/config/{key}')
async def get_commission_config(key: str, db: Depends[get_db]):
    db = SessionLocal()
    config = db.query(CommissionConfig).filter(CommissionConfig.key == key).first()
    db.close()
    return {'key': config.key, 'value': config.value} if config else {'error': '配置不存在'}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import uuid

@app.post('/invite/generate')
async def generate_invite_link(inviter_id: str, db: Session = Depends(get_db)):
    # 生成唯一邀请码（简化示例，实际可使用更短的哈希）
    link_code = str(uuid.uuid4())[:8]
    # 检查邀请者是否已存在（可选）
    existing_inviter = db.query(InviteLinkTree).filter(InviteLinkTree.inviter_id == inviter_id).first()
    if not existing_inviter:
        # 根节点（无父节点）
        new_node = InviteLinkTree(inviter_id=inviter_id, invitee_id=inviter_id, link_code=link_code, parent_id=None)
        db.add(new_node)
        db.commit()
    return {'link_code': link_code, 'url': f'https://your-domain.com/register?code={link_code}'}

@app.post('/register')
async def user_register(invitee_id: str, link_code: str, db: Session = Depends(get_db)):
    # 查找邀请码对应的邀请者
    inviter_node = db.query(InviteLinkTree).filter(InviteLinkTree.link_code == link_code).first()
    if not inviter_node:
        raise HTTPException(status_code=400, detail='无效的邀请码')
    # 检查被邀请者是否已存在
    existing_invitee = db.query(InviteLinkTree).filter(InviteLinkTree.invitee_id == invitee_id).first()
    if existing_invitee:
        raise HTTPException(status_code=400, detail='用户已注册')
    # 创建新节点（父节点为邀请者的id）
    new_node = InviteLinkTree(
        inviter_id=inviter_node.inviter_id,
        invitee_id=invitee_id,
        link_code=link_code,
        parent_id=inviter_node.id
    )
    db.add(new_node)
    db.commit()
    return {'message': '注册成功，邀请关系已记录'}


@app.post('/order/complete')
async def complete_order(invitee_id: str, order_amount: float, db: Session = Depends(get_db)):
    records = calculate_commission(db, invitee_id, order_amount)
    return {'message': '佣金已结算', 'records': [{'inviter_id': r.inviter_id, 'amount': r.amount} for r in records]}


@app.get('/commission/available')
async def get_available_commission(user_id: str, db: Session = Depends(get_db)):
    # 查询所有该用户作为邀请者、未结算的佣金
    available = db.query(func.sum(CommissionRecord.amount))\
                   .filter(CommissionRecord.inviter_id == user_id)\
                   .filter(CommissionRecord.is_settled == 0)\
                   .scalar()
    return {'user_id': user_id, 'available_amount': available or 0.0}

@app.post('/commission/settle')
async def settle_commission(user_id: str, db: Session = Depends(get_db)):
    # 1. 查询可结算的佣金总额
    available_amount = db.query(func.sum(CommissionRecord.amount))\
                         .filter(CommissionRecord.inviter_id == user_id)\
                         .filter(CommissionRecord.is_settled == 0)\
                         .scalar()
    if not available_amount or available_amount <= 0:
        raise HTTPException(status_code=400, detail='无可用结算的佣金')

    # 2. 开启事务（确保原子性）
    try:
        # 3. 创建结算记录
        settlement = SettlementRecord(
            user_id=user_id,
            total_amount=available_amount,
            status='processing'
        )
        db.add(settlement)
        db.flush()  # 获取刚插入的settlement.id

        # 4. 标记关联的佣金为已结算
        db.query(CommissionRecord)\
          .filter(CommissionRecord.inviter_id == user_id)\
          .filter(CommissionRecord.is_settled == 0)\
          .update({CommissionRecord.is_settled: 1})

        # 5. 模拟结算完成（实际可对接支付系统，这里简化为直接标记完成）
        settlement.status = 'completed'
        settlement.completed_at = datetime.now()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'结算失败：{str(e)}')

    return {'message': '结算成功', 'settlement_id': settlement.id, 'amount': available_amount}

@app.get('/commission/settlement/history', response_model=PageResponse[CommissionSettleResponse])
async def get_settlement_history(
    user_id: str,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    # 计算总条数
    total = db.query(SettlementRecord)
              .filter(SettlementRecord.user_id == user_id)
              .count()
    # 分页查询
    records = db.query(SettlementRecord)
                .filter(SettlementRecord.user_id == user_id)
                .order_by(SettlementRecord.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
    # 转换响应数据
    formatted_records = [{
        'settlement_id': r.id,
        'amount': r.total_amount,
        'status': r.status,
        'created_at': r.created_at,
        'completed_at': r.completed_at
    } for r in records]
    return PageResponse(
        data=formatted_records,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@app.post('/admin/commission/rate')
async def set_commission_rate(
    admin_id: str,
    rate: float,
    description: str = '',
    db: Session = Depends(get_db)
):
    if rate <= 0 or rate > 1:
        raise HTTPException(status_code=400, detail='比例需在(0,1]范围内')
    # 记录历史
    new_rate = CommissionRateHistory(
        admin_id=admin_id,
        rate=rate,
        description=description
    )
    db.add(new_rate)
    db.commit()
    return {'message': '佣金比例设置成功', 'rate': rate, 'effective_at': new_rate.effective_at}


@app.get('/admin/commission/rate/history')
async def get_commission_rate_history(
    admin_id: str = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(CommissionRateHistory)
    if admin_id:
        query = query.filter(CommissionRateHistory.admin_id == admin_id)
    # 按生效时间倒序排序
    records = query.order_by(CommissionRateHistory.effective_at.desc())
                  .offset((page - 1) * page_size)
                  .limit(page_size)
                  .all()
    return [{
        'id': r.id,
        'admin_id': r.admin_id,
        'rate': r.rate,
        'effective_at': r.effective_at.strftime('%Y-%m-%d %H:%M:%S'),
        'description': r.description
    } for r in records]


# 初始化日志配置（添加在main.py顶部）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('app.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 添加全局异常处理中间件（在app初始化后）
@app.middleware('http')
async def global_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # 记录完整异常堆栈
        error_trace = traceback.format_exc()
        logger.error(f'全局异常捕获：{str(e)}{error_trace}')
        # 返回标准化错误响应
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                'code': 500,
                'message': '服务器内部错误',
                'detail': str(e),
                'timestamp': datetime.now().isoformat()
            }
        )
