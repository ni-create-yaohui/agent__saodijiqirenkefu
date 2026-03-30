# -*- coding: utf-8 -*-
"""
客服业务工具模块 - 提供订单查询、产品推荐、故障诊断等客服相关功能
"""

import json
from datetime import datetime
from langchain_core.tools import tool
from project.logger_handler import logger
from project.path_tool import get_abs_path


# 加载产品数据
_products_data = None
_usage_data = None


def _load_products_data():
    """加载产品数据"""
    global _products_data
    if _products_data is None:
        try:
            products_file = get_abs_path("data/products.json")
            with open(products_file, 'r', encoding='utf-8') as f:
                _products_data = json.load(f)
        except FileNotFoundError:
            _products_data = _get_default_products()
    return _products_data


def _get_default_products():
    """默认产品数据"""
    return {
        "扫地机器人": [
            {
                "model": "追觅S10",
                "price": 2999,
                "features": ["4000Pa吸力", "激光导航", "自动集尘", "3D结构光避障"],
                "suitable_for": "中大户型家庭，需要全面清洁",
                "rating": 4.8
            },
            {
                "model": "石头P10",
                "price": 3299,
                "features": ["5500Pa吸力", "AI避障", "自动洗拖布", "热风烘干"],
                "suitable_for": "注重拖地效果的家庭",
                "rating": 4.9
            },
            {
                "model": "科沃斯T20",
                "price": 3999,
                "features": ["6000Pa吸力", "TrueDetect 3D", "自动补水", "全能基站"],
                "suitable_for": "高端用户，追求极致体验",
                "rating": 4.7
            }
        ],
        "扫拖一体机器人": [
            {
                "model": "追觅X30",
                "price": 4999,
                "features": ["7000Pa吸力", "仿生机械臂", "自动上下水", "双轮增压拖布"],
                "suitable_for": "大户型，追求深度清洁",
                "rating": 4.9
            },
            {
                "model": "石头G10S Pure",
                "price": 3999,
                "features": ["5100Pa吸力", "声波震动擦地", "自动抬升拖布", "抗菌拖布"],
                "suitable_for": "有地毯的家庭",
                "rating": 4.8
            }
        ],
        "手持吸尘器": [
            {
                "model": "追觅V16",
                "price": 2499,
                "features": ["210AW吸入功率", "85分钟续航", "5重过滤", "多种吸头"],
                "suitable_for": "需要灵活清洁的用户",
                "rating": 4.7
            }
        ]
    }


def _load_usage_data():
    """加载使用记录数据"""
    global _usage_data
    if _usage_data is None:
        _usage_data = {}
        try:
            import csv
            csv_path = get_abs_path("data/external/records.csv")
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    user_id = row['用户ID']
                    month = row['时间']
                    if user_id not in _usage_data:
                        _usage_data[user_id] = {}
                    _usage_data[user_id][month] = {
                        "特征": row['特征'],
                        "清洁效率": row['清洁效率'],
                        "耗材": row['耗材'],
                        "对比": row['对比']
                    }
        except Exception as e:
            logger.error(f"加载使用数据失败: {e}")
    return _usage_data


