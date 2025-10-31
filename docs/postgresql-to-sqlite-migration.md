# PostgreSQL到SQLite迁移指南

## 概述

本指南说明如何从PostgreSQL迁移到SQLite，这是基于系统架构简化的决策，以减少维护复杂度并提高部署便利性。

## 迁移原因

1. **简化架构**: 减少外部依赖，降低系统复杂度
2. **易于部署**: SQLite是嵌入式数据库，无需额外数据库服务
3. **减少故障点**: 移除PostgreSQL服务，减少系统组件
4. **保持性能**: SQLite+WAL模式能满足大多数应用场景
5. **保留Redis**: 继续使用Redis提供高性能缓存

## 数据迁移步骤

### 1. 备份PostgreSQL数据

```bash
# 备份所有表
pg_dump -h localhost -U langgraph_user -d langgraph_db > postgres_backup.sql

# 或者仅备份数据
pg_dump -h localhost -U langgraph_user -d langgraph_db --data-only > data_backup.sql
```

### 2. 创建SQLite数据库

```bash
# 确保数据目录存在
mkdir -p data

# 创建SQLite数据库
sqlite3 data/app.db < scripts/init-db.sql
```

### 3. 数据转换脚本

由于PostgreSQL和SQLite的数据类型差异，需要使用转换脚本：

```python
import sqlite3
import psycopg2
import json
from datetime import datetime

def migrate_data():
    # 连接PostgreSQL
    pg_conn = psycopg2.connect(
        host="localhost",
        database="langgraph_db",
        user="langgraph_user",
        password="langgraph_password"
    )
    pg_cur = pg_conn.cursor()

    # 连接SQLite
    sqlite_conn = sqlite3.connect("data/app.db")
    sqlite_cur = sqlite_conn.cursor()

    try:
        # 迁移tasks表
        pg_cur.execute("SELECT * FROM tasks")
        for row in pg_cur.fetchall():
            # 转换JSON字段
            input_data = json.dumps(row[10]) if row[10] else '{}'
            output_data = json.dumps(row[11]) if row[11] else None
            metadata = json.dumps(row[12]) if row[12] else '{}'

            sqlite_cur.execute("""
                INSERT INTO tasks (
                    id, title, description, task_type, priority, status,
                    created_at, updated_at, started_at, completed_at,
                    requester_id, input_data, output_data, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row[0]), row[1], row[2], row[3], row[4], row[5],
                row[6], row[7], row[8], row[9], row[10] or '',
                input_data, output_data, metadata
            ))

        # 迁移其他表...
        # workflows, agent_executions, checkpoints, metrics, event_logs

        sqlite_conn.commit()
        print("数据迁移完成")

    except Exception as e:
        print(f"迁移失败: {e}")
        sqlite_conn.rollback()
        raise
    finally:
        pg_conn.close()
        sqlite_conn.close()

if __name__ == "__main__":
    migrate_data()
```

### 4. 验证迁移结果

```bash
# 检查数据完整性
sqlite3 data/app.db "SELECT COUNT(*) FROM tasks;"
sqlite3 data/app.db "SELECT COUNT(*) FROM workflows;"

# 验证数据格式
sqlite3 data/app.db "SELECT * FROM tasks LIMIT 5;"
```

## 配置变更

### 环境变量更新

```bash
# 移除PostgreSQL相关配置
# DATABASE_URL=postgresql://...  # 删除此行

# 使用SQLite配置
SQLITE_DATABASE_PATH=./data/app.db

# Redis配置保持不变
REDIS_URL=redis://localhost:6379/0
```

### Docker配置更新

```yaml
# docker-compose.yml 变更
services:
  langgraph-multi-agent:
    environment:
      - DATABASE_URL=sqlite:///data/app.db  # SQLite数据库
      - REDIS_URL=redis://redis:6379/0     # Redis保持不变
    depends_on:
      - redis        # 移除postgres依赖
    volumes:
      - ./data:/app/data  # SQLite数据持久化

  # 移除postgres服务块
```

## 功能对比

| 功能 | PostgreSQL | SQLite | 迁移影响 |
|------|-----------|--------|----------|
| 数据持久化 | ✅ 完整 | ✅ 完整 | 无损失 |
| 并发写入 | ✅ 高并发 | ✅ WAL模式支持 | 略有降低 |
| 复杂查询 | ✅ 强大 | ✅ 基本支持 | 部分简化 |
| 数据类型 | ✅ 丰富 | ✅ 基本类型 | 需转换 |
| JSON支持 | ✅ JSONB | ✅ TEXT存储 | 格式转换 |
| 全文搜索 | ✅ 内置 | ❌ 需扩展 | 功能减少 |
| 连接池 | ✅ 复杂 | ✅ 简化 | 配置简化 |

## 性能优化

### SQLite优化配置

```python
# 数据库连接优化
import sqlite3
from sqlalchemy import create_engine

engine = create_engine(
    "sqlite:///data/app.db",
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
        "timeout": 20,
        "isolation_level": None
    }
)

# 启用WAL模式
with sqlite3.connect("data/app.db") as conn:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-2000")
    conn.execute("PRAGMA temp_store=memory")
```

### 缓存策略

- 使用Redis处理高频查询缓存
- 实现应用级缓存减少SQLite压力
- 配置合适的SQLite缓存大小

## 回滚方案

如果需要回滚到PostgreSQL：

1. 保留PostgreSQL备份文件
2. 恢复PostgreSQL服务
3. 更新配置文件回退到PostgreSQL连接
4. 验证数据完整性

## 注意事项

1. **并发限制**: SQLite的并发写入能力有限，高并发场景需要测试
2. **事务大小**: 避免过大的事务，可能影响性能
3. **备份策略**: 定期备份SQLite文件
4. **监控监控**: 监控SQLite性能指标，及时发现问题

## 迁移验证清单

- [ ] PostgreSQL数据备份完成
- [ ] SQLite数据库初始化成功
- [ ] 数据迁移无错误
- [ ] 数据完整性验证通过
- [ ] 应用功能测试正常
- [ ] 性能测试满足要求
- [ ] 监控指标正常
- [ ] 备份策略已更新
- [ ] 文档已更新

## 故障排除

### 常见问题

1. **数据库锁定错误**
   ```bash
   # 检查WAL模式
   sqlite3 data/app.db "PRAGMA journal_mode;"

   # 重启应用释放锁
   ```

2. **数据类型转换错误**
   ```python
   # 检查JSON字段格式
   import json
   json.loads(data_string)  # 验证格式
   ```

3. **性能问题**
   ```bash
   # 检查数据库统计信息
   sqlite3 data/app.db "ANALYZE;"

   # 重建索引
   sqlite3 data/app.db "REINDEX;"
   ```

## 后续维护

1. **定期维护**: 执行VACUUM和ANALYZE操作
2. **监控**: 设置SQLite性能监控
3. **备份**: 自动化SQLite文件备份
4. **升级**: 关注SQLite版本更新