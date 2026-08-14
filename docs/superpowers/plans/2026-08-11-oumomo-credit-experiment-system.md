# Oumomo Credit Experiment System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不超过 980 积分、不触碰认证信息或真实发布的前提下，完成 Oumomo 能力黑盒实验、当前工程节点复盘、媒体质检、SOP 和可复用 Skill。

**Architecture:** 浏览器实验必须串行执行，通过统一 ExperimentRecord 和 CreditLedger 保存脱敏证据；媒体与文本产物下载后执行本地只读分析。核心实验先消耗最多 450 分，条件实验只有通过报价和最小重复数门禁后才使用剩余 530 分；所有结论进入报告、SOP 和一个经 RED-GREEN 验证的 Skill。

**Tech Stack:** Chrome browser runtime、Python 3.12 标准库、ffprobe/ffmpeg（本机存在时）、JSONL、CSV、Markdown、SHA-256、现有合成商品图、Codex Skill 规范。

## Global Constraints

- 总净扣积分硬上限为 980；余额初始事实为 980。
- 所有 shell 命令以 `rtk` 开头。
- 只在 `main` 分支工作，不使用 worktree。
- 未经用户明确要求不创建 commit、不 push。
- 浏览器付费任务一次只提交一个；页面无响应时先查任务、项目和积分，禁止重复点击。
- 只使用正常 UI、可见任务状态、积分账本和用户自己的生成产物。
- 不读取或保存 Cookie、Token、请求头、完整任务 ID、签名媒体 URL、手机号、账号标识或模型私有推理。
- 不绕过登录、验证码、权限、付费、限流或安全拦截。
- 不执行 OAuth、TikTok 账号绑定或最终发布。
- 只使用自制商品图、站内授权素材和自己的生成产物。
- 每项结论标记 `F`、`I-H`、`I-M`、`U` 或 `Vendor claim`。
- 浏览器控制结束时保留用户原始工作台，关闭研究标签页。

---

### Task 1: 建立实验合同、积分账本与脱敏校验器

**Files:**
- Create: `tools/oumomo_experiments/__init__.py`
- Create: `tools/oumomo_experiments/contracts.py`
- Create: `tools/oumomo_experiments/record.py`
- Create: `tools/oumomo_experiments/tests/test_contracts.py`
- Create: `outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`
- Create: `outputs/oumomo-reverse-engineering/experiments/credit-ledger.csv`
- Create: `outputs/oumomo-reverse-engineering/experiments/job-state-events.jsonl`
- Create: `outputs/oumomo-reverse-engineering/fixtures/fixture-manifest.json`

**Interfaces:**
- Consumes: 设计规格中的 ExperimentRecord 字段、980 积分硬上限和敏感字段禁令。
- Produces: `ExperimentRecord.from_mapping(data) -> ExperimentRecord`、`validate_record(record) -> list[str]`、`append_record(path, record) -> None`、`ledger_total(path) -> int`。

- [x] **Step 1: 写合同失败测试**

`tools/oumomo_experiments/tests/test_contracts.py` 至少包含：

```python
from pathlib import Path
import tempfile
import unittest

from tools.oumomo_experiments.contracts import ExperimentRecord, validate_record
from tools.oumomo_experiments.record import append_record, ledger_total


class ExperimentContractTests(unittest.TestCase):
    def test_rejects_paid_record_without_quote_and_credit_delta(self) -> None:
        record = ExperimentRecord.from_mapping({
            "experiment_id": "S-B01",
            "feature": "video-script",
            "verdict": "pass",
            "confidence": "F",
            "submit_count": 1,
        })
        self.assertEqual(
            validate_record(record),
            ["paid submission requires quote_before_submit, credit_before, credit_after and ledger_delta"],
        )

    def test_rejects_sensitive_fields_and_raw_job_ids(self) -> None:
        record = ExperimentRecord.from_mapping({
            "experiment_id": "Z00",
            "feature": "account-baseline",
            "verdict": "blocked",
            "confidence": "F",
            "cookie": "secret",
            "job_id": "raw-job-id",
        })
        self.assertEqual(
            validate_record(record),
            ["forbidden field: cookie", "raw job_id is forbidden; store job_id_hash"],
        )

    def test_ledger_total_rejects_more_than_980_points(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.csv"
            path.write_text("experiment_id,quote,delta,balance_after\nA,500,-500,480\nB,500,-500,-20\n")
            with self.assertRaisesRegex(ValueError, "980 point budget exceeded"):
                ledger_total(path)
```

- [x] **Step 2: 运行测试并确认正确失败**

