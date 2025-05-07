# Features

## role
- 任务角色支持

## plugin
- 插件支持

## kb-support
- 支持保存完整的任务数据到 sqlite/json/minio
- 支持任务重用: 完全一样的任务/稍微有区别的任务/参数化的任务


## usage-limit
- 完善使用情况统计：支持各家 API，支持细粒度
- 时间统计
- 对话次数统计

可以配置三种数据的最大值，超过就停止任务。

## shiv
支持 shiv 打包

## check-result
### 需求
- 确保 __result__ 可以 json 序列化
- 替换 __result__ 里 api key 的值

## add-llm-claude
### 需求
- 支持配置和使用 Claude API

## io-yes-now
### 需求
- 自动确认 LLM 申请安装 package 或获取 env 的申请
- 统一输入输出接口，为脱离控制台使用做准备
- 解决客户端证书路径问题

## use-dynaconf
### 需求
- 降低配置复杂度：避免配置文件里有太多内容吓倒用户
- 开发时避免维护两个版本的配置文件

### 方案
配置文件划分成两个：
- 默认配置：default.toml，提交到 git
- 本地配置：保存用户必须设置的配置，如 API KEY 等

