from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any
from uuid import UUID


@dataclass
class Exchange:
    exchange_id: str 
    exchange_name: str
    exchange_description: str
    exchange_metadata: Dict[str, Any] = field(default_factory=dict)
    exchange_urls: Dict[str, Any] = field(default_factory=dict)
    exchange_config: Dict[str, Any] = field(default_factory=dict)
    exchange_stats: Dict[str, Any] = field(default_factory=dict)
    exchange_subjects: List[Any] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Exchange":
        return Exchange(
            exchange_id=str(data.get("exchange_id")),
            exchange_name=data.get("exchange_name", ""),
            exchange_description=data.get("exchange_description", ""),
            exchange_metadata=data.get("exchange_metadata", {}) or {},
            exchange_urls=data.get("exchange_urls", {}) or {},
            exchange_config=data.get("exchange_config", {}) or {},
            exchange_stats=data.get("exchange_stats", {}) or {},
            exchange_subjects=data.get("exchange_subjects", []) or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
