from bs4 import BeautifulSoup
import pandas as pd
import requests

class  GameDay:
    def __init__(self, post_id: int, day_number:int, post: requests.get):

        self.post_id      = post_id
        self.day_number   = day_number
        self.players      = self.get_player_list(post)

        # When players are even, majority is players / 2 + 1
        # When players are odd,  majority is players  / 2 rounded up
        
        if (len(self.players) % 2) == 0:
            self.majority = int(len(self.players) / 2) + 1
        else:
            self.majority = int(round(len(self.players)/2, 0))
        
        

    def get_player_list(self, parser) -> list():
        '''
        Parses opening day post to get a list of active players. We are sent
        an http get request with the day post. This way, we can recycle a previous
        request.
        '''
        self._response = BeautifulSoup(parser.text, 'html.parser')
        self._all_posts = self._response.find_all('div', attrs={'data-num':True,
                                                                'data-autor':True})
        
        self._player_list = []

        for self._post in self._all_posts:

            ##We found the post of interest
            if int(self._post['data-num']) == self.post_id: 

                # Get the first list. It should be the player lists according to the templace
                self._players = self._post.find('ol').find_all('a')

                for self._player in self._players:
                    self._player_list.append(self._player.contents[0])

                return self._player_list



    def vote_player(self, victim:str, player:str, post:int):
        '''
        Keeps track of votes.
        
        if  'desvoto' in victim.lower(): #This is easier for pple using dots after vote.
            print(player, 'is unvoting.')
        
        if  'no linchamiento' in victim.lower():
            print(player, 'chose not to lynch!')
        
        if victim in self.players: ## Oho, it's a valid victim


        


        print(f'{player} voted {victim} at {post}')
        '''