Run: `rtk uv run --project apps/api python -m unittest discover -s tools/oumomo_experiments/tests -v`

Expected: import 失败，因为合同模块尚未存在。

- [x] **Step 3: 实现最小合同和追加写入**

`contracts.py` 使用 frozen dataclass 保存已知字段和 `extra_fields`；`validate_record` 必须执行：

```text
submit_count > 0 → quote_before_submit、credit_before、credit_after、ledger_delta 全部存在
confidence ∈ {F, I-H, I-M, U, Vendor claim}
verdict ∈ {pass, fail, blocked, inconclusive}
禁止 cookie、token、authorization、headers、phone、raw_job_id、job_id、signed_url
job_id 只能以 64 位十六进制 job_id_hash 保存
```

`record.py` 使用 UTF-8、`json.dumps(..., sort_keys=True)` 和 `csv.DictReader`；累计净扣分按负 delta 的绝对值计算，超过 980 抛出 `ValueError`。

- [x] **Step 4: 初始化空账本和夹具清单**

`credit-ledger.csv` 固定表头：

```csv
experiment_id,observed_at,feature,quote,credit_before,credit_after,delta,terminal_state,notes
```

`fixture-manifest.json` 初始登记已有 `pulse-mix.png` 的相对路径、用途和 SHA-256；不写入绝对路径。

- [x] **Step 5: 验证合同与敏感字段扫描**

Run: `rtk uv run --project apps/api python -m unittest discover -s tools/oumomo_experiments/tests -v`

Expected: 全部通过。

Run: `rtk rg -n -i "cookie|authorization:|bearer |signed_url|raw_job_id|phone" outputs/oumomo-reverse-engineering/experiments outputs/oumomo-reverse-engineering/fixtures`

Expected: 零命中。

---

### Task 2: 完成零积分能力、报价与账户基线盘点

**Files:**
- Create: `outputs/oumomo-reverse-engineering/reports/capability-map.md`
- Create: `outputs/oumomo-reverse-engineering/experiments/config-snapshots/free-probe-2026-08-11.json`
- Modify: `outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`
- Modify: `outputs/oumomo-reverse-engineering/experiments/credit-ledger.csv`

**Interfaces:**
- Consumes: 当前已登录 Chrome 标签页、Task 1 合同、余额 980。
- Produces: `Z00`–`Z12` 脱敏记录、功能/参数/报价图谱和每个付费模块的执行门禁结论。

- [x] **Step 1: 记录 Z00 账户基线**

连续刷新工作台三次，记录余额、任务队列计数、项目计数、历史产物指纹和余额刷新延迟。不得记录页面中的手机号或完整任务身份。

Expected: 三次余额均为 980；如不一致，暂停后续任务并先对账。

- [x] **Step 2: 记录 Z01 榜单与模板目录**

只读枚举地区、品类、时间窗、GMV、销量、AI 生成、排序、分页和模板分类；保存 URL 中非敏感筛选键、前 12 项脱敏指纹和结果数量。不得下载第三方原视频。

- [x] **Step 3: 记录 Z02 爆款脚本免费路径**

依次验证空输入、错误 URL、非支持域和站内示例；每例只走到配置与报价前。记录商品字段、可编辑卖点、语言、受众、优惠、时长、script type、参考范围和预计 10 分报价。

- [x] **Step 4: 记录 Z03 爆款复刻免费路径**

分别检查 2 条站内参考、2 条公开合法参考和 2 条失效参考的可播放性。只有找到可稳定播放的参考并记录结构摘要时，`replica_paid_gate=true`。

- [x] **Step 5: 记录 Z04 链接生视频免费路径**

依次验证示例 URL、错误 URL和手动商品；记录商品字段、图片上限、模式、分辨率、时长、数量、workspace 状态和最低报价。未观察到旧 HTML/JSON 错误不代表提交已修复，只能允许单次付费回归。

- [x] **Step 6: 记录 Z05–Z10 扩展能力**

逐项走到付费按钮前：爆款模板、TK 图文带货、数字人、视频模型、图片模型、视频去重、视频质量检测、多角度白底图、标题/标签和视频增强。记录可见 ID/名称、输入约束、报价和输出类型。

- [x] **Step 7: 记录 Z11 项目生命周期与 Z12 现有产物入口**

使用已有项目验证预览、编辑、下载、重新生成报价、任务恢复和发布 dry-run 入口；不得点击重新生成或最终发布。

- [x] **Step 8: 对账零积分阶段**

Expected: `credit_before=980`、`credit_after=980`、`ledger_delta=0`。任何扣分都要记录为异常并暂停。

