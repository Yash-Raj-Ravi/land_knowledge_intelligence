import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from backend.models.anomaly import AnomalyItem, AnomalyProviderResponse

logger = logging.getLogger(__name__)


class BaseAnomalyProvider(ABC):
    """Abstract boundary interface for anomaly detection providers."""

    @abstractmethod
    def fetch_parcel_anomalies(self, parcel_id: str) -> List[AnomalyItem]:
        pass

    @abstractmethod
    def fetch_project_anomalies(self, project_id: str) -> List[AnomalyItem]:
        pass


class LocalAnomalyProvider(BaseAnomalyProvider):
    """
    Local / Registered anomaly provider.
    Provides mock and registered parcel anomalies for testing and local integration.
    """

    def __init__(self):
        # Demo anomaly fixture for PCL-VADADALA-142-3A
        self._demo_anomalies = {
            "PCL-VADADALA-142-3A": [
                AnomalyItem(
                    parcel_id="PCL-VADADALA-142-3A",
                    project_id="PRJ-NHAI-2024",
                    anomaly_type="Area Discrepancy",
                    severity="high",
                    field="area_hectares",
                    expected_value="0.4500 Ha",
                    observed_value="0.5200 Ha",
                    source="Land Area Validation Model",
                    confidence=0.92,
                    status="open"
                )
            ]
        }

    def fetch_parcel_anomalies(self, parcel_id: str) -> List[AnomalyItem]:
        pid_upper = parcel_id.upper()
        for k, items in self._demo_anomalies.items():
            if k.upper() == pid_upper or parcel_id in k:
                return items
        return []

    def fetch_project_anomalies(self, project_id: str) -> List[AnomalyItem]:
        pid_upper = project_id.upper()
        result = []
        for items in self._demo_anomalies.values():
            for item in items:
                if item.project_id and item.project_id.upper() == pid_upper:
                    result.append(item)
        return result


class FailingAnomalyProvider(BaseAnomalyProvider):
    """Provider mock to simulate external service outage for fault tolerance testing."""

    def fetch_parcel_anomalies(self, parcel_id: str) -> List[AnomalyItem]:
        raise ConnectionError("External Anomaly Detection Service connection timeout.")

    def fetch_project_anomalies(self, project_id: str) -> List[AnomalyItem]:
        raise ConnectionError("External Anomaly Detection Service connection timeout.")


class AnomalyService:
    """
    Fault-Tolerant Anomaly Service Wrapper.
    Uses abstract BaseAnomalyProvider so local or external providers can be swapped.
    Ensures main intelligence APIs never fail if the anomaly service is down.
    """

    def __init__(self, provider: Optional[BaseAnomalyProvider] = None):
        self.provider = provider or LocalAnomalyProvider()

    def get_anomalies_for_parcel(self, parcel_id: str) -> AnomalyProviderResponse:
        try:
            items = self.provider.fetch_parcel_anomalies(parcel_id)
            return AnomalyProviderResponse(
                service_status="online",
                anomalies=items,
                message=f"Retrieved {len(items)} anomaly record(s)."
            )
        except Exception as e:
            logger.warning(f"Anomaly service unavailable for parcel '{parcel_id}': {e}")
            return AnomalyProviderResponse(
                service_status="unavailable",
                anomalies=[],
                message=f"Anomaly service unavailable: {str(e)}"
            )

    def get_anomalies_for_project(self, project_id: str) -> AnomalyProviderResponse:
        try:
            items = self.provider.fetch_project_anomalies(project_id)
            return AnomalyProviderResponse(
                service_status="online",
                anomalies=items,
                message=f"Retrieved {len(items)} anomaly record(s)."
            )
        except Exception as e:
            logger.warning(f"Anomaly service unavailable for project '{project_id}': {e}")
            return AnomalyProviderResponse(
                service_status="unavailable",
                anomalies=[],
                message=f"Anomaly service unavailable: {str(e)}"
            )
