from interfaces.telegram_bot.formatting import format_health
from rag_core.healthcheck import HealthReport, ServiceStatus


def test_all_ok_when_every_service_ok():
    report = HealthReport(services=[ServiceStatus(name="qdrant", ok=True)])
    assert report.all_ok is True


def test_not_all_ok_when_one_service_down():
    report = HealthReport(
        services=[ServiceStatus(name="qdrant", ok=True), ServiceStatus(name="ollama", ok=False, detail="timeout")]
    )
    assert report.all_ok is False


def test_format_health_all_up():
    report = HealthReport(services=[ServiceStatus(name="qdrant", ok=True)])
    assert format_health(report) == "All services are up."


def test_format_health_lists_down_services_with_detail():
    report = HealthReport(services=[ServiceStatus(name="qdrant", ok=False, detail="connection refused")])
    out = format_health(report)
    assert "qdrant: DOWN" in out
    assert "connection refused" in out
