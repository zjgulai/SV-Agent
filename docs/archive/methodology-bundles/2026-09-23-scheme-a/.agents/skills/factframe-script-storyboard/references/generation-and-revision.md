# Generation 与 Fact Rebind SOP

## Generation

1. 从当前 Product Truth 读取 frozen Snapshot、ordered selected/excluded 与可选 Promotion。
2. 编译完整 Creative Pattern，冻结 duration、language、audience、provider/model、prompt contract 和 input digest。
3. 在一个事务创建 Job、generation、初始 JobEvent 与 Outbox intent。
4. Provider request 只包含 selected facts 与必要生成参数。
5. Provider 返回后由服务端覆盖 visual、action、acceptance、phase purpose、titles、tags、shooting list、audience copy 与 Promotion CTA。
6. 保存前重新读取 Facts/Promotion 并运行固定顺序的结构、时间、事实、excluded、copy、Pattern 校验。
7. 只在完整 acceptable 时追加 Script Version；失败写安全、typed findings。

## Fact rebind

1. 父版本必须可接受且属于冻结 generation。
2. 每个 shot 恰好一个 binding；fact 必须来自 generation 的 selected set。
3. 不接受自由文案、部分 shot、时间线、结构或 Pattern 变更。
4. 服务端复制结构并重建 voiceover、caption、claims 和 identifiers。
5. 完整重跑 frozen Pattern、excluded、Promotion 与事实资格校验。
6. 用 parent identity + operation key 幂等追加 child，不修改 parent。

## 关键测试

- 每种 Pattern、language 与 15/30/45 秒 plan。
- 少/多 shot、错序 role、语速/时间预算、server-owned copy 篡改。
- Provider request 不含 excluded、Promotion、audience、source raw content。
- Fact 在 queue、provider 前、save 时降级。
- rebind 缺 shot、重复 shot、自由文案、非 selected fact、operation replay。

执行语义交给 `$factframe-reliable-execution`；不要在此 skill 重新定义 Celery 重试。
