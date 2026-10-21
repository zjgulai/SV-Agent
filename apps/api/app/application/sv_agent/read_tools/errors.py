class ReadToolSourceFailure(Exception):
    def __init__(self, stable_error_code: str, recovery_action: str) -> None:
        super().__init__(stable_error_code)
        self.stable_error_code = stable_error_code
        self.recovery_action = recovery_action
