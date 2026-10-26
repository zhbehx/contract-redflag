#!/usr/bin/env python3
"""扫描租房/劳动合同的风险条款，指出「需要逐字看」的条目与「本该有但没有」的条款。

用法：
    python scripts/scan_contract.py contract.txt --type rent
    python scripts/scan_contract.py contract.txt --type labor --explain
    python scripts/scan_contract.py contract.txt --type rent --json
    python scripts/scan_contract.py contract.txt --type rent --fail-over 60

类型：rent（租房）/ labor（劳动）/ other（通用，只查通用条款）

退出码：0 正常；--fail-over 触发时 1；文件错误 2。

注意：本工具只做文本匹配，不构成法律意见。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# (正则, 级别, 类别, 风险点, 建议补充)
# 级别：H=高(扣15) M=中(扣7) L=提醒(扣3)
COMMON_RULES: list[tuple[str, str, str, str, str]] = [
    (r"及时(退还|返还|支付)|尽快(退还|返还|支付)|合理期限内", "H", "模糊表述",
     "没有可执行的时间标准，等于没有约定", "改成具体天数或工作日，如「3 个工作日内」"),
    (r"合理损耗|正常使用(的)?痕迹|保持整洁|保持良好", "M", "模糊表述",
     "标准由强势方单方解释", "列举具体情形，或直接删掉改为具体义务"),
    (r"另行(约定|协商)|双方(另行)?协商(确定|约定)|根据.{0,6}(需要|情况)调整", "H", "模糊表述",
     "把关键事项推给未来，届时你没有议价能力", "现在写清楚，或注明「未达成一致时不生效」"),
    (r"包括但不限于", "L", "模糊表述", "范围无边界", "保留可以，但要附一个已知清单"),
    (r"全部损失|一切(责任|后果|损失)由", "H", "违约与赔偿",
     "赔偿范围无边界", "限定为「因过错直接造成的实际损失，不含间接损失」"),
    (r"违约(金)?.{0,6}(30|三成|50)%|合同总额的\s*\d+%", "H", "违约与赔偿",
     "违约金比例偏高，可能被认定过高", "与实际损失挂钩，或设上限（如一个月租金/一个月工资）"),
    (r"滞纳金.{0,10}(日|每天).{0,6}(\d+(\.\d+)?%)|按日\s*\d+(\.\d+)?%", "H", "违约与赔偿",
     "日息标准可能远超法定上限", "改为日万分之五，或不超过 LPR 的 4 倍"),
    (r"单方(面)?(解除|终止|变更)|有权(随时|单方)(解除|收回|调整)", "H", "单方权利",
     "对方保留单方变更权，你的预期会被打破", "要求对等权利，或明确行使条件与补偿"),
]

RENT_RULES: list[tuple[str, str, str, str, str]] = [
    (r"押(金)?.{0,8}(不予|不)退还|押金不退", "H", "押金",
     "押金直接没收，可能远超实际损失", "明确扣款情形，违约金不超过一个月租金"),
    (r"扣除(相应|相关|部分)费用", "H", "押金",
     "「相应费用」没有标准，可任意扣", "「扣款项目及金额须经双方书面确认」"),
    (r"照价赔偿|按原价赔偿", "M", "押金", "「照价」由房东单方认定", "「按同期市场价或维修发票结算」"),
    (r"清洁费|保洁费", "M", "押金", "可能高于实际成本且标准模糊", "「按实际发生结算，最高不超过 X 元」"),
    (r"自动续租|自动顺延|期满(后)?(自动)?续", "H", "期限与续约",
     "想走时走不掉，可能被再锁一年", "「任一方可在到期前 30 日书面通知不续租」"),
    (r"提前(退租|解约).{0,10}(押金|不予|不退)", "H", "期限与续约",
     "解约成本可能等于全部押金", "「提前 30 日通知可解约，违约金不超过一个月租金」"),
    (r"甲方有权(提前)?收回|房东有权收回", "M", "单方权利",
     "房东可提前收房，无补偿", "「提前收回须提前 60 日通知并补偿一个月租金」"),
    (r"(甲方|房东)(有权|可)?(随时)?进入|开门|带人看房", "M", "单方权利",
     "可能未经通知进入房屋", "「进入须提前 24 小时通知并取得乙方同意」"),
    (r"维修.{0,6}(由)?乙方(负责|承担)|乙方负责维修", "H", "责任划分",
     "结构性问题也归你", "「主体结构及原有设施自然损坏由甲方维修」"),
    (r"(物业费|取暖费|供暖费).{0,6}(由)?乙方(承担|支付)", "M", "责任划分",
     "一年可能几千元，且未写金额", "明确各项费用金额与承担方"),
    (r"不得转租|禁止转租", "M", "期限与续约", "中途无法转手，工作变动时被动", "「经甲方书面同意可转租」"),
    (r"乙方(应)?(自行)?承担.{0,8}(水电|燃气|网络)", "L", "责任划分",
     "未写单价，可能被加价", "「按供水/供电/燃气公司标准单价结算」"),
]

LABOR_RULES: list[tuple[str, str, str, str, str]] = [
    (r"试用期.{0,10}(\d|[一二三四五六])个月", "L", "期限与续约",
     "需核对是否超过法定上限（3 年以上合同最长 6 个月）", "对照合同期限确认合法性"),
    (r"试用期.{0,12}(80%|八折|打八折|80％)", "M", "钱怎么发",
     "80% 是法定下限，不能再低", "确认不低于转正后 80%，且不低于当地最低工资"),
    (r"不(缴纳|缴|上)社保|社保(折现|补贴)|自愿放弃社保", "H", "钱怎么发",
     "违法，且会让你失去医疗/养老/买房资格", "要求按规定缴纳，不可折现"),
    (r"自愿放弃(加班费|社保|年假)", "H", "责任划分", "常见无效约定", "拒绝签署，保留工时证据"),
    (r"根据(公司)?(经营)?需要(调整|变更).{0,8}(岗位|薪资|工作地点)", "H", "单方权利",
     "变相调岗降薪", "「变更须双方协商一致并书面确认」"),
    (r"服从(公司)?(的)?(各项)?工作安排|完成(领导|上级)交办", "M", "单方权利",
     "工作内容无边界", "「工作内容以岗位说明书为准」"),
    (r"公司(有权)?(可)?单方(解除|终止).{0,10}(无需|不予)补偿", "H", "单方权利",
     "排除法定补偿义务", "明确列举解除情形，其余按法定标准补偿"),
    (r"竞业限制.{0,20}(\d|[一二])年|竞业(限制)?期", "M", "期限与续约",
     "需核对是否超过 2 年，以及是否有按月补偿", "「不超过 2 年，且按月支付补偿」"),
    (r"服务期.{0,10}(\d|[一二三四五])年|培训服务期", "M", "期限与续约",
     "服务期应与培训成本对应，需看培训费用凭证", "确认培训费用金额与凭证"),
    (r"违约金.{0,10}(万元|元)", "M", "违约与赔偿",
     "除培训服务期与竞业限制外，一般不得约定劳动者违约金", "要求删除或明确适用情形"),
    (r"加班.{0,10}(不计入|不视为|不另行)", "H", "责任划分", "排除加班认定，常见无效", "保留打卡与工作记录"),
    (r"工资(已)?包含加班费|包干工资", "M", "钱怎么发", "可能变相压低加班报酬", "确认基数与折算方式"),
]

# 缺失条款检查：(名称, 命中正则, 缺了会怎样, 建议补充)
MISSING_COMMON = [
    ("争议解决方式", r"仲裁|诉讼|管辖|法院",
     "出事时不知道该去哪主张，可能被迫去对方所在地", "「争议由合同履行地（房屋所在地 / 用人单位所在地）法院管辖」"),
    ("合同变更须书面", r"变更.{0,8}(书面|签订)|书面(变更|补充)",
     "口头承诺事后不认", "「本合同的变更须经双方书面确认」"),
    ("附件清单", r"附件|附表|确认单|清单",
     "附件没写进合同，事后可以说那不算", "列明附件并双方签字"),
]

MISSING_RENT = [
    ("押金退还期限", r"押金.{0,20}(退还|返还).{0,20}(日|工作日)|(\d+|三|五|七)\s*个?工作日内退还",
     "押金拖着不还你拿他没办法", "「验收合格后 3 个工作日内退还」"),
    ("租金调整机制", r"租金.{0,10}(调整|涨幅|不变)|涨幅.{0,6}\d+%",
     "房东可随时涨租", "「租期内租金不变；续租涨幅不超过 5%」"),
    ("提前解约条件", r"提前\s*(\d+|[一二三])?\s*(个)?月?.{0,6}(通知|解约)",
     "只能住满，或损失全部押金", "「提前 30 日通知可解约，违约金不超过一个月租金」"),
    ("维修责任划分", r"维修.{0,20}(甲方|房东|乙方)",
     "结构问题丢给你赔", "「主体结构自然损坏由甲方维修」"),
    ("房屋状况确认", r"确认单|状况(清单|确认)|交接(单|清单)",
     "退租时说你弄坏了本来坏的", "交房时共同签署状况确认单（含照片）"),
]

MISSING_LABOR = [
    ("工资发放日", r"(\d+|[一二三四五])\s*(日|号).{0,10}(发放|支付)工资|工资发放日",
     "可拖到月底甚至更久", "「每月 10 日前发放上月工资」"),
    ("工资构成", r"基本工资|绩效工资|补贴|工资构成",
     "说不清哪部分可扣，绩效可全扣", "列明基本/绩效/补贴各自金额"),
    ("社保公积金基数", r"(社保|公积金).{0,12}(基数|按.{0,6}缴纳)",
     "按最低基数缴，退休与买房受影响", "「按本人实际工资为基数缴纳」"),
    ("工时制度", r"工时|标准工时|综合计算|不定时",
     "加班是否算钱说不清", "「执行标准工时制，每日 8 小时」"),
    ("加班补偿方式", r"加班.{0,12}(调休|1\.5|2 倍|3 倍|加班费)",
     "只能调休不给钱", "明确 1.5/2/3 倍或调休规则"),
    ("竞业限制补偿", r"竞业.{0,20}(补偿|30%|按月支付)",
     "只有义务没有补偿，条款可能无效", "「按月支付离职前 12 个月平均工资的 30%」"),
]

LEVEL_PENALTY = {"H": 15, "M": 7, "L": 3}
LEVEL_LABEL = {"H": "高危", "M": "中危", "L": "提醒"}


def cjk_len(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def rules_for(kind: str) -> list[tuple[str, str, str, str, str]]:
    if kind == "rent":
        return COMMON_RULES + RENT_RULES
    if kind == "labor":
        return COMMON_RULES + LABOR_RULES
    return COMMON_RULES


def missing_for(kind: str) -> list[tuple[str, str, str, str]]:
    if kind == "rent":
        return MISSING_COMMON + MISSING_RENT
    if kind == "labor":
        return MISSING_COMMON + MISSING_LABOR
    return MISSING_COMMON


# 这些词出现在命中位置附近，说明该条款其实是在保护乙方（或已写清程序）
PROTECTIVE = re.compile(
    r"提前\s*\d+\s*(小时|日|天).{0,8}通知|提前通知|经.{0,6}书面同意|取得.{0,4}同意|除紧急情况"
)


def is_protective(text: str, pos: int) -> bool:
    """命中点前后 60 字内若有程序性保护表述，则不算风险。"""
    window = text[max(0, pos - 60): pos + 60]
    return bool(PROTECTIVE.search(window))


def snippet(text: str, pos: int, width: int = 26) -> str:
    """截取命中位置附近的原文，便于人工核对。"""
    start = max(0, pos - width // 3)
    return text[start:start + width].replace("\n", " ").strip()


def scan(text: str, kind: str) -> dict:
    raw: list[dict] = []
    for pattern, level, cat, risk, fix in rules_for(kind):
        for m in re.finditer(pattern, text, re.I):
            if is_protective(text, m.start()):
                continue
            raw.append({
                "clause": m.group(0),
                "snippet": snippet(text, m.start()),
                "level": level,
                "category": cat,
                "risk": risk,
                "fix": fix,
                "pos": m.start(),
                "end": m.end(),
            })

    # 同一段文字被多条规则命中时只留一条（保留级别最高的）
    raw.sort(key=lambda h: ({"H": 0, "M": 1, "L": 2}[h["level"]], -h["end"] + h["pos"]))
    hits: list[dict] = []
    for h in raw:
        if any(not (h["end"] <= x["pos"] or h["pos"] >= x["end"]) for x in hits):
            continue
        hits.append(h)
    hits.sort(key=lambda h: ({"H": 0, "M": 1, "L": 2}[h["level"]], h["pos"]))

    missing = [
        {"item": name, "consequence": cons, "suggest": sug}
        for name, pat, cons, sug in missing_for(kind)
        if not re.search(pat, text, re.I)
    ]

    penalty = sum(LEVEL_PENALTY[h["level"]] for h in hits) + len(missing) * 6
    score = min(100, penalty)

    if score >= 60:
        band = "风险偏高：签字前至少补 3 条，或换一份格式合同"
    elif score >= 30:
        band = "需要确认：把标出的条款逐条问清，缺的补上再签"
    else:
        band = "相对规范：仍要核对缺失条款与附件"

    return {
        "type": kind,
        "score": score,
        "band": band,
        "high": sum(1 for h in hits if h["level"] == "H"),
        "mid": sum(1 for h in hits if h["level"] == "M"),
        "low": sum(1 for h in hits if h["level"] == "L"),
        "hits": hits,
        "missing": missing,
        "cjk_chars": cjk_len(text),
        "disclaimer": "本结果由关键词规则生成，不构成法律意见；涉及金额较大或已发生争议请咨询律师或劳动仲裁机构。",
    }


DISCLAIMER = ("⚠️ 本工具只做关键词匹配，不构成法律意见。"
              "涉及金额较大或已发生争议的，请咨询律师或当地法律援助/劳动仲裁机构。")


def render(r: dict, explain: bool) -> str:
    out = [DISCLAIMER, ""]
    out.append(f"风险分：{r['score']}/100    {r['band']}")
    out.append(f"条款：高危 {r['high']} · 中危 {r['mid']} · 提醒 {r['low']}"
               f"   缺失 {len(r['missing'])} 条   （{r['cjk_chars']} 个汉字）")

    if r["hits"]:
        out.append("\n【需要逐字看的条款】")
        for h in r["hits"]:
            out.append(f"  [{LEVEL_LABEL[h['level']]}] 「{h['clause']}」")
            out.append(f"       原文：…{h['snippet']}…")
            if explain:
                out.append(f"       风险：{h['risk']}")
                out.append(f"       建议：{h['fix']}")

    if r["missing"]:
        out.append("\n【缺失条款（比写了什么更值得警惕）】")
        for m in r["missing"]:
            out.append(f"  - {m['item']}：{m['consequence']}")
            if explain:
                out.append(f"       建议补充：{m['suggest']}")

    if not explain:
        out.append("\n加 --explain 看每条的风险说明与建议补充文本。")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="扫描合同风险条款")
    ap.add_argument("file", help="合同文本文件")
    ap.add_argument("--type", choices=["rent", "labor", "other"], default="rent",
                    help="rent=租房（默认）/ labor=劳动 / other=只查通用条款")
    ap.add_argument("--explain", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-over", type=float, default=None, help="风险分超过该值时退出码 1")
    args = ap.parse_args(argv)

    p = Path(args.file)
    if not p.is_file():
        print(f"找不到文件：{p}", file=sys.stderr)
        return 2
    text = p.read_text(encoding="utf-8-sig")
    if cjk_len(text) < 50:
        print("合同文本太短（不足 50 个汉字），可能截断了；缺失条款会误报。", file=sys.stderr)
        return 2

    r = scan(text, args.type)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render(r, args.explain))

    if args.fail_over is not None and r["score"] > args.fail_over:
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:]))