- [x] **Step 9: 验证能力图谱覆盖**

Run: `rtk rg -n "Z0[0-9]|Z1[0-2]" outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`

Expected: Z00–Z12 各至少一条记录。

---

### Task 3: 下载并完成已有复刻产物的零积分媒体取证

**Files:**
- Create: `tools/oumomo_experiments/media_probe.py`
- Create: `tools/oumomo_experiments/tests/test_media_probe.py`
- Create: `outputs/oumomo-reverse-engineering/artifacts/hashes.csv`
- Create: `outputs/oumomo-reverse-engineering/artifacts/scorecards.csv`
- Create: `outputs/oumomo-reverse-engineering/artifacts/frame-grids/existing-replica.md`
- Create: `outputs/oumomo-reverse-engineering/artifacts/asr/existing-replica.md`
- Create: `outputs/oumomo-reverse-engineering/artifacts/ocr/existing-replica.md`
- Create: `outputs/oumomo-reverse-engineering/artifacts/shot-boundaries/existing-replica.json`
- Modify: `outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`

**Interfaces:**
- Consumes: 用户自己的已有爆款复刻项目和下载入口。
- Produces: `probe_media(path) -> dict[str, object]`、媒体哈希、元数据、帧摘要、ASR/OCR/镜头人工或工具证据。

- [x] **Step 1: 写 media_probe 失败测试**

测试使用不存在文件和已知字节夹具，断言不存在文件返回稳定错误、SHA-256 与字节数正确；ffprobe 不存在时返回 `probe_status=unavailable` 而不是崩溃。

- [x] **Step 2: 运行测试并确认模块缺失**

Run: `rtk uv run --project apps/api python -m unittest tools.oumomo_experiments.tests.test_media_probe -v`

Expected: import 失败。

- [x] **Step 3: 实现媒体探针**

使用 `hashlib`、`pathlib` 和 `subprocess.run([...], shell=False)`；ffprobe 参数固定输出 JSON，不把文件 URL 或绝对路径写入报告。

- [x] **Step 4: 验证媒体探针测试**

Run: `rtk uv run --project apps/api python -m unittest tools.oumomo_experiments.tests.test_media_probe -v`

Expected: 全部通过。

- [x] **Step 5: 从项目页下载自己的已有产物**

下载前确认项目属于本账号且是既有实验生成；保存到 `outputs/oumomo-reverse-engineering/artifacts/media/`。不得保存签名 CDN URL。

- [x] **Step 6: 生成元数据、帧网格和镜头证据**

运行 media probe；本机有 ffmpeg 时按 0%、25%、50%、75%、95% 抽帧，并记录镜头变化。无 ffmpeg 时保留哈希和浏览器可见帧证据，标记工具不可用。

- [x] **Step 7: 完成 ASR/OCR 与事实审计**

记录可听口播、可见包装文字、无证据声明、商品颜色/Logo 漂移和镜头角色。自动工具不可用时使用人工双遍核对并标记 `method=manual-two-pass`。

- [x] **Step 8: 对账任务未产生积分变化**

Expected: 余额仍为 980。

---

### Task 4: 执行爆款脚本 12 次单变量实验

**Files:**
- Create: `outputs/oumomo-reverse-engineering/fixtures/product-facts/pulse-mix-facts.json`
- Create: `outputs/oumomo-reverse-engineering/experiments/config-snapshots/script-matrix.json`
- Create: `outputs/oumomo-reverse-engineering/reports/script-experiment-findings.md`
- Modify: `outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`
- Modify: `outputs/oumomo-reverse-engineering/experiments/credit-ledger.csv`
- Modify: `outputs/oumomo-reverse-engineering/experiments/job-state-events.jsonl`

**Interfaces:**
- Consumes: Z02 免费探路、固定商品事实、10 分报价。
- Produces: S-B01–S-B03、S-D15、S-D45、S-T01、S-T02、S-L01、S-A01、S-P01、S-O01、S-F01，共 12 个独立脚本产物和对照结论。

- [x] **Step 1: 冻结脚本输入夹具**

`pulse-mix-facts.json` 只包含图上可见、安全事实：商品名 `PULSE MIX`、白/蓝包装、粉末冲调形态；不得加入能量、口味、剂量、健康效果、认证或价格。

- [x] **Step 2: 执行 S-B01、S-B02、S-B03 完全重复基线**

同商品、30 秒、英语、相同受众、相同 script type、相同参考范围和无优惠。每次提交前确认报价 10、记录余额并只点击一次。三次输出分别保存，不能接受同详情覆盖而不另存证据。

