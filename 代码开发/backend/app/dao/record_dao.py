"""
检测记录数据访问层（DAO）

所有方法自行用 SessionLocal 管理数据库会话，异常时回滚并记录日志。
测试时可通过替换 DetectionRecordDAO.session_factory 使用内存数据库。
"""
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import String, func

from app.database import SessionLocal
from app.models.detection_record import DetectionRecord
from app.algorithms.defect_mapping import get_severity_by_name
from app.utils.logger import get_logger

logger = get_logger("record_dao")


class DetectionRecordDAO:
    """DetectionRecord 表的数据访问封装"""

    # 会话工厂（测试环境可替换为内存数据库会话）
    session_factory = SessionLocal

    # ---------------- 增 ----------------

    def create(self, **kwargs: Any) -> int:
        """插入一条检测记录，返回记录 ID"""
        session = self.session_factory()
        try:
            record = DetectionRecord(**kwargs)
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info("检测记录已入库: id=%s, 文件名=%s", record.id, record.file_name)
            return record.id
        except Exception as e:
            session.rollback()
            logger.exception("创建检测记录失败: %s", e)
            raise
        finally:
            session.close()

    def update(self, record_id: int, **kwargs: Any) -> None:
        """按 ID 更新记录的部分字段"""
        session = self.session_factory()
        try:
            row = session.get(DetectionRecord, record_id)
            if row is None:
                raise ValueError(f"记录不存在: {record_id}")
            for key, value in kwargs.items():
                setattr(row, key, value)
            session.commit()
            logger.info("检测记录已更新: id=%s, 字段=%s", record_id, list(kwargs.keys()))
        except Exception as e:
            session.rollback()
            logger.exception("更新检测记录失败: id=%s, %s", record_id, e)
            raise
        finally:
            session.close()

    # ---------------- 查 ----------------

    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """按 ID 查询单条记录，返回字典；不存在返回 None"""
        session = self.session_factory()
        try:
            row = session.get(DetectionRecord, record_id)
            return row.to_dict() if row else None
        except Exception as e:
            session.rollback()
            logger.exception("按ID查询失败: id=%s, %s", record_id, e)
            raise
        finally:
            session.close()

    def get_list(
        self,
        page: int = 1,
        size: int = 10,
        defect_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        分页查询，支持按缺陷类型和日期范围（含当天）筛选。
        返回 {"total": 总条数, "items": [记录字典]}，按检测时间倒序。
        """
        session = self.session_factory()
        try:
            query = session.query(DetectionRecord)

            # 缺陷类型筛选：defect_types 为 JSON {"裂纹": 2}，SQLite 按文本存储，
            # 用 LIKE 匹配键名即可判断该记录是否包含此缺陷类型
            if defect_type:
                query = query.filter(
                    DetectionRecord.defect_types.cast(String).like(f'%"{defect_type}"%')
                )

            # 日期范围筛选（start_date <= created_at < end_date+1天，含当天）
            if start_date:
                try:
                    query = query.filter(DetectionRecord.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))
                except ValueError:
                    raise ValueError(f"start_date 格式错误（应为 YYYY-MM-DD）: {start_date}")
            if end_date:
                try:
                    dt_end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                except ValueError:
                    raise ValueError(f"end_date 格式错误（应为 YYYY-MM-DD）: {end_date}")
                query = query.filter(DetectionRecord.created_at < dt_end)

            total = query.count()
            rows = (
                query.order_by(DetectionRecord.created_at.desc(), DetectionRecord.id.desc())
                .offset((page - 1) * size)
                .limit(size)
                .all()
            )
            logger.info(
                "分页查询完成: page=%s size=%s 缺陷类型=%s 日期=%s~%s, 共 %s 条",
                page, size, defect_type, start_date, end_date, total,
            )
            return {"total": total, "items": [r.to_dict() for r in rows]}
        except ValueError:
            raise
        except Exception as e:
            session.rollback()
            logger.exception("分页查询失败: %s", e)
            raise
        finally:
            session.close()

    # ---------------- 统计 ----------------

    def get_statistics(self) -> Dict[str, Any]:
        """
        统计汇总，返回：
          total_count           总检测数
          pass_count/fail_count 合格/不合格数
          pass_rate             合格率
          today_count           今日检测数
          defect_distribution   各缺陷类型累计数量
          severity_distribution 严重程度分布（高/中/低）
          daily_trend           近 7 天日检测趋势（含今天，缺省补 0）
        """
        session = self.session_factory()
        try:
            total = session.query(func.count(DetectionRecord.id)).scalar() or 0
            pass_count = (
                session.query(func.count(DetectionRecord.id))
                .filter(DetectionRecord.status == "合格")
                .scalar()
                or 0
            )
            today_start = datetime.combine(date.today(), time.min)
            today_count = (
                session.query(func.count(DetectionRecord.id))
                .filter(DetectionRecord.created_at >= today_start)
                .scalar()
                or 0
            )

            # 近 7 天趋势（含今天），按天分组，缺失日期补 0
            seven_days_ago = today_start - timedelta(days=6)
            grouped = (
                session.query(func.date(DetectionRecord.created_at), func.count(DetectionRecord.id))
                .filter(DetectionRecord.created_at >= seven_days_ago)
                .group_by(func.date(DetectionRecord.created_at))
                .all()
            )
            trend_map = {str(d): int(c) for d, c in grouped}
            daily_trend: List[Dict[str, Any]] = []
            for i in range(6, -1, -1):
                day_str = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
                daily_trend.append({"date": day_str, "count": trend_map.get(day_str, 0)})

            # 缺陷类型分布：从 JSON 列聚合（演示规模数据量小，Python 聚合清晰可靠）
            defect_distribution: Dict[str, int] = {}
            for (defect_types,) in session.query(DetectionRecord.defect_types).all():
                if isinstance(defect_types, dict):
                    for name, cnt in defect_types.items():
                        defect_distribution[name] = defect_distribution.get(name, 0) + int(cnt or 0)

            severity_distribution = {"高": 0, "中": 0, "低": 0}
            for name, cnt in defect_distribution.items():
                sev = get_severity_by_name(name)
                severity_distribution[sev] = severity_distribution.get(sev, 0) + cnt

            pass_rate = round(pass_count / total, 4) if total else 0.0

            result = {
                "total_count": int(total),
                "pass_count": int(pass_count),
                "fail_count": int(total - pass_count),
                "pass_rate": pass_rate,
                "today_count": int(today_count),
                "defect_distribution": defect_distribution,
                "severity_distribution": severity_distribution,
                "daily_trend": daily_trend,
            }
            logger.info("统计汇总完成: 总数=%s 合格=%s 合格率=%s", result["total_count"], result["pass_count"], pass_rate)
            return result
        except Exception as e:
            session.rollback()
            logger.exception("统计汇总失败: %s", e)
            raise
        finally:
            session.close()
