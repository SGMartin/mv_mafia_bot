import os.path
import requests
import re
import time


from bs4 import BeautifulSoup
import pandas as pd

import game_day

class MafiaBot:

    def __init__(self, game_url: str, gm: str, loop_waittime_seconds:int):

        print('MV MafiaBot started')

        #Initialize vars
        self.game_title           = 'Unknown'
        self.game_thread          = game_url
        self.game_master          = gm
        self.page_count           =  1
        
        self.current_game_day          = None
        self.day_ended                 = False

        # Let's set some limits here
        if loop_waittime_seconds < 60:
            self.loop_waittime_seconds = 60
        else:
            self.loop_waittime_seconds = loop_waittime_seconds

        # Get thread id
        self.thread_id = self.get_thread_id_from_url(self.game_thread)

        #Load game database
        self.database  = self.load_database(self.thread_id)

        # Fire the bot up
       # self.run(self.loop_waittime_seconds)
        self.run(10)

    def get_thread_id_from_url(self, url:str) -> str:
        '''
        TODO: docs
        '''
        self._thread_id           = -1
        self._name_and_thread_id = url.split('/')[5]
   
        try:
            self._thread_id = int(self._name_and_thread_id.split('-')[-1])
        except:
            print('Could not parse thread id... Wrong thread url?')
            #TODO: Exit bot here
        
        return self._thread_id


    def load_database(self, thread_id):
        '''
        We'll attempt to load this game database. If not found, we'll assume
        we are being initialized for the first time.
        '''
        self.database_path = 'mafia_' + str(thread_id) + '.csv'
        
        if os.path.exists(self.database_path):

            self._database = pd.read_csv(filepath_or_buffer=self.database_path, sep=',')
            self._database.set_index('record', inplace=True)
            print('Database found for this game!')

        else:
            print('No data found for this game... starting from scratch')
            self._database  = pd.DataFrame({'record': ['last_page'], 'value':[1]})
            self._database.set_index('record', inplace=True)

        return self._database


    def run(self, seconds_interval):

        self._failed_runs   = 0

        while(True):

            while(not self.day_ended):
                
                # Launch day phase routine
                self.check_current_phase()

                # Get last page checked. Will default to 1 if a database was not found
                self.current_page =  int(self.database.loc['last_page', 'value'])


             
               
  
    def start_game_phase(self, post_id:int, day_number:int, day_start_post):
        
        print('Day started!')

        self.day_ended = False
        self.current_game_day = game_day.GameDay(game_day=day_number,
                                                 post_id=post_id,
                                                 day_start_post=day_start_post)

       

    def end_game_phase(self, post_id:int):

        print('Ending day:', post_id)
        self.day_ended = True
        
        # Update the database
        self.database.loc['day', 'value']  = self.current_game_day.day
        self.current_game_day.end_game_day()
        


    def get_game_title(self, request_text):
        # Get game name
        self._game_title = BeautifulSoup(request_text, 'html.parser')
        self._game_title = self._game_title.find('title').text

        # Remove the trailing '| Mediavida'
        self._game_title = self._game_title.split('|')[0]

        return self.game_title


    def get_page_count(self, request_text):
        #Let's try to parse the page count from the bottom  page panel
        self._page_count = 1
        try:
            self._panel_layout = BeautifulSoup(request_text, 'html.parser') 
            self._panel_layout = self._panel_layout.find('div', id = 'bottompanel')

            # get all <a> elements. Ours is the second last in the list
            self._result = self._panel_layout.find_all('a')[-2].contents[0]
            self._page_count = int(self._result)
        
        #TODO: we should actually check if there is only one page or networking problem.
        except:
            print('Warning... single page thread?')
            self._page_count = 1
        
        return self._page_count


    def count_votes_from_page(self, request_text):
        
        self._parser = BeautifulSoup(request_text, 'html.parser')
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

            for self._paragraph  in self._post_paragraphs:
                if len(self._paragraph.findAll('strong')) > 0:
                   for self._bolded_paragraph in self._paragraph.findAll('strong'):    
                       ## Ok, possible vote here. Call process_vote for
                       ## further checks
                       print('Method call for vote routine here!')
                       
     
    
    def check_current_phase(self) -> int:
        '''
        Attempt to parse h2 tags in GM posts to get the current  phase.
        It will set some flags for the main loop.
        '''
        self._current_day = 0

        self._gm_posts  = self.game_thread + '?u=' + self.game_master
        self._gm_posts  = requests.get(self._gm_posts).text

        # Get total gm pages
        self._gm_pages = self.get_page_count(self._gm_posts)

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
                        self.end_game_phase(int(self._post['data-num']))
                      
                    elif self._phase_start: 
                        self._current_day = int(self._phase_start[0].split('Día ')[-1])
                        
                        # Start new Game day
                        self.start_game_phase(post_id=int(self._post['data-num']),
                                              day_number=self._current_day,
                                              day_start_post=self._request)
                        

                        return