- [x] **Step 3: 执行 S-D15 和 S-D45 时长对照**

只把时长改为 15 秒或 45 秒；其余配置与 S-B01 完全一致。

- [x] **Step 4: 执行 S-T01 和 S-T02 结构对照**

从 Z02 枚举中选择 phase 序列差异最大的两个 script type；只改变 script type。

- [x] **Step 5: 执行 S-L01 语言对照**

只把英语改为站点支持的另一种语言；记录所有可见字段是否完整切换语言。

- [x] **Step 6: 执行 S-A01 受众对照**

只改变目标受众；检查卖点排序和措辞变化，商品事实必须保持。

- [x] **Step 7: 执行 S-P01 优惠对照**

只增加明确、可追踪且标为实验输入的优惠文本；不得伪造真实价格或稀缺性。

- [x] **Step 8: 执行 S-O01 卖点顺序对照**

只调整既有事实顺序，不增加或删除事实。

- [x] **Step 9: 执行 S-F01 删除事实对照**

从输入中删除一个非身份事实；若输出继续使用该事实，记为事实泄漏。

- [x] **Step 10: 逐次保存和对账**

每次记录 quote、before/after、状态、耗时、输出结构、标题、标签和失败签名。Expected cumulative debit: 120；若单次报价不是 10，暂停矩阵重新审计。

- [x] **Step 11: 计算脚本实验结论**

比较 phase/shot 数、Hook 位置、事实精确率、无证据声明、字段完整率、重复输出差异、版本独立性和编辑持久化；区分随机性与单变量效应。

---

### Task 5: 执行爆款复刻 6 次结构与一致性实验

**Files:**
- Create: `outputs/oumomo-reverse-engineering/fixtures/reference-videos/reference-manifest.json`
- Create: `outputs/oumomo-reverse-engineering/experiments/config-snapshots/replica-matrix.json`
- Create: `outputs/oumomo-reverse-engineering/reports/replica-experiment-findings.md`
- Modify: `outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`
- Modify: `outputs/oumomo-reverse-engineering/experiments/credit-ledger.csv`
- Modify: `outputs/oumomo-reverse-engineering/artifacts/hashes.csv`
- Modify: `outputs/oumomo-reverse-engineering/artifacts/scorecards.csv`

**Interfaces:**
- Consumes: Z03 的可播放参考门禁、1 张和 3 张商品图、最低档 30 分报价。
- Produces: R-B01–R-B03、R-I03、R-P01、R-V02 六个视频产物与参考结构对照。

- [x] **Step 1: 锁定可播放参考并写结构摘要**

- [x] **阻塞状态**：2026-08-12 重检后仍仅 1 条可播放且不可稳定复现，`reference_preview_unstable`，Task 5 暂停，待两条稳定参考确认。  
- [ ] **步骤 2-8**：受阻塞条件限制，暂停提交 R-B01~R-V02，保留 180 分预算。

记录参考指纹、时长、Hook、镜头角色、CTA、字幕/口播摘要和使用依据。参考无法稳定播放时将 Task 5 标记 blocked，不消耗积分。

- [ ] **Step 2: 执行 R-B01、R-B02、R-B03 基线重复**

同参考、单张商品图、空提示词、Mini/480P/15 秒/英语/1 个；每次报价必须为 30 或更低且属于预算信封。

- [ ] **Step 3: 执行 R-I03 多角度商品图对照**

只把单张图替换为相同商品的三角度图；不改变参考、提示词或渲染配置。

- [ ] **Step 4: 执行 R-P01 事实约束提示词对照**

只加入“不得声称能量、口味、剂量、健康效果、认证或价格；仅展示包装与冲调动作”的事实约束。

- [ ] **Step 5: 执行 R-V02 参考视频对照**

只更换为第二条可播放参考；商品图、提示词和渲染配置保持。

- [ ] **Step 6: 每条任务跟踪到终态并下载自己的产物**

记录状态序列、耗时、报价、扣分和媒体哈希；任务失败先对账，不自动补跑。

- [ ] **Step 7: 完成结构、商品和原创性分析**

比较 Hook 偏差、镜头角色 F1、CTA、ASR/OCR、商品颜色/文字/Logo、无证据声明和三次基线的媒体相似度。

- [ ] **Step 8: 验证模块预算**

Expected maximum cumulative debit for Task 5: 180；总累计不超过 300。

---

### Task 6: 执行链接生视频故障回归与最多 5 次实验

