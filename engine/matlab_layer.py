import matlab.engine


class MatlabLayer:
    # Singleton instance of the MATLAB engine
    _eng = None

    @classmethod
    def launch(cls):
        if cls._eng is None:
            cls._eng = matlab.engine.start_matlab()
        return cls._eng

    @classmethod
    def execute(cls, command, nargout=0):
        if cls._eng is None:
            raise RuntimeError("MATLAB engine not launched. Call MatlabEngine.launch() first.")
        try:
            return cls._eng.eval(command, nargout=nargout)
        except Exception as e:
            raise RuntimeError(f"MATLAB error during command:\n  {command}\n  {e}") from e

    @classmethod
    def is_alive(cls):
        try:
            cls._eng.eval("1+1;", nargout=0)
            return True
        except Exception:
            return False

    @classmethod
    def exit(cls):
        if cls._eng is not None:
            cls._eng.quit()
            cls._eng = None

if __name__ == "__main__":
    MatlabLayer.launch()
    print("MATLAB engine launched successfully.")
    print(MatlabLayer.is_alive())  # Test if engine is responsive
    print("Is alive")
    MatlabLayer.exit()
    print("MATLAB engine exited successfully.")
