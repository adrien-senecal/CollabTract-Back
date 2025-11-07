from pydantic import BaseModel
from typing import Dict, Any
import os

from ..settings import MUNICIPALITIES_DATA_PATH


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    uptime: float
    checks: Dict[str, Any]


def check_database_connection() -> Dict[str, Any]:
    """Check if database/data files are accessible."""
    try:
        # Check if data files exist
        required_files = [
            MUNICIPALITIES_DATA_PATH,
        ]

        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)

        if missing_files:
            return {
                "status": "unhealthy",
                "message": f"Missing data files: {', '.join(missing_files)}",
            }

        return {"status": "healthy", "message": "Data files accessible"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Database check failed: {str(e)}"}