**Files:**
- Create: `outputs/oumomo-reverse-engineering/experiments/config-snapshots/url-video-matrix.json`
- Create: `outputs/oumomo-reverse-engineering/reports/url-video-experiment-findings.md`
- Modify: `outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`
- Modify: `outputs/oumomo-reverse-engineering/experiments/credit-ledger.csv`
- Modify: `outputs/oumomo-reverse-engineering/experiments/job-state-events.jsonl`

**Interfaces:**
- Consumes: Z04 免费配置、最低档报价、合成商品输入。
- Produces: U-B01；通过故障门禁后再产生 U-B02、U-B03、U-A01、U-I01。

- [x] **Step 1: 提交 U-B01 单次故障回归**

冻结最低档配置，记录报价和余额，只点击一次。观察是否创建可恢复 job、是否出现旧 `Unexpected token '<'`、按钮是否永久 disabled、是否扣分。

- [x] **Step 2: 执行强制停止判断**

若无 job、HTML/JSON 错误、扣费不明或永久 disabled，记录 blocked/fail，停止 Task 6，不再使用剩余 120 分。  
- [ ] **步骤 3-5 决策**：尽管 U-B01 已成功恢复，本阶段保持暂缓，按“先修复提交契约和恢复链路”优先，再决定是否重放 U-B02~U-I01。

- [ ] **Step 3: 执行 U-B02、U-B03 完全重复**

只有 U-B01 成功且账务明确时执行；配置与 U-B01 完全一致，使基线总样本达到 3。

- [ ] **Step 4: 执行 U-A01 受众对照**

只改变受众；比较脚本、镜头和商品事实。

- [ ] **Step 5: 执行 U-I01 图片数量对照**

只把 1 张图改为 3 张同商品多角度图；其他配置保持。

- [x] **Step 6: 下载、分析和对账成功产物**

记录任务恢复、媒体参数、脚本事实、ASR/OCR、镜头结构和三次重复相似度。

- [x] **Step 7: 验证核心预算**

Expected maximum Task 6 debit: 150；Tasks 4–6 总净扣不超过 450。

---

### Task 7: 执行模板与图片模型条件实验

**Files:**
- Create: `outputs/oumomo-reverse-engineering/experiments/config-snapshots/template-image-matrix.json`
- Create: `outputs/oumomo-reverse-engineering/reports/template-image-findings.md`
- Modify: `outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`
- Modify: `outputs/oumomo-reverse-engineering/experiments/credit-ledger.csv`
- Modify: `outputs/oumomo-reverse-engineering/artifacts/scorecards.csv`

**Interfaces:**
- Consumes: Z05/Z10 的模板、GPT Image 2/Nano Banana 2 可见身份和报价。
- Produces: T-A01/T-A02、T-B01/T-B02 和至少两个图片模型各两次结果。

- [x] **Step 1: 验证模板最小有效设计门禁**

必须存在稳定模板名称或 ID、明确预览、同商品/同模型配置和单次报价不超过 30；实际未满足，模板实验记录为 blocked，预算保留。

- [ ] **Step 2: 执行模板 A 两次和模板 B 两次（blocked）**

只有模板变量不同；比较模板内方差和模板间 phase/shot/Hook/CTA 效应。由于预审门槛（稳定模板名/预览/单次报价）不成立，当前阶段保持 blocked，不消耗积分。

- [x] **Step 3: 验证图片模型门禁**

至少两个可见模型，每模型能用相同 prompt、商品图、比例和数量重复 2 次；总报价不超过 60。

- [x] **Step 4: 执行图片模型矩阵**

每模型两次；若 3 个模型均满足预算可执行 6 次，否则执行 2 模型 × 2 次的最小矩阵。

- [x] **Step 5: 分析图片结果**

记录商品文字、颜色、构图、人物/手部、场景遵循、多图一致性、模型内方差和模型间差异。

---

### Task 8: 执行数字人与视频模型路由条件实验

**Files:**
- Create: `outputs/oumomo-reverse-engineering/experiments/config-snapshots/avatar-video-model-matrix.json`
- Create: `outputs/oumomo-reverse-engineering/reports/avatar-video-model-findings.md`
- Modify: `outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`
- Modify: `outputs/oumomo-reverse-engineering/experiments/credit-ledger.csv`
- Modify: `outputs/oumomo-reverse-engineering/artifacts/scorecards.csv`

**Interfaces:**
- Consumes: 站内授权 Avatar、可见视频模型名、最低有效报价。
- Produces: Avatar A 三次、Avatar B 两次；至少 2 个视频模型各两次，预算允许时 3 模型各两次。

- [x] **Step 1: 验证数字人门禁**

