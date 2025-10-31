## Why
当前系统支持SQLite和PostgreSQL两种数据库持久化方案，增加了系统复杂度和维护成本。为了简化部署和运维，同时保持Redis的高性能缓存能力，需要将数据持久化策略简化为仅使用SQLite，这样可以：

- 减少数据库相关的外部依赖
- 简化Docker配置和部署流程
- 降低数据库运维复杂度和故障点
- 保持系统轻量级和易于部署的特点
- 保留Redis的高性能缓存优势

## What Changes
- **移除PostgreSQL依赖**: 删除PostgreSQL相关配置和服务
- **保留Redis缓存**: 继续使用Redis作为缓存和会话存储
- **SQLite作为唯一持久化存储**: 所有持久化数据统一使用SQLite
- **简化Docker配置**: 移除PostgreSQL容器，保留Redis容器
- **更新配置管理**: 简化数据库配置选项，保留Redis配置
- **调整监控配置**: 移除PostgreSQL相关监控，保留Redis监控

## Impact
- **受影响的规格**: agent-system规格中的状态管理部分需要修改
- **受影响的代码**: 数据访问层、配置管理、Docker配置
- **部署影响**: Docker Compose配置将简化，移除PostgreSQL但保留Redis
- **性能影响**: SQLite用于持久化，Redis继续提供高性能缓存