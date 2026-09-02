"""
API 接口测试

覆盖：健康检查、图片上传检测、历史记录分页查询、记录详情、
统计总览、单次检测报告、异常输入（格式错误/超大小/404）。
使用内存数据库 + 假检测器，不依赖训练好的模型。
"""
import json

from tests.conftest import make_image_bytes


def _upload(api_client, filename="product_test.png", content=None):
    """封装上传请求，返回 response"""
    return api_client.post(
        "/api/upload",
        files={"file": (filename, content if content is not None else make_image_bytes(), "image/png")},
    )


class TestHealth:
    def test_health_check(self, api_client):
        resp = api_client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["status"] == "ok"
        assert body["data"]["service"] == "defect-detection-backend"

    def test_root(self, api_client):
        resp = api_client.get("/")
        assert resp.status_code == 200
        assert resp.json()["code"] == 0


class TestUploadDetect:
    def test_upload_success(self, api_client):
        resp = _upload(api_client)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        # 结论与统计（假检测器返回 1 裂纹 + 1 划痕）
        assert data["status"] == "不合格"
        assert data["total_defects"] == 2
        assert data["defect_types"] == {"裂纹": 1, "划痕": 1}
        # 记录与报告
        assert data["record_id"] > 0
        assert data["report_no"].startswith("RPT-")
        # 图片 URL 与检测框
        assert data["original_image_url"].startswith("/uploads/")
        assert data["result_image_url"].startswith("/results/")
        assert len(data["boxes"]) == 2
        assert data["boxes"][0]["class_name"] == "裂纹"
        assert data["image_size"] == {"width": 300, "height": 200}

    def test_upload_invalid_ext(self, api_client):
        resp = _upload(api_client, filename="evil.txt", content=b"not an image")
        assert resp.status_code == 400
        assert resp.json()["code"] == 400

    def test_upload_oversize(self, api_client):
        # 构造 10MB + 1 字节的内容
        big = b"x" * (10 * 1024 * 1024 + 1)
        resp = _upload(api_client, filename="big.png", content=big)
        assert resp.status_code == 400

    def test_upload_empty(self, api_client):
        resp = _upload(api_client, filename="empty.png", content=b"")
        assert resp.status_code == 400


class TestRecords:
    def test_records_pagination(self, api_client):
        for i in range(3):
            assert _upload(api_client, f"img_{i}.png").status_code == 200

        resp = api_client.get("/api/records", params={"page": 1, "size": 2})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["items"]) == 2
        # 字段完整性
        item = data["items"][0]
        for key in ("id", "file_name", "total_defects", "status", "defect_types",
                    "confidence_avg", "processing_time", "created_at",
                    "result_image_url", "original_image_url"):
            assert key in item

    def test_records_filter_by_defect_type(self, api_client):
        _upload(api_client, "a.png")
        resp = api_client.get("/api/records", params={"defect_type": "裂纹"})
        assert resp.json()["data"]["total"] == 1
        resp = api_client.get("/api/records", params={"defect_type": "气泡"})
        assert resp.json()["data"]["total"] == 0

    def test_records_filter_by_date(self, api_client):
        _upload(api_client, "b.png")
        resp = api_client.get(
            "/api/records", params={"start_date": "2000-01-01", "end_date": "2099-12-31"}
        )
        assert resp.json()["data"]["total"] >= 1
        resp = api_client.get(
            "/api/records", params={"start_date": "2000-01-01", "end_date": "2000-01-02"}
        )
        assert resp.json()["data"]["total"] == 0

    def test_record_detail_and_404(self, api_client):
        record_id = _upload(api_client, "c.png").json()["data"]["record_id"]
        resp = api_client.get(f"/api/records/{record_id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["record"]["id"] == record_id
        assert data["report"] is not None
        assert data["report"]["report_no"].startswith("RPT-")

        resp = api_client.get("/api/records/999999")
        assert resp.status_code == 404


class TestStatistics:
    def test_statistics_overview(self, api_client):
        _upload(api_client, "d.png")
        resp = api_client.get("/api/statistics/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_count"] == 1
        assert data["fail_count"] == 1
        assert data["pass_count"] == 0
        assert 0 <= data["pass_rate"] <= 1
        assert data["today_count"] == 1
        assert data["defect_distribution"] == {"裂纹": 1, "划痕": 1}
        assert data["severity_distribution"] == {"高": 1, "中": 0, "低": 1}
        assert len(data["daily_trend"]) == 7

    def test_statistics_report(self, api_client):
        record_id = _upload(api_client, "e.png").json()["data"]["record_id"]
        resp = api_client.get(f"/api/statistics/report/{record_id}")
        assert resp.status_code == 200
        report = resp.json()["data"]
        assert report["report_title"] == "智能车间产品外观缺陷检测报告"
        assert report["conclusion"]["status"] == "不合格"
        assert len(report["defect_details"]) == 2
        assert report["inspector"]["model"] == "YOLOv8"

    def test_statistics_report_404(self, api_client):
        resp = api_client.get("/api/statistics/report/999999")
        assert resp.status_code == 404
