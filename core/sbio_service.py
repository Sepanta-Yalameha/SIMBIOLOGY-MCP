import matlab.engine

class SbioService:
    def __init__(self):
        self.eng = matlab.engine.start_matlab()

    def list_sbiomodels(self, sbproj_path):
        # Load the project