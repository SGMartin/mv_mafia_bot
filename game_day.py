from bs4 import BeautifulSoup
import pandas as pd
import requests

class  GameDay:
    def __init__(self, game_day:int, post_id: int, day_start_post):

        self.post_id            = post_id
        self.majority_reached   = False
        self.day                = game_day

        # Load vote rights table
        self.vote_rights = pd.read_csv('vote_config.csv', sep=',')
        self.vote_rights.set_index('player', inplace=True)

        self.alive_players      = self.get_player_list(day_start_post)

        # When players are even, majority is players / 2 + 1
        # When players are odd,  majority is players  / 2 rounded up  
        
        if (len(self.alive_players) % 2) == 0:
            self.majority = int(len(self.alive_players) / 2) + 1
        else:
            self.majority = int(round(len(self.alive_players)/2, 0))
        
        # Create vote count table
        self.vote_table = pd.DataFrame(columns=['player', 'voted_by', 'post_id'])

        print('Alive players:', self.alive_players)    

    def get_player_list(self, post_text) -> list():
        '''
        Parses opening day post to get a list of active players. We are sent
        an http get request with the day post. This way, we can recycle a previous
        request.
        '''
        self._response = BeautifulSoup(post_text, 'html.parser')
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



    def is_valid_vote(self, player:str, victim:str) -> bool:
        '''
        Check if a casted vote is legit
        '''
        self._is_valid_vote = False

        if not self.majority_reached:

            if player in self.alive_players:

                self._player_max_votes = self.vote_rights.loc[player, 'allowed_votes']
                self._player_current_votes = len(self.vote_table[self.vote_table['voted_by'] == player])
            
                if victim.lower() in 'desvoto' and self._player_current_votes > 0:
                    self._is_valid_vote = True
            
                if victim.lower() in 'no linchamiento' and self._player_current_votes < self._player_max_votes:
                    self._is_valid_vote  = True
            
                if victim in self.alive_players:
                    if self.vote_rights.loc[victim, 'can_be_voted'] == 1:
                        if self._player_current_votes < self._player_max_votes:
                            self._is_valid_vote = True
    
        return self._is_valid_vote

                

    def is_lynched(self, victim:str) -> bool:
        '''
        Check if this player has reached lynch majority to be lynched
        '''
        self._lynched = False

        # Count this player votes
        self._lynch_votes = len(self.vote_table[self.vote_table['player'] == victim])
        self._player_majority = self.majority + self.vote_rights.loc[victim, 'mod_to_lynch']

        if self._lynch_votes >= self._player_majority:
            self._lynched = True
        
        return self._lynched



    def vote_player(self, player:str, victim:str, post_id:int):

        if self.is_valid_vote(player, victim):

            if victim.lower() in  'desvoto':
                self._old_vote = self.vote_table[self.vote_table['voted_by'] == player].index[0]
                self.vote_table.drop(self._old_vote, axis=0, inplace=True)
                print(player, 'unvoted.')
            
            else:
                self._victim = victim

                if victim.lower() in 'no linchamiento':
                    self._victim = 'no_lynch'

                self.vote_table  = self.vote_table.append({'player': self._victim,
                                                           'voted_by': player,
                                                           'post_id': post_id},
                                                           ignore_index=True)
                
                print(player, 'voted', self._victim)

                #Check if we have reached majority
                if self.is_lynched(self._victim):
                    self.majority_reached = True        

        else:
            print('Invalid vote by', player, 'at', post_id, 'They voted', victim)
    
    #TODO: track vote history and save it here.
    def end_game_day(self):
        '''
        If the day has ended, we should save the current vote count to a file.
        '''
        self._file_name = f'day_{self.day}_last_count.csv'
        self.vote_table.to_csv(self._file_name, sep=',', index=False)


           