只用站内授权 Avatar；不上传人脸或声音。单次报价不超过 30，总报价不超过 150；否则 blocked。
- [ ] **说明**：当前引用 Avatar A/B 75 积分 > 30 cap，已触发 cap blocked。

- [ ] **Step 2: 执行 Avatar A 三次和 Avatar B 两次**

固定脚本、声音、背景和模型；记录身份、口型、手部/商品接触、视线、面部漂移、声音和跨镜头一致性。

- [x] **Step 3: 验证视频模型路由门禁**

页面必须显示具体模型名而不只是 Mini/快速/高质；相同 prompt、参考图、比例、时长和分辨率可用。每模型至少重复 2 次，总报价不超过 180。

- [ ] **Step 4: 执行视频模型矩阵（blocked）**

优先选择 3 个差异定位明显的模型各两次；预算只支持 2 模型时执行 2 × 2 最小矩阵并保留余额。  
当前因模型参考输入上传门禁未通过，无法保证同输入同模型对照，暂停矩阵。

- [ ] **Step 5: 分析模型结果**

比较可见模型名、报价、时延、分辨率、时长、codec、大小、OCR、颜色、动作、人物一致性、prompt 遵循和模型内/间方差。

---

### Task 9: 校准质量评分、评估去重并完成发布 dry-run

**Files:**
- Create: `tools/oumomo_experiments/create_degradations.py`
- Create: `tools/oumomo_experiments/tests/test_create_degradations.py`
- Create: `outputs/oumomo-reverse-engineering/fixtures/scoring-degradations/manifest.json`
- Create: `outputs/oumomo-reverse-engineering/reports/quality-dedup-publish-findings.md`
- Modify: `outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`
- Modify: `outputs/oumomo-reverse-engineering/experiments/credit-ledger.csv`

**Interfaces:**
- Consumes: 用户自己的一个成功视频、Task 4–8 的重复产物。
- Produces: 原片/强压缩/错比例/静音/音画错位/关键画面受损样本，质量评分重复性结论、媒体多样性结论和发布字段合同。

- [x] **Step 1: 写受控降质失败测试**

测试要求每个 degradation 有唯一 ID、source hash、变换类型和参数；缺 ffmpeg 时返回 unavailable，不生成伪产物。

- [x] **Step 2: 实现受控降质脚本并验证**

使用参数数组和 `shell=False`；只处理本地自有媒体。Run: `rtk uv run --project apps/api python -m unittest tools.oumomo_experiments.tests.test_create_degradations -v`。Expected: 全部通过。

- [x] **Step 3: 生成六类评分样本**

生成原片、强压缩、错比例、静音、音画错位和关键画面遮挡；保存变换参数和哈希。

- [ ] **Step 4: 执行质量评分门禁与矩阵（blocked）**

若免费，每类重复 3 次；若收费，20 分预算必须容纳至少两个组各两次。记录总分、子分、阈值、解释和修改建议。
- [ ] **说明**：`Q-GATE` 选择 U-B01 后跨路由跳转到 TikTok 幻灯片页，未形成可用前后对照。

- [ ] **Step 5: 评估评分器有效性（blocked）**

检查同文件重复波动、严重度单调性、画质/音频子分敏感性和关键画面损伤识别。没有这些信号时不能把总分视为可靠质量指标。

- [ ] **Step 6: 评估去重/多样性（blocked）**

复用三次重复产物，比较感知相似度、镜头结构、ASR/OCR n-gram、音频和事实保持。没有显式去重前后对照时结论固定为“输出多样性”，不写成算法因果。

- [x] **Step 7: 完成发布 dry-run**

只记录项目、平台、标题、标签、隐私、排期、预览和状态字段；在 OAuth、绑定账号或最终发布按钮前停止。

- [x] **Step 8: 完成最终积分对账**

Run: `rtk uv run --project apps/api python -c "from pathlib import Path; from tools.oumomo_experiments.record import ledger_total; print(ledger_total(Path('outputs/oumomo-reverse-engineering/experiments/credit-ledger.csv')))"`

Expected: 输出不大于 980，且当前站点余额与 CSV 最后一行一致。

---

### Task 10: 形成当前项目逐节点复盘与 P1/P2 路线

**Files:**
- Create: `outputs/oumomo-reverse-engineering/reports/project-node-review.md`
- Create: `outputs/oumomo-reverse-engineering/reports/p1-p2-roadmap.md`
- Modify: `outputs/oumomo-reverse-engineering/reports/capability-map.md`

**Interfaces:**
- Consumes: 当前仓库代码、既有 81 个后端测试/11 个前端测试/2 个 E2E 的基线事实、所有实验记录。
- Produces: 输入、领域、API、异步、Provider、校验、持久化、迁移、安全、Web、测试逐节点评分与路线。

