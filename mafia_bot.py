import requests
import time
import re

from bs4 import BeautifulSoup
import pandas as pd

class MafiaBot:

    def __init__(self, game_url: str, game_master: str, loop_waittime_seconds:int):

        print('Mafia MV Bot started!')
        print('Game run by:', game_master)

        self.game_thread           = game_url
        self.game_master           = game_master

        self._current_day_start_post  = 1
        self.player_list              = []

        # Load vote rights table
        self.vote_rights = pd.read_csv('vote_config.csv', sep=',')
        self.vote_rights.set_index('player', inplace=True)

        # Initialize empty vote table
        self.vote_table = pd.DataFrame(columns=['player', 'voted_by', 'post_id'])

        self.majority_reached         = False

        self.run(loop_waittime_seconds)
    
    def run(self, update_tick:int):

        while(True):

            if self.is_day_phase(): # Daytime, count

                print('Starting vote count...')

                self._start_page = self.get_page_number_from_post(self._current_day_start_post)
                self._page_count = self.request_page_count()

                print('Detected day start at page:', self._start_page)

                for self._cur_page in range(self._start_page, (self._page_count + 1)):

                    print('Checking page:', self._cur_page)
                    self.get_votes_from_page(self._cur_page)

                print('Finished counting.')
                
            
            print('Sleeping for', update_tick, 'seconds.')   
            time.sleep(10)
    


    def is_day_phase(self) -> bool:
        '''
        Attempt to parse h2 tags in GM posts to get the current  phase.
        It will set some flags for the main loop.
        '''

        self._is_day_phase     = False

        self._gm_posts         = self.game_thread + '?u=' + self.game_master
        self._gm_posts         = requests.get(self._gm_posts).text

        # Get total gm pages
        self._gm_pages = self.get_page_count_from_page(self._gm_posts)

        # We'll start looping from the last page to the previous one
        for self._pagenum in range(self._gm_pages, 0, -1):

            self._request      = f'{self.game_thread}?u={self.game_master}&pagina={self._pagenum}'
            self._request      = requests.get(self._request).text
            self._current_page = BeautifulSoup(self._request, 'html.parser')

            #TODO: log these iterations?
            self._posts        = self._current_page.find_all('div', attrs={'data-num':True,
                                                                          'data-autor':True})
          
            for self._post in reversed(self._posts): #from more recent to older posts

                self._headers = self._post.find_all('h2') #get all GM h2 headers

                for self._pday in self._headers:

                    self._phase_end     = re.findall('^Final del día [0-9]*', self._pday.text)
                    self._phase_start   = re.findall('^Día [0-9]*', self._pday.text)

                    if self._phase_end:
                        return self._is_day_phase
                      
                    elif self._phase_start: 

                        #TODO: We should start thinking about an standalone method here
                        self._current_day_start_post = int(self._post['data-num'])
                        self._is_day_phase = True
                        self.player_list = self.get_player_list(self._current_day_start_post)

        return self._is_day_phase


    def get_votes_from_page(self, page_to_scan:int):

        self._parsed_url = f'{self.game_thread}/{page_to_scan}'
        self._request    = requests.get(self._parsed_url).text
        
        self._parser = BeautifulSoup(self._request, 'html.parser')

        # MV has unqiue div elements for odd and even posts, 
        # and another one for the very first post of the page.
        # I'm ignoring edit div elements because players should not edit while
        # playing.

        self._posts = self._parser.findAll('div', class_ = ['cf post',
                                                'cf post z',
                                                'cf post first'
                                                ])

        for self._post in self._posts:
            self._author  = self._post['data-autor']
            self._post_id = int(self._post['data-num'])
            self._post_content = self._post.find('div', class_ = 'post-contents')
            self._post_paragraphs = self._post_content.findAll('p')
            self._victim = ''

            for self._paragraph  in self._post_paragraphs:

                if len(self._paragraph.findAll('strong')) > 0:
                    
                    for self._bolded_paragraph in self._paragraph.findAll('strong'):

                        if 'desvoto' in self._bolded_paragraph.text.lower():
                            self._victim = 'desvoto'
                        
                        elif 'no linchamiento' in self._bolded_paragraph.text.lower():
                            self._victim = 'no_lynch' 
                        
                        elif 'voto' in self._bolded_paragraph.text.lower():
                            self._victim = self._bolded_paragraph.text.split(' ')[-1]
                    
                        if self._victim != '': # Call votecount routine here
                            self.vote_player(self._author, self._victim, self._post_id)



    def request_page_count(self):
        '''
        Gets page count by performing a standalone request to the game
        thread. Then, get_page_count_from page is called to retrieve
        the page count.
        '''

        self._request = requests.get(self.game_thread).text
        self._page_count = self.get_page_count_from_page(self._request)

        return self._page_count


    def get_page_count_from_page(self, request_text):
        #Let's try to parse the page count from the bottom  page panel
        self._page_count = 1
        try:
            self._panel_layout = BeautifulSoup(request_text, 'html.parser') 
            self._panel_layout = self._panel_layout.find('div', id = 'bottompanel')

            # get all <a> elements. Ours is the second last in the list
            self._result = self._panel_layout.find_all('a')[-2].contents[0]
            self._page_count = int(self._result)
        
        except:
            print('Warning: cannot get total page count. Single page thread?')
            self._page_count = 1
        
        return self._page_count


    def get_page_number_from_post(self, post_id:int):

        self._page_number = int(round(post_id / 30))
        return self._page_number


    def get_player_list(self, start_day_post_id:int) -> list():
        '''
        Parses opening day post to get a list of active players. We are sent
        an http get request with the day post. This way, we can recycle a previous
        request.
        '''
        self._start_day_page = self.get_page_number_from_post(start_day_post_id)

        self._request_url = f'{self.game_thread}/{self._start_day_page}'
        self._request     = requests.get(self._request_url).text

        self._response  = BeautifulSoup(self._request, 'html.parser')
        self._all_posts = self._response.find_all('div', attrs={'data-num':True,
                                                                'data-autor':True})
        
        self._player_list = []

        for self._post in self._all_posts:

            ##We found the post of interest
            if int(self._post['data-num']) == start_day_post_id: 

                # Get the first list. It should be the player lists according to the templace
                self._players = self._post.find('ol').find_all('a')

                for self._player in self._players:
                    self._player_list.append(self._player.contents[0])

                return self._player_list


    def is_valid_vote(self, player:str, victim:str) -> bool:

        self._is_valid_vote = False

        if not self.majority_reached:

            if player in self.player_list or player == self.game_master:

                if player == self.game_master:
                    self._player_max_votes = 999
                else:
                    self._player_max_votes = self.vote_rights.loc[player, 'allowed_votes']

                self._player_current_votes = len(self.vote_table[self.vote_table['voted_by'] == player])
            
                if victim == 'desvoto' and self._player_current_votes > 0:
                    self._is_valid_vote = True
            
                elif victim  == 'no_lynch' and self._player_current_votes < self._player_max_votes:
                    self._is_valid_vote  = True
            
                elif victim in self.player_list:

                    if victim in self.vote_rights.index:
                        if self.vote_rights.loc[victim, 'can_be_voted'] == 1:
                            if self._player_current_votes < self._player_max_votes:
                                self._is_valid_vote = True
                    else:
                        print('Warning: player', victim, 'is not on the vote rights table.')
    
        return self._is_valid_vote

    
    def is_lynched(self, victim:str) -> bool:
        '''
        Check if this player has reached lynch majority to be lynched
        '''
        self._lynched = False

        # Count this player votes
        self._lynch_votes = len(self.vote_table[self.vote_table['player'] == victim])
        self._player_majority = self.get_vote_majority() + self.vote_rights.loc[victim, 'mod_to_lynch']

        if self._lynch_votes >= self._player_majority:
            self._lynched = True
        
        return self._lynched

    
    def vote_player(self, player:str, victim:str, post_id:int):

        if self.is_valid_vote(player, victim):

            if victim == 'desvoto':
                self._old_vote = self.vote_table[self.vote_table['voted_by'] == player].index[0]
                self.vote_table.drop(self._old_vote, axis=0, inplace=True)
                print(player, 'unvoted.')
            
            else:
                self.vote_table  = self.vote_table.append({'player': victim,
                                                           'voted_by': player,
                                                           'post_id': post_id},
                                                           ignore_index=True)
                
                print(player, 'voted', self._victim)

                #Check if we have reached majority
                if self.is_lynched(self._victim):
                    self.majority_reached = True    
        else:
            print('Invalid vote by', player, 'at', post_id, 'They voted', self._victim)


    def get_vote_majority(self) -> int:

        # When players are even, majority is players / 2 + 1
        # When players are odd,  majority is players  / 2 rounded up  
        
        if (len(self.player_list) % 2) == 0:
            self._majority = int(len(self.player_list) / 2) + 1
        else:
            self._majority = int(round(len(self.player_list)/2, 0))

        return self._majority