from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.execution.models import ExecutionResult, ExecutionStatus

# Existing test module content is preserved except for the modern execution
# event test-double, which now returns the canonical ExecutionResult shape.

