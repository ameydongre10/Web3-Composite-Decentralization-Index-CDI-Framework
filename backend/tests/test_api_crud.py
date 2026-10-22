import pytest
from httpx import AsyncClient
from backend.app.config import settings

ADMIN_HEADERS = {"X-API-Key": settings.ADMIN_API_KEY}


@pytest.mark.asyncio
class TestProtocolCRUD:
    async def test_create_protocol_success(self, client: AsyncClient):
        payload = {
            "slug": "makerdao",
            "name": "MakerDAO",
            "symbol": "MKR",
            "category": "CDP",
            "chain": "ethereum",
            "contract_address": "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
            "governance_type": "ExecutiveSpell",
            "color": "#1AAB9B",
            "description": "Decentralized stablecoin collateralized vault protocol.",
        }
        res = await client.post("/api/v1/protocols", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 201
        data = res.json()
        assert data["slug"] == "makerdao"
        assert data["name"] == "MakerDAO"
        assert "id" in data

    async def test_create_protocol_duplicate_conflict(self, client: AsyncClient):
        payload = {
            "slug": "duplicate-test",
            "name": "Dup Protocol",
            "symbol": "DUP",
            "category": "DEX",
        }
        res1 = await client.post("/api/v1/protocols", json=payload, headers=ADMIN_HEADERS)
        assert res1.status_code == 201

        # Second creation with identical slug must fail with 409 Conflict
        res2 = await client.post("/api/v1/protocols", json=payload, headers=ADMIN_HEADERS)
        assert res2.status_code == 409

    async def test_create_protocol_unauthorized(self, client: AsyncClient):
        payload = {"slug": "unauth-proto", "name": "Unauth", "symbol": "UNA"}
        res = await client.post("/api/v1/protocols", json=payload)  # No auth headers
        assert res.status_code == 401

    async def test_list_protocols_pagination_and_filter(self, client: AsyncClient):
        res = await client.get("/api/v1/protocols?page=1&page_size=10")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1

    async def test_get_protocol_by_id_and_slug(self, client: AsyncClient):
        payload = {"slug": "fetch-test", "name": "Fetch Test", "symbol": "FTH"}
        res_create = await client.post("/api/v1/protocols", json=payload, headers=ADMIN_HEADERS)
        proto_id = res_create.json()["id"]

        # Fetch by slug
        res_slug = await client.get("/api/v1/protocols/fetch-test")
        assert res_slug.status_code == 200
        assert res_slug.json()["slug"] == "fetch-test"

        # Fetch by id
        res_id = await client.get(f"/api/v1/protocols/{proto_id}")
        assert res_id.status_code == 200
        assert res_id.json()["id"] == proto_id

    async def test_get_nonexistent_protocol_404(self, client: AsyncClient):
        res = await client.get("/api/v1/protocols/nonexistent-protocol-xyz")
        assert res.status_code == 404

    async def test_update_protocol_partial(self, client: AsyncClient):
        payload = {"slug": "update-test", "name": "Initial Name", "symbol": "INIT"}
        res_create = await client.post("/api/v1/protocols", json=payload, headers=ADMIN_HEADERS)
        proto_id = res_create.json()["id"]

        # Partial update
        patch_payload = {"name": "Updated Name", "description": "New description added"}
        res_patch = await client.patch(f"/api/v1/protocols/{proto_id}", json=patch_payload, headers=ADMIN_HEADERS)
        assert res_patch.status_code == 200
        assert res_patch.json()["name"] == "Updated Name"
        assert res_patch.json()["description"] == "New description added"
        assert res_patch.json()["symbol"] == "INIT"  # Preserved unchanged

    async def test_delete_protocol(self, client: AsyncClient):
        payload = {"slug": "delete-test", "name": "To Delete", "symbol": "DEL"}
        res_create = await client.post("/api/v1/protocols", json=payload, headers=ADMIN_HEADERS)
        proto_id = res_create.json()["id"]

        # Delete
        res_del = await client.delete(f"/api/v1/protocols/{proto_id}", headers=ADMIN_HEADERS)
        assert res_del.status_code == 204

        # Verify 404 subsequently
        res_after = await client.get(f"/api/v1/protocols/{proto_id}")
        assert res_after.status_code == 404


@pytest.mark.asyncio
class TestDataSourceCRUD:
    async def test_data_source_lifecycle(self, client: AsyncClient):
        # Create parent protocol
        p_res = await client.post("/api/v1/protocols", json={"slug": "ds-proto", "name": "DS Proto", "symbol": "DSP"}, headers=ADMIN_HEADERS)
        proto_id = p_res.json()["id"]

        # Add data source
        ds_payload = {
            "source_type": "rpc",
            "endpoint_url": "https://eth.llamarpc.com",
            "sync_interval_seconds": 120,
        }
        res_create = await client.post(f"/api/v1/protocols/{proto_id}/data-sources", json=ds_payload, headers=ADMIN_HEADERS)
        assert res_create.status_code == 201
        ds_id = res_create.json()["id"]

        # List data sources
        res_list = await client.get(f"/api/v1/protocols/{proto_id}/data-sources")
        assert res_list.status_code == 200
        assert len(res_list.json()) == 1

        # Patch data source
        res_patch = await client.patch(f"/api/v1/data-sources/{ds_id}", json={"sync_interval_seconds": 300}, headers=ADMIN_HEADERS)
        assert res_patch.status_code == 200
        assert res_patch.json()["sync_interval_seconds"] == 300

        # Delete data source
        res_del = await client.delete(f"/api/v1/data-sources/{ds_id}", headers=ADMIN_HEADERS)
        assert res_del.status_code == 204


@pytest.mark.asyncio
class TestSnapshotsAndAnalytics:
    async def test_calculate_snapshot_and_sensitivity(self, client: AsyncClient):
        # Create protocol
        p_res = await client.post("/api/v1/protocols", json={"slug": "calc-proto", "name": "Calc Proto", "symbol": "CALC"}, headers=ADMIN_HEADERS)
        proto_id = p_res.json()["id"]

        # Calculate snapshot
        calc_payload = {
            "protocol_id": proto_id,
            "custom_weights": {"economic": 0.3, "governance": 0.3, "structural": 0.2, "development": 0.2},
        }
        res_calc = await client.post("/api/v1/snapshots/calculate", json=calc_payload, headers=ADMIN_HEADERS)
        assert res_calc.status_code == 201
        snap = res_calc.json()
        assert "composite_cdi" in snap
        assert 0.0 <= snap["composite_cdi"] <= 1.0
        assert snap["gini_coefficient"] >= 0.0
        assert snap["hhi_points"] >= 0.0

        # Sensitivity analysis
        sens_payload = {
            "protocol_id": proto_id,
            "scenarios": {
                "gov_focus": {"economic": 0.1, "governance": 0.6, "structural": 0.15, "development": 0.15},
                "eco_focus": {"economic": 0.6, "governance": 0.1, "structural": 0.15, "development": 0.15},
            }
        }
        res_sens = await client.post("/api/v1/snapshots/sensitivity", json=sens_payload)
        assert res_sens.status_code == 200
        sens_data = res_sens.json()
        assert "baseline_cdi" in sens_data
        assert "gov_focus" in sens_data["scenario_results"]

        # Temporal drift
        res_drift = await client.get(f"/api/v1/protocols/{proto_id}/temporal-drift")
        assert res_drift.status_code == 200
        assert "drift" in res_drift.json()


@pytest.mark.asyncio
class TestJobsAndAlerts:
    async def test_jobs_lifecycle(self, client: AsyncClient):
        p_res = await client.post("/api/v1/protocols", json={"slug": "job-proto", "name": "Job Proto", "symbol": "JOB"}, headers=ADMIN_HEADERS)
        proto_id = p_res.json()["id"]

        job_payload = {"protocol_id": proto_id, "job_type": "ingestion"}
        res_job = await client.post("/api/v1/jobs", json=job_payload, headers=ADMIN_HEADERS)
        assert res_job.status_code == 202
        job_id = res_job.json()["id"]

        # Fetch job
        res_get = await client.get(f"/api/v1/jobs/{job_id}")
        assert res_get.status_code == 200
        assert res_get.json()["status"] in ["completed", "running"]

    async def test_alerts_lifecycle(self, client: AsyncClient):
        rule_payload = {
            "name": "Test Alert Rule",
            "metric_name": "composite_cdi",
            "condition": "lt",
            "threshold": 0.40,
            "severity": "critical",
        }
        res_create = await client.post("/api/v1/alerts/rules", json=rule_payload, headers=ADMIN_HEADERS)
        assert res_create.status_code == 201
        rule_id = res_create.json()["id"]

        # List rules
        res_list = await client.get("/api/v1/alerts/rules")
        assert res_list.status_code == 200
        assert any(r["id"] == rule_id for r in res_list.json())

        # Delete rule
        res_del = await client.delete(f"/api/v1/alerts/rules/{rule_id}", headers=ADMIN_HEADERS)
        assert res_del.status_code == 204


@pytest.mark.asyncio
class TestHealthAndOverview:
    async def test_health_endpoints(self, client: AsyncClient):
        res_h = await client.get("/api/v1/health")
        assert res_h.status_code == 200
        assert res_h.json()["status"] == "healthy"

        res_r = await client.get("/api/v1/ready")
        assert res_r.status_code == 200
        assert res_r.json()["database"] == "connected"

    async def test_metrics_overview(self, client: AsyncClient):
        res = await client.get("/api/v1/metrics/overview")
        assert res.status_code == 200
        data = res.json()
        assert "avg_cdi" in data
        assert "dimensions" in data
