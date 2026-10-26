# 推广素材：合同风险扫描

> 租房合同里哪几条要逐字看、哪些本该有却没写。

下面每条文案都用本仓脚本测过 AI 味。

---

## 一、GitHub 仓库元信息

**About**：见仓库设置（已由发布脚本写入）。

**Social preview**：`market/social-preview.png`（1280×640，已生成）。


---

## 二、小红书

**标题（5 选 1）**

1. 签租房合同前，请一定逐字看这 6 条
2. 我的押金是怎么没的：一句话的事
3. 合同不怕它写了什么，怕它没写什么
4. 中介给的模板，我只改了 3 句话
5. 打工人必看：劳动合同里这 5 条最坑

**正文**

去年退租，押金没退回来。

合同上写的是「租赁期满，乙方结清费用并将房屋交还甲方后，押金于退租时退还」。

看起来挺正常对吧？问题在于——**「退租时」可以是下个月，也可以是三个月后**。

后面还跟着一句「如房屋有损坏，甲方有权扣除相应费用后退还」。「相应费用」没有标准。他说墙面脏了要重刷，你就得认。

那份合同我后来逐字读了一遍，一共十条，六条有问题：

❗ 押金退还无期限、扣款无标准
❗ 租期届满自动续租一年，想走走不掉
❗ 维修责任全归乙方，水管爆了算你的
❗ 提前退租押金不退，等于损失一个月房租
❗ 逾期付款按日 5% 计滞纳金，欠 4800 一天罚 240
❗ 一切损失由乙方承担，赔偿没有边界

更值得注意的是**它没写什么**：

没有押金退还期限、没有租金调整机制、没有维修责任划分、没有争议解决方式、没有房屋状况确认单。

没写的东西比写了的更危险，因为出事的时候全靠对方解释。

我把这份和一份规范合同都跑了一遍：**100 分 vs 0 分**。

关键不是删掉条款，是给每条补上「期限、标准、程序」。

比如押金那条，补一句就行：

「退租验收合格后 3 个工作日内退还，逾期按日万分之五支付违约金。扣款项目及金额须经双方书面确认；自然损耗不视为损坏。」

跟房东谈的时候别说「你这条违法」，说：

「这套合同是中介的模板吧？我想在补充条款里加三句话，其他都不动，您看行吗？」

**对方愿不愿意在纸上补一句话，本身就是答案。**

⚠️ 一点说明：这个工具只做文本匹配，不构成法律意见。金额大的（比如押金超过两个月房租）花几百块找律师看一眼是划算的。

`#租房` `#劳动合同` `#避坑` `#打工人` / `#租房攻略` `#押金` `#合同` `#签约` / `#我的租房生活`

**首评（置顶）**

补充一个我觉得最实用的判断：拿「缺失项清单」去问对方。如果连「押金 3 个工作日内退」这种标准条款都不肯写，那这笔交易本身就要重新评估。

---

## 三、X / Twitter（英文）

```
Signed a lease last year. Lost the deposit over one sentence I didn't read:

"押金于退租时退还" — deposit returned "at move-out." No deadline. That's not a
promise, it's a permission.

Built a scanner. Two things it does that generic contract review doesn't:

1. **Locates the clause.** Not "there are risks" — here's the exact sentence,
   with the page you're on.
2. **Reports what's missing.** No deposit-return deadline, no repair-cost split,
   no early-termination clause. Missing terms are worse than bad terms, because
   when things go wrong the other side just interprets.

Each hit ships with replacement text you can paste into an addendum.

Calibration: bad lease 100, clean lease 0.

Not legal advice — explicitly, in the output, every run.
```


---

## 四、Show HN

```
Show HN: Contract-redflag – scan leases and employment contracts for risky clauses

I lost a deposit to a single sentence: "deposit returned at move-out." No
deadline, no standard for deductions. Legally it may be fine; practically it
means the other side decides when and how much.

The tool scores a contract and, more usefully, does two things generic "AI
review this contract" doesn't:

1. Locates each risky clause verbatim so you can find it in the paper copy.
2. Reports missing clauses. A lease with no deposit-return deadline, no repair
   cost split, and no early-termination terms scored worse than one with a
   single hostile clause — because absent terms get interpreted later by whoever
   holds the deposit.

Every finding comes with paste-ready replacement text for an addendum.

Two implementation details worth mentioning: it filters "protective" phrasing
(a clause that *requires* 24h notice before entry is not a risk), and it
de-duplicates overlapping matches so one bad sentence doesn't tank the score
three times.

Explicitly not legal advice, printed on every run.

github.com/zhbehx/contract-redflag
```


---

## 五、发布清单

| 渠道 | 素材 | 关键动作 |
| --- | --- | --- |
| GitHub | Release v1.0.0 | 已发布 |
| X | 上面的英文稿 | 配终端截图，分数可见 |
| Show HN | 上面的 HN 稿 | 周二至周四 UTC 14:00–16:00 |
| 社群 / 即刻 | 一句话 + 链接 | 只讲一个点，别贴 README |