@tool(description="根据用户需求推荐适合的扫地机器人或扫拖一体机器人产品。参数budget为预算范围(如'2000-3000')，house_size为房屋面积，floor_type为地面类型，has_pet为是否有宠物，need_mop为是否需要拖地功能")
def recommend_product(budget: str = "", house_size: str = "", floor_type: str = "",
                      has_pet: bool = False, need_mop: bool = False) -> str:
    """
    产品推荐工具
    """
    products = _load_products_data()

    # 确定产品类别
    category = "扫拖一体机器人" if need_mop else "扫地机器人"

    candidates = products.get(category, [])

    # 添加手持吸尘器作为备选
    candidates.extend(products.get("手持吸尘器", []))

    if not candidates:
        return "抱歉，暂时没有找到合适的产品推荐"

    # 筛选逻辑
    recommendations = []
    for product in candidates:
        score = 0
        reasons = []

        # 预算匹配
        if budget:
            try:
                min_budget, max_budget = map(int, budget.split('-'))
                if min_budget <= product['price'] <= max_budget:
                    score += 3
                    reasons.append(f"价格{product['price']}元在预算范围内")
            except:
                pass

        # 面积匹配
        if house_size:
            size = int(house_size.replace('㎡', '').replace('平', ''))
            if size > 100 and product['price'] > 3000:
                score += 2
                reasons.append("大户型适用")
            elif size < 80 and product['price'] < 3500:
                score += 2
                reasons.append("小户型性价比高")

        # 地面类型匹配
        if floor_type:
            if '地毯' in floor_type and '增压' in str(product['features']):
                score += 2
                reasons.append("支持地毯增压")
            if '木地板' in floor_type or '大理石' in floor_type:
                score += 1

        # 宠物匹配
        if has_pet:
            if any('毛发' in f or '防缠绕' in f for f in product['features']):
                score += 2
                reasons.append("适合养宠家庭")

        recommendations.append({
            "product": product,
            "score": score,
            "reasons": reasons
        })

    # 按评分排序
    recommendations.sort(key=lambda x: x['score'], reverse=True)

    # 生成推荐结果
    result = "根据您的需求，为您推荐以下产品：\n\n"
    for i, rec in enumerate(recommendations[:3], 1):
        p = rec['product']
        result += f"【推荐{i}】{p['model']}\n"
        result += f"💰 价格：{p['price']}元\n"
        result += f"⭐ 评分：{p['rating']}/5.0\n"
        result += f"🎯 适用场景：{p['suitable_for']}\n"
        result += f"🔧 核心功能：{', '.join(p['features'][:3])}\n"
        if rec['reasons']:
            result += f"✅ 推荐理由：{', '.join(rec['reasons'])}\n"
        result += "\n"

    return result


@tool(description="诊断扫地机器人常见故障并提供解决方案。参数symptom为故障现象描述")
def diagnose_fault(symptom: str) -> str:
    """
    故障诊断工具
    """
    # 故障知识库
    fault_solutions = {
        "不工作": {
            "可能原因": ["电池没电", "电源开关未开启", "卡在障碍物中", "APP设置为勿扰模式"],
            "解决方案": [
                "检查电量，放回充电座充电30分钟以上",
                "确认电源开关已开启（通常在侧面或底部）",
                "检查是否卡在床底、沙发底部，手动移出",
                "打开APP检查勿扰时段设置"
            ]
        },
        "不充电": {
            "可能原因": ["充电座电源未接通", "充电触点脏污", "充电座位置不当", "电池老化"],
            "解决方案": [
                "检查充电座电源指示灯是否亮起",
                "用干布清洁机器人和充电座的充电触点",
                "确保充电座周围0.5米内无障碍物",
                "如使用超过2年，可能需要更换电池"
            ]
        },
        "清扫不干净": {
            "可能原因": ["尘盒已满", "吸力设置过低", "主刷缠绕异物", "滤网堵塞"],
            "解决方案": [
                "清空尘盒，建议每次清扫后清理",
                "在APP中将吸力调至标准或强力模式",
                "检查主刷，清理缠绕的头发、线头",
                "清洗或更换HEPA滤网"
            ]
        },
        "找不到充电座": {
            "可能原因": ["充电座位置移动", "信号被遮挡", "充电座附近有镜面反射物"],
            "解决方案": [
                "充电座位置固定后不要随意移动",
                "确保充电座前方1.5米、左右0.5米无遮挡",
                "避免将充电座放在镜子、玻璃门附近"
            ]
        },
        "拖地漏水": {
            "可能原因": ["水箱未正确安装", "拖布安装不当", "水箱损坏", "水管堵塞"],
            "解决方案": [
                "重新安装水箱，确保卡扣锁紧",
                "正确安装拖布支架",
                "检查水箱是否有裂缝",
                "清理水箱出水口和管路"
            ]
        },
        "噪音大": {
            "可能原因": ["主刷缠绕异物", "边刷变形或缠绕", "风扇叶轮积灰", "机器老化"],
            "解决方案": [
                "清理主刷缠绕的头发、线头",
                "检查边刷是否变形，必要时更换",
                "打开上盖清理风扇叶轮灰尘",
                "如使用时间长，考虑更换主刷或边刷"
            ]
        },
        "避障失效": {
            "可能原因": ["传感器脏污", "环境光线太暗", "障碍物过高或过低", "软件版本过旧"],
            "解决方案": [
                "用软布清洁所有传感器（悬崖传感器、沿墙传感器等）",
                "在光线充足的环境使用",
                "注意：高度低于5cm的障碍物可能无法识别",
                "更新APP和机器固件到最新版本"
            ]
        },
        "离线": {
            "可能原因": ["WiFi信号弱", "路由器问题", "机器距离路由器太远"],
            "解决方案": [
                "将充电座移近路由器",
                "重启路由器",
                "重置WiFi连接（长按重置按钮3-5秒）",
                "确认使用2.4GHz网络（不支持5GHz）"
            ]
        }
    }

    symptom_lower = symptom.lower()

    # 匹配故障
    matched_key = None
    for key in fault_solutions.keys():
        if key in symptom_lower or any(k in symptom_lower for k in key.split('/')):
            matched_key = key
            break

    if not matched_key:
        # 模糊匹配
        for key in fault_solutions.keys():
            if any(word in symptom_lower for word in ['不工作', '不动', '停']):
                matched_key = '不工作'
                break
            elif any(word in symptom_lower for word in ['充不进', '充不上', '不充电']):
                matched_key = '不充电'
                break
            elif any(word in symptom_lower for word in ['扫不干净', '吸力', '漏扫']):
                matched_key = '清扫不干净'
                break
            elif any(word in symptom_lower for word in ['噪音', '声音大', '响']):
                matched_key = '噪音大'
                break
            elif any(word in symptom_lower for word in ['找不到', '回不去', '迷路']):
                matched_key = '找不到充电座'
                break
            elif any(word in symptom_lower for word in ['漏水', '出水', '拖地']):
                matched_key = '拖地漏水'
                break
            elif any(word in symptom_lower for word in ['撞', '碰', '避障']):
                matched_key = '避障失效'
                break
            elif any(word in symptom_lower for word in ['离线', '连不上', '网络']):
                matched_key = '离线'
                break

    if matched_key:
        solution = fault_solutions[matched_key]
        result = f"""🔧 故障诊断结果：{matched_key}

【可能原因】
{chr(10).join(f'• {c}' for c in solution['可能原因'])}

【解决方案】
{chr(10).join(f'{i+1}. {s}' for i, s in enumerate(solution['解决方案']))}

💡 温馨提示：如果以上方法无法解决问题，请联系售后客服获取进一步帮助。"""
        return result

    return f"""未能识别您描述的故障现象：「{symptom}」

请您更详细地描述问题，例如：
• 机器完全不工作
• 无法充电
• 清扫效果不好
• 噪音异常
• 找不到充电座
• 拖地功能异常

您也可以直接描述具体情况，我会尽力帮您解决。"""