- [x] **Step 1: 写后端节点复盘**

每个节点必须包含实际文件路径、输入输出合同、价值星级、壁垒星级、复杂度星级、已覆盖失败和开放缺口。

- [x] **Step 2: 写 Web 节点复盘**

覆盖商品、事实、生成、Job、脚本、版本、diff、导出、导航、错误恢复、移动端和无障碍。

- [x] **Step 3: 对照实验更新能力图谱**

将模板、数字人、模型、去重、评分和发布结论标记证据等级；营销声明与实测分栏。

- [x] **Step 4: 写 P1/P1.5/P2 路线**

P1 固定为事实驱动脚本工作台；P1.5 固定为 outbox、ImportAttempt、完整 pattern 和 SaaS 权限；P2 固定为 preview-first 视频流水线。每项必须链接代码缺口或 experiment_id。

- [x] **Step 5: 验证报告无未标注推断**

Run: `rtk rg -n "可能|推测|应该是|大概" outputs/oumomo-reverse-engineering/reports`

Expected: 每个命中附近都明确标注 I-H、I-M、U 或 Vendor claim。

---

### Task 11: 编写并用实测事件验证 9 份 SOP

**Files:**
- Create: `outputs/oumomo-reverse-engineering/sops/paid-job-safe-submit.md`
- Create: `outputs/oumomo-reverse-engineering/sops/credit-reconciliation.md`
- Create: `outputs/oumomo-reverse-engineering/sops/single-variable-experiment.md`
- Create: `outputs/oumomo-reverse-engineering/sops/product-fact-claim-audit.md`
- Create: `outputs/oumomo-reverse-engineering/sops/ai-media-qc.md`
- Create: `outputs/oumomo-reverse-engineering/sops/template-effect-benchmark.md`
- Create: `outputs/oumomo-reverse-engineering/sops/model-router-benchmark.md`
- Create: `outputs/oumomo-reverse-engineering/sops/quality-score-calibration.md`
- Create: `outputs/oumomo-reverse-engineering/sops/publish-dry-run.md`

**Interfaces:**
- Consumes: 实验事件、停止条件、账本与媒体分析。
- Produces: 每份 SOP 的 Purpose、Inputs、Preconditions、Steps、Evidence、Stop Conditions、Acceptance、Recovery 八段式合同。

- [x] **Step 1: 写安全提交、积分对账和单变量 SOP**

每份至少引用一个本轮成功或失败 experiment_id；不得写成无证据通用建议。

- [x] **Step 2: 写事实审计和媒体 QC SOP**

明确事实精确率、无证据声明、ASR/OCR、镜头、商品一致性和工具不可用回退。

- [x] **Step 3: 写模板、模型和评分 SOP**

明确组内重复、组间变量、最低样本数、预算门禁和无法形成因果结论的条件。

- [x] **Step 4: 写发布 dry-run SOP**

必须在 OAuth、账号绑定和最终发布前停止，不能包含绕过确认的操作。

- [x] **Step 5: 执行结构校验**

Run: `rtk run 'for f in outputs/oumomo-reverse-engineering/sops/*.md; do for h in Purpose Inputs Preconditions Steps Evidence "Stop Conditions" Acceptance Recovery; do grep -q "## $h" "$f" || exit 1; done; done'`

Expected: exit 0。

---

### Task 12: 以 RED-GREEN-REFACTOR 创建并前向验证主 Skill

**Files:**
- Create: `outputs/oumomo-reverse-engineering/skills/baseline-scenarios.md`
- Create: `outputs/oumomo-reverse-engineering/skills/baseline-results.md`
- Create: `outputs/oumomo-reverse-engineering/skills/oumomo-clean-room-experiment-runner/SKILL.md`
- Create: `outputs/oumomo-reverse-engineering/skills/oumomo-clean-room-experiment-runner/agents/openai.yaml`
- Create: `outputs/oumomo-reverse-engineering/skills/oumomo-clean-room-experiment-runner/references/evidence-contract.md`
- Create: `outputs/oumomo-reverse-engineering/skills/oumomo-clean-room-experiment-runner/references/feature-playbooks.md`
- Create: `outputs/oumomo-reverse-engineering/skills/oumomo-clean-room-experiment-runner/scripts/validate_evidence.py`
- Create: `outputs/oumomo-reverse-engineering/skills/forward-test-results.md`

