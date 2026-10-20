---
status: accepted
---

# PostgreSQL 继续作为唯一业务事实源

Product Snapshot、Product Fact、Job、Script Version 和 Storyboard 等业务状态只以 PostgreSQL 为权威；Oumomo ledger 和 Momcozy asset archive 保持独立证据存储。文件证据可以支持 capability finding 和 roadmap，但不能直接成为 Product Fact，避免证据等级、所有权和 append-only 规则被跨域混用。