@tool(description="根据扫地机器人使用情况提供保养和维护建议。参数usage_months为使用月数，device_model为设备型号，issues为遇到的问题列表")
def maintenance_advice(usage_months: int = 0, device_model: str = "", issues: str = "") -> str:
    """
    保养建议工具
    """
    advice = []

    # 基于使用时长的建议
    if usage_months >= 12:
        advice.append("⏰ 您的设备已使用超过1年，建议进行以下保养：")
        advice.append("• 检查主刷是否磨损严重，考虑更换")
        advice.append("• 更换HEPA滤网（建议6-12个月更换一次）")
        advice.append("• 检查电池健康度，续航明显下降需更换")
        advice.append("• 清洁所有传感器和充电触点")
    elif usage_months >= 6:
        advice.append("📅 您的设备已使用半年，建议进行以下保养：")
        advice.append("• 清洗或更换滤网")
        advice.append("• 检查边刷是否变形")
        advice.append("• 清洁主刷和轴承")
    elif usage_months >= 3:
        advice.append("✨ 日常保养建议：")
        advice.append("• 定期清空尘盒")
        advice.append("• 清理主刷缠绕物")
        advice.append("• 擦拭传感器")

    # 基于问题的建议
    if issues:
        if '毛发' in issues or '缠绕' in issues:
            advice.append("\n🐾 针对毛发缠绕问题：")
            advice.append("• 建议使用防缠绕主刷（胶刷）")
            advice.append("• 每2-3天检查一次主刷")
            advice.append("• 可配备自动集尘座减少清理频率")

        if '续航' in issues or '电量' in issues:
            advice.append("\n🔋 针对续航问题：")
            advice.append("• 避免频繁启动，让机器一次完成清扫")
            advice.append("• 确保充电座位置通风良好")
            advice.append("• 如使用超过2年，考虑更换电池")

        if '拖地' in issues or '水箱' in issues:
            advice.append("\n💧 针对拖地功能：")
            advice.append("• 每次使用后清洗拖布并晾干")
            advice.append("• 定期清洁水箱防止水垢")
            advice.append("• 使用专用清洁液效果更佳")

    # 通用保养计划
    advice.append("\n📋 建议保养计划：")
    advice.append("• 每日：清空尘盒、检查主刷")
    advice.append("• 每周：清洗滤网、清洁边刷")
    advice.append("• 每月：深度清洁传感器、检查轮胎")
    advice.append("• 每季度：更换滤网、检查耗材")

    return "\n".join(advice)


