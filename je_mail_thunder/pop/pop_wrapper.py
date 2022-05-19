from poplib import POP3_SSL


class POPWrapper(POP3_SSL):

    def __init__(self, host: str):
        super().__init__(host)

    

