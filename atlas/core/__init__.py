def __init__(self):

    self.config = AtlasConfig()

    self.logger = get_logger("ATLAS")

    self.registry = AgentRegistry()

    self.registry.register(NewsAnalyst())

    self.analysis_service = AnalysisService(self.registry)