"""
DAO 数据访问层测试

覆盖：创建记录、按 ID 查询、分页查询（含缺陷类型/日期筛选）、
统计汇总。使用内存 SQLite（conftest 已替换会话工厂）。
"""
from datetime import datetime, timedelta

import pytest

from app.dao.record_dao import DetectionRecordDAO


@pytest.fixture
def dao():
    return DetectionRecordDAO()


def _create(dao, file_name="a.jpg", status="不合格", defect_types=None,
            total_defects=1, created_at=None, **extra):
    kwargs = dict(
        file_name=file_name,
        file_path=f"uploads/{file_name}",
        result_image_path=f"results/{file_name}",
        defect_types={"裂纹": 1} if defect_types is None else defect_types,
        total_defects=total_defects,
        status=status,
        confidence_avg=0.9,
        processing_time=0.5,
    )
    if created_at:
        kwargs["created_at"] = created_at
    kwargs.update(extra)
    return dao.create(**kwargs)


class TestCreateAndQuery:
    def test_create_returns_id(self, dao):
        rid = _create(dao)
        assert rid > 0

    def test_get_by_id(self, dao):
        rid = _create(dao, file_name="record1.jpg")
        rec = dao.get_by_id(rid)
        assert rec is not None
        assert rec["file_name"] == "record1.jpg"
        assert rec["defect_types"] == {"裂纹": 1}
        assert rec["created_at"] is not None

    def test_get_by_id_missing(self, dao):
        assert dao.get_by_id(999999) is None

    def test_update(self, dao):
        rid = _create(dao)
        dao.update(rid, status="合格", total_defects=0)
        rec = dao.get_by_id(rid)
        assert rec["status"] == "合格"
        assert rec["total_defects"] == 0


class TestGetList:
    def test_pagination(self, dao):
        for i in range(5):
            _create(dao, file_name=f"img_{i}.jpg")

        page1 = dao.get_list(page=1, size=2)
        assert page1["total"] == 5
        assert len(page1["items"]) == 2

        page3 = dao.get_list(page=3, size=2)
        assert len(page3["items"]) == 1

        # 倒序：最新的在最前
        assert page1["items"][0]["file_name"] == "img_4.jpg"

    def test_filter_by_defect_type(self, dao):
        _create(dao, file_name="crack.jpg", defect_types={"裂纹": 2})
        _create(dao, file_name="scratch.jpg", defect_types={"划痕": 1})
        _create(dao, file_name="both.jpg", defect_types={"裂纹": 1, "划痕": 1})

        result = dao.get_list(defect_type="裂纹")
        assert result["total"] == 2
        result = dao.get_list(defect_type="划痕")
        assert result["total"] == 2
        result = dao.get_list(defect_type="气泡")
        assert result["total"] == 0

    def test_filter_by_date_range(self, dao):
        old = datetime.now() - timedelta(days=30)
        recent = datetime.now() - timedelta(days=1)
        _create(dao, file_name="old.jpg", created_at=old)
        _create(dao, file_name="recent.jpg", created_at=recent)

        start = (old - timedelta(days=1)).strftime("%Y-%m-%d")
        end = (old + timedelta(days=1)).strftime("%Y-%m-%d")
        result = dao.get_list(start_date=start, end_date=end)
        assert result["total"] == 1
        assert result["items"][0]["file_name"] == "old.jpg"

    def test_invalid_date_format(self, dao):
        with pytest.raises(ValueError):
            dao.get_list(start_date="2026/08/01")


class TestGetStatistics:
    def test_statistics_aggregation(self, dao):
        _create(dao, file_name="fail1.jpg", status="不合格", defect_types={"裂纹": 2, "划痕": 1}, total_defects=3)
        _create(dao, file_name="fail2.jpg", status="不合格", defect_types={"裂纹": 1, "夹杂": 1}, total_defects=2)
        _create(dao, file_name="pass1.jpg", status="合格", defect_types={}, total_defects=0)

        stats = dao.get_statistics()
        assert stats["total_count"] == 3
        assert stats["pass_count"] == 1
        assert stats["fail_count"] == 2
        assert stats["pass_rate"] == round(1 / 3, 4)
        assert stats["today_count"] == 3
        assert stats["defect_distribution"] == {"裂纹": 3, "划痕": 1, "夹杂": 1}
        # 严重程度：裂纹=高(3)，划痕=低(1)，夹杂=中(1)
        assert stats["severity_distribution"] == {"高": 3, "中": 1, "低": 1}
        assert len(stats["daily_trend"]) == 7
        assert stats["daily_trend"][-1]["count"] == 3

    def test_statistics_empty(self, dao):
        stats = dao.get_statistics()
        assert stats["total_count"] == 0
        assert stats["pass_rate"] == 0.0
        assert len(stats["daily_trend"]) == 7
        assert sum(d["count"] for d in stats["daily_trend"]) == 0
