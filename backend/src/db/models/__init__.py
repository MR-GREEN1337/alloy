from .user import User
from .report import Report, ReportStatus
from .analysis import ReportAnalysis, CultureClash, UntappedGrowth, ClashSeverity

__all__ = [
    "User",
    "Report",
    "ReportStatus",
    "ReportAnalysis",
    "CultureClash",
    "UntappedGrowth",
    "ClashSeverity",
]

# Verify that all models are properly loaded
def verify_models():
    """Verify that all expected models are loaded and registered."""
    missing_models = [model for model in __all__ if model not in globals()]
    if missing_models:
        raise ImportError(
            f"Failed to import the following models: {', '.join(missing_models)}"
        )


# Run verification when the module is imported
verify_models()
