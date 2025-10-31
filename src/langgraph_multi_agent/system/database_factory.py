"""数据库连接工厂"""

import logging
import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from typing import Optional
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class DatabaseFactory:
    """数据库连接工厂"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()

    def create_engine(self, database_url: Optional[str] = None) -> Engine:
        """创建数据库引擎"""
        if database_url is None:
            database_url = self.config_manager.get_database_url()

        db_config = self.config_manager.config.database

        # 为SQLite优化连接参数
        if database_url.startswith("sqlite"):
            engine = create_engine(
                database_url,
                poolclass=StaticPool,
                pool_size=db_config.pool_size,
                max_overflow=db_config.max_overflow,
                pool_timeout=db_config.pool_timeout,
                pool_recycle=db_config.pool_recycle,
                echo=db_config.echo,
                connect_args=db_config.connect_args,
            )

            # 启用WAL模式和SQLite优化
            self._enable_sqlite_optimizations(engine)

        else:
            # 其他数据库（虽然已经移除PostgreSQL，但保留兼容性）
            engine = create_engine(
                database_url,
                pool_size=db_config.pool_size,
                max_overflow=db_config.max_overflow,
                pool_timeout=db_config.pool_timeout,
                pool_recycle=db_config.pool_recycle,
                echo=db_config.echo,
            )

        return engine

    def _enable_sqlite_optimizations(self, engine: Engine):
        """启用SQLite性能优化"""
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """设置SQLite PRAGMA配置"""
            cursor = dbapi_connection.cursor()

            try:
                # 启用WAL模式以提高并发性能
                cursor.execute("PRAGMA journal_mode=WAL")

                # 设置同步模式为NORMAL（性能与安全性的平衡）
                cursor.execute("PRAGMA synchronous=NORMAL")

                # 增加缓存大小（-2000表示2MB缓存）
                cursor.execute("PRAGMA cache_size=-2000")

                # 设置临时存储为内存
                cursor.execute("PRAGMA temp_store=memory")

                # 启用外键约束
                cursor.execute("PRAGMA foreign_keys=ON")

                # 设置WAL自动检查点间隔（1000页）
                cursor.execute("PRAGMA wal_autocheckpoint=1000")

                # 优化查询计划器
                cursor.execute("PRAGMA optimize")

                logger.debug("SQLite性能优化已启用")

            except Exception as e:
                logger.warning(f"设置SQLite优化时出错: {e}")
            finally:
                cursor.close()

    def test_connection(self, engine: Engine) -> bool:
        """测试数据库连接"""
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False

    def get_database_info(self, engine: Engine) -> dict:
        """获取数据库信息"""
        try:
            with engine.connect() as conn:
                if engine.url.drivername.startswith("sqlite"):
                    # SQLite信息
                    result = conn.execute("PRAGMA journal_mode").fetchone()
                    journal_mode = result[0] if result else "unknown"

                    result = conn.execute("PRAGMA synchronous").fetchone()
                    synchronous = result[0] if result else "unknown"

                    result = conn.execute("PRAGMA cache_size").fetchone()
                    cache_size = result[0] if result else "unknown"

                    return {
                        "type": "sqlite",
                        "database_url": str(engine.url).replace(engine.url.password or "", "***"),
                        "journal_mode": journal_mode,
                        "synchronous": synchronous,
                        "cache_size": cache_size,
                        "wal_enabled": journal_mode.upper() == "WAL"
                    }
                else:
                    return {
                        "type": engine.url.drivername,
                        "database_url": str(engine.url).replace(engine.url.password or "", "***"),
                    }

        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {
                "type": "unknown",
                "error": str(e)
            }


# 全局实例
_database_factory: Optional[DatabaseFactory] = None


def get_database_factory() -> DatabaseFactory:
    """获取数据库工厂实例"""
    global _database_factory
    if _database_factory is None:
        _database_factory = DatabaseFactory()
    return _database_factory


def create_database_engine(database_url: Optional[str] = None) -> Engine:
    """创建数据库引擎（便捷函数）"""
    return get_database_factory().create_engine(database_url)