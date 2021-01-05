class VoteCountRequest:
    def __init__(self, author:str, from_post:int, to_post:int, of_who:str, day:int):

        self.author = author
        