@tool(description="查询用户设备的使用记录和统计数据。参数user_id为用户ID，month为查询月份(格式YYYY-MM)，如不指定则查询最新记录")
def query_usage_record(user_id: str, month: str = "") -> str:
    """
    使用记录查询工具
    """
    usage_data = _load_usage_data()

    if user_id not in usage_data:
        return f"未找到用户 {user_id} 的使用记录。请确认用户ID是否正确。"

    user_records = usage_data[user_id]

    if month:
        if month not in user_records:
            available_months = list(user_records.keys())
            return f"未找到 {month} 的记录。可用月份：{', '.join(sorted(available_months)[-5:])}"
        record = user_records[month]
    else:
        # 获取最新记录
        latest_month = sorted(user_records.keys())[-1]
        record = user_records[latest_month]
        month = latest_month

    result = f"""📊 用户 {user_id} 的使用记录（{month}）

【家庭特征】
{record['特征']}

【清洁效率】
{record['清洁效率']}

【耗材状态】
{record['耗材']}

【对比分析】
{record['对比']}
"""
    return result


@tool(description="获取当前月份的标准格式字符串，如2025-03")
def get_current_month() -> str:
    """获取当前月份"""
    return datetime.now().strftime("%Y-%m")


@tool(description="查询订单物流状态。参数order_id为订单编号")
def query_order(order_id: str) -> str:
    """
    订单查询工具（模拟）
    """
    # 模拟订单数据
    mock_orders = {
        "D20250301001": {
            "status": "已签收",
            "product": "追觅S10扫地机器人",
            "delivery_date": "2025-03-05",
            "tracking": "SF1234567890"
        },
        "D20250315002": {
            "status": "运输中",
            "product": "石头P10 Pro扫拖一体机",
            "delivery_date": "预计2025-03-20",
            "tracking": "YT9876543210"
        }
    }

    if order_id in mock_orders:
        order = mock_orders[order_id]
        return f"""📦 订单查询结果

订单编号：{order_id}
商品名称：{order['product']}
订单状态：{order['status']}
{'预计' if '预计' in order['delivery_date'] else ''}送达时间：{order['delivery_date']}
物流单号：{order['tracking']}

💡 如需更多帮助，请联系人工客服。"""
    else:
        return f"""未找到订单 {order_id}

请检查订单号是否正确，或联系客服查询。
订单号通常以 D 开头，如：D20250301001"""


@tool(description="获取耗材更换提醒和购买建议。参数device_model为设备型号，usage_months为使用月数")
def consumable_reminder(device_model: str = "", usage_months: int = 0) -> str:
    """
    耗材提醒工具
    """
    reminders = []

    # 根据使用时间给出建议
    if usage_months >= 6:
        reminders.append({
            "name": "HEPA滤网",
            "status": "⚠️ 建议更换",
            "reason": "使用超过6个月，过滤效果下降",
            "price": "39-79元"
        })

    if usage_months >= 3:
        reminders.append({
            "name": "边刷",
            "status": "⚠️ 建议检查",
            "reason": "使用超过3个月，可能变形或磨损",
            "price": "19-39元/个"
        })

    if usage_months >= 12:
        reminders.append({
            "name": "主刷",
            "status": "⚠️ 建议更换",
            "reason": "使用超过1年，刷毛可能老化",
            "price": "79-149元"
        })
        reminders.append({
            "name": "电池",
            "status": "⚠️ 建议检测",
            "reason": "使用超过1年，续航可能下降",
            "price": "199-399元"
        })

    # 通用耗材提醒
    reminders.append({
        "name": "拖布",
        "status": "定期更换",
        "reason": "建议1-2个月更换或深度清洗",
        "price": "29-59元/组"
    })
    reminders.append({
        "name": "清洁液",
        "status": "常备",
        "reason": "拖地功能必需，建议常备",
        "price": "29-49元/瓶"
    })

    result = "🔧 耗材状态提醒\n\n"
    for r in reminders:
        result += f"【{r['name']}】\n"
        result += f"  状态：{r['status']}\n"
        result += f"  说明：{r['reason']}\n"
        result += f"  参考价格：{r['price']}\n\n"

    result += "💡 提示：建议通过官方渠道购买耗材，确保质量和兼容性。"

    return result