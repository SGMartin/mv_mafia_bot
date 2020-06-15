import os.path
import requests
import re
import time

from bs4 import BeautifulSoup
import pandas as pd

class MafiaBot:

    def __init__(self, game_url: str, gm: str):

        print('MV MafiaBot started')

        #Initialize vars
        self.game_title   = 'Unknown'
        self.game_thread  = game_url
        self.game_master  = gm
        self.page_count   =  1
        self.current_day  =  1

        #Load game database
        self.database = self.load_database()

        # Get last page checked. 0 = none.
        self.current_page =  int(self.database.loc['last_page', 'value'])

        if self.current_page == 0:  ## First init.

            self._request         = requests.get(self.game_thread)
            self.game_title       =  self.get_game_title(self._request.text)
            self.page_count       =  self.get_page_count(self._request.text)

        else:
            self.game_title = self.database.loc['title', 'value']
   
            #Start a response from the last page checked. Include said page
            #just in case the bot was closed with the page not completely parsed
            #Also: Reusing a request to update page count
        
            self._request_url = f'{self.game_thread}/{self.current_page}'
            self._request     = requests.get(url=self._request_url)

            self.page_count         = self.get_page_count(self._request.text)

        # We have to get the current day anyway
        self.current_day = self.get_current_game_day()

        self._welcome = f'Game {self.game_title}. GM: {self.game_master}. Pages: {self.page_count}'
        print(self._welcome)
        print('We are on day:', self.current_day)




    def load_database(self):
        '''
        We'll attempt to load this game database. If not found, we'll assume
        we are being initialized for the first time.
        '''

        ## Get thread id ##
        self._name_and_thread_id = self.game_thread.split('/')[5]
        self._thread_id          = int(self._name_and_thread_id.split('-')[-1]) #get last element

        self.database_path = 'mafia_' + str(self._thread_id) + '.csv'
        
        if os.path.exists(self.database_path):

            self._database = pd.read_csv(filepath_or_buffer=self.database_path, sep=',')
            self._database.set_index('record', inplace=True)
            print('Database found for this game!')

        else:
            print('No data found for this game... starting from scratch')
            self._database  = pd.DataFrame({'record': ['last_page'], 'value':[0]})
            self._database.set_index('record', inplace=True)

        return self._database


    def get_game_title(self, request_text):
        # Get game name
        self._game_title = BeautifulSoup(request_text, 'html.parser')
        self._game_title = self._game_title.find('title').text

        # Remove the trailing '| Mediavida'
        self._game_title = self._game_title.split('|')[0]

        return self.game_title


    def get_page_count(self, request_text):
        #Let's try to parse the page count from the bottom  page panel
        self._page_count = 0
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


    def count_votes_from_page(self, page_to_parse):
        
        # Build a valid URL to scan
        self._parsing_page = self.game_thread + '/' +  str(page_to_parse)
        self._parsing_page = requests.get(self._parsing_page)

        #TODO: what if page does not exists
        self._parser = BeautifulSoup(self._parsing_page.text, 'html.parser')

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
                       self.process_vote_candidate(self._bolded_paragraph.text,
                                                   self._author,
                                                   self._post_id)
                       
    
    def process_vote_candidate(self, bold_text, author, post_id):

        # Check the player is not unvoting
        if 'desvoto'  in bold_text.lower():
            print(author,'is unvoting', 'at', post_id)

        # Check for the vote: struct
        if 'voto:' in bold_text.lower():
            # Remove white spaces,  if any
            player = bold_text.split(':')[1]
            player = player.replace(' ', '')

            # TODO: Check against player list
            print(author, 'voted', player, 'at', post_id)    
    
    
    def get_current_game_day(self) -> int:
        '''
        Attempt to parse h2 tags in GM posts to get the current day phase.
        Will return 0 if no day found.
        '''
        self._current_day = 0

        self._gm_posts  = self.game_thread + '?u=' + self.game_master
        self._gm_posts  = requests.get(self._gm_posts)
        self._gm_posts  = BeautifulSoup(self._gm_posts.text, 'html.parser')
        
        # Get total gm pages
        self._gm_pages = int(self.get_page_count(self._gm_posts))

        # We'll start looping from the last page to the previous one
        for self._pagenum in range(self._gm_pages, 0, -1):

            self._current_page = f'{self.game_thread}?u={self.game_master}&pagina={self._pagenum}'
            self._current_page = requests.get(self._current_page)
            self._current_page = BeautifulSoup(self._current_page.text, 'html.parser')

            #TODO: log these iterations?
            self._headers      = self._current_page.find_all('h2')

            # From latter entries backwards
            for self._pday in reversed(self._headers):
                self._results = re.findall('^Día [0-9]*', self._pday.text)

                if self._results:
                    self._day = self._results[0].split('Día ')
                    self._current_day = int(self._day[1])
                    return self._current_day


    def run(self, seconds):

        self._failed_runs = 0

        while(True):
                print('Scanning thread...')

                #Send a request to the current page
                self._page_to_scan = f'{self.game_thread}/{self.current_page}'
                self._request      = requests.get(self._page_to_scan)

                if self._request.status_code == 200:

                    # Update current page count
                    self.page_count = self.get_page_count(self._request.text)
                
                    if (self.page_count - self.current_page) > 0:

                        for page in range(self.current_page, (self._page_count + 1)):

                            print('Scanning page', page)
                            self.count_votes_from_page(page)
                            self.current_page = page
                            time.sleep(1) #try not to query too many pages at once


                    print('Scanning finished. I will sleep for:', seconds, 'seconds')

                
                else:
                    self._failed_runs += 1
                    print('Scan attempt failed. Verify your Internet connection.')

                    if self._failed_runs >= 3:
                        print('Too many attempts failed. Aborting...')
                        break

                time.sleep(seconds)



               
             