**Interfaces:**
- Consumes: 9 份 SOP、实际实验失败、Task 1 合同、Skill Creator 和 writing-skills 规则。
- Produces: 可触发、可发现、可验证的 `oumomo-clean-room-experiment-runner` Skill。

- [x] **Step 1: 读取 Skill 编写和 TDD 规则**

完整读取 `skill-creator`、`superpowers:writing-skills`、`superpowers:test-driven-development` 及其要求的测试参考。

- [x] **Step 2: 创建 3 类无 Skill 基线场景**

场景分别施加：页面迟延诱发重复点击、余额充足诱发无对照烧分、输出成功诱发忽略事实漂移。每个场景要求 Agent 制定并执行实验决策。

- [x] **Step 3: 在无 Skill 条件下运行基线并记录失败**

至少记录遗漏的报价、任务恢复、账务、对照、停止条件或证据等级之一；若基线没有失败，则不创建对应规则。

- [x] **Step 4: 使用 init_skill.py 初始化 Skill**

输出目录固定为 `outputs/oumomo-reverse-engineering/skills`；资源仅创建 `scripts,references`。Skill 名称固定为 `oumomo-clean-room-experiment-runner`。

- [x] **Step 5: 写最小 SKILL.md 与 references**

frontmatter 只包含 name 和以 `Use when...` 开头的第三人称触发条件；SKILL.md 保持核心流程与停止门禁，详细证据合同和功能矩阵放 references。

- [x] **Step 6: 写并运行 validate_evidence.py**

脚本读取 JSONL/CSV，验证必填字段、预算、敏感字段和 job hash；使用 Task 1 测试夹具验证通过/失败路径。

- [x] **Step 7: 运行有 Skill 的相同和变体场景**

验证 Agent 能单次提交、先恢复任务、阻止超预算、要求有效对照、标注未知和停止真实发布。

- [x] **Step 8: 修正新歧义并重新验证**

只修复前向测试真实暴露的缺口；记录改动前后行为，不添加假设规则。

- [x] **Step 9: 运行 Skill 结构验证**

使用 Skill Creator 的 `quick_validate.py` 验证目录；检查 `agents/openai.yaml` 与 SKILL.md 一致。

---

### Task 13: 执行最终验收、敏感信息与工作区审计

**Files:**
- Modify: `outputs/oumomo-reverse-engineering/actual-validation-report.md`
- Modify: `outputs/oumomo-reverse-engineering/evidence/session-log.md`
- Create: `outputs/oumomo-reverse-engineering/reports/final-acceptance.md`
- Modify: `docs/architecture/p0-architecture.md` only if experiments produce lasting architectural decisions for P1/P2.
- Modify: `docs/development/testing.md` only if new durable validation commands are introduced.

**Interfaces:**
- Consumes: Tasks 1–12 的代码、证据、报告、SOP 和 Skill。
- Produces: 最终通过/阻断清单、精确积分、文件范围、测试结果和未完成事项。

- [x] **Step 1: 运行工具单元测试**

Run: `rtk uv run --project apps/api python -m unittest discover -s tools/oumomo_experiments/tests -v`

Expected: 全部通过。

- [x] **Step 2: 验证实验合同和积分上限**

运行 evidence validator；Expected: 无缺字段、无敏感字段、总净扣不超过 980、最终余额对账一致。

- [x] **Step 3: 验证报告和 SOP 完整性**

检查 13 个零积分 case、所有实际付费 case、9 份 SOP、4 份核心报告和 Skill 前向测试均存在；被门禁阻断的案例必须有明确 evidence_ref。

- [x] **Step 4: 执行敏感信息扫描**

Run: `rtk rg -n -i "cookie|authorization|bearer |token=|signed_url|raw_job_id|205466|187150" outputs/oumomo-reverse-engineering tools/oumomo_experiments docs`

Expected: 零真实敏感值；文档中的禁止词语句必须人工确认不是泄漏。

- [x] **Step 5: 运行差异格式和范围审计**

Run: `rtk run 'git diff --check'`

Run: `rtk git status --short --branch`

Expected: 只有本轮规格、计划、工具、实验、报告、SOP、Skill 和必要项目文档变化；无 `.env`、凭证、数据库、缓存、浏览器产物或第三方受保护媒体。

- [x] **Step 6: 更新长期文档**

仅把稳定、跨任务有效的架构与验证知识写入 architecture/testing；单次实验流水账留在 outputs。

- [x] **Step 7: 汇报但不提交**

报告实际扣分、剩余积分、成功/失败/阻断实验、最值得复刻部分、当前工程优先缺口、验证结果和未完成事项。未经用户新的明确授权，不创建 commit 或 push。
