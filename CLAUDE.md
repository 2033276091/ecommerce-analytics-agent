# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

这是一个面向电商经营分析的智能问数 Agent —— 用户用自然语言提问，系统理解问题、匹配数据表和指标口径、生成安全 SQL、查询本地 SQLite 数据库，并用业务语言解释结果。

## 智能体问数SOP
1. 问题输入：用户输入问题
2. 意图识别：识别用户问题意图（指标查询、报表生成、归因分析、异常查询）
3. schema召回：根据问题查询knowledge目录下的schema.py模块找到相应的表、字段以及metrics.py模块找到相应指标口径，并调用recall.py模块生成召回后提示词
4. SQL生成：基于召回schema提示词的指标定义和表结构生成 SQL
5. SQL校验：调用ask.py模块校验表权限、字段、语法是否有危险操作
6. 查询执行：调用ask.py模块将校验通过SQL提交数据库执行
7. 返回结果：按照相应的意图返回对应的结果
8. 追问推荐：给出下一步分析建议

## 输出规范
1. 识别用户意图（指标查询、报表生成、归因分析、异常查询）并打印
2. 根据用户问题进行schema召回并打印用到哪些表、哪些字段以及匹配到知识库哪个指标口径，没有匹配到表、字段和指标口径先说明不要自己硬算
3. 生成SQL并打印出来
4. 打印SQL校验过程
5. 提交数据库执行
6. 根据用户意图返回对应结果
7. 给出下一步分析建议
8. 把输出整理成一个文件放在output目录下的一个markdown文件中，命名格式模板为"001—用户意图-问题概要.md"

## 参考

表结构信息见 `docs/data_model.md`。

知识库 knowledge 目录
    schema.py 表结构信息
    metrics.py 指标口径定义
    recall.py schema召回

从 `docs/data_model.md` 加载口径定义（GMV、支付订单数、客单价、转化率、退款率、复购率等）。写 SQL 时必须遵守这些口径，例如：GMV 仅统计 `order_status = 'paid'`，退款率仅统计 `refund_status = 'approved'`。

