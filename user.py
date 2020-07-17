'''
Needed workaround until robobrowser import bug is fixed
'''
import werkzeug
werkzeug.cached_property  = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

import pandas as pd

class User:

    def  __init__(self, thread_id:int, thread_url:str, bot_id:str, bot_password:str,
                  vote_count: pd.DataFrame, alive_players:int, vote_majority:int):
        
        # Load vote rights table, we need vote visibility info.
        self.vote_config = pd.read_csv('vote_config.csv', sep=',')

        # Attempt to log into MV with these credentials.
        #TODO: Log errors here

        self.thread_url = thread_url

        self.user_id  = bot_id
        self.password = bot_password

        self.browser = self.login(self.user_id, self.password)
        self.message_to_post = self.generate_vote_message(vote_count, thread_id, alive_players, vote_majority)

        self.post(self.message_to_post, thread_id, self.browser)
        

    def login(self, user, password):

        self._browser = RoboBrowser(parser="html.parser")
        self._browser.open('http://m.mediavida.com/login')

        self._login = self._browser.get_form(id='login_form')
        self._login['name'].value = user
        self._login['password'].value = password

        self._browser.submit_form(self._login)

        return self._browser


    def post(self, message, thread_id, browser):

        browser.open(f'http://www.mediavida.com/foro/post.php?tid={thread_id}')
        self._post  = browser.get_form(id='postear')
        self._post['cuerpo'].value = message
        
        browser.submit_form(self._post)
        
        return browser.url

    def generate_vote_message(self, vote_count: pd.DataFrame, thread_id:int, alive_players:int, vote_majority:int):

        self._header = "# Recuento de votos \n"

        self._votes_rank  = self.generate_string_from_vote_count(vote_count, self.thread_url)

        self._footer  = (f'_Con {alive_players}  jugadores vivos, la mayoría se alcanza con {vote_majority} votos._ \n \n')
        self._bot_ad  = "**Soy un bot de recuento automático. Por favor, no me cites _¡N'wah!_** \n"

        self._message  = self._header + self._votes_rank + '\n' + self._footer + self._bot_ad

        return self._message


    def generate_string_from_vote_count(self, vote_count: pd.DataFrame, thread_url):

        self._vote_count = vote_count['player'].value_counts().sort_values(ascending=False)

        self._vote_rank = ''

        for i in range(0, len(self._vote_count)):

            self._player = self._vote_count.index[i]
            self._votes  = self._vote_count[i]
            
            self._voters  = vote_count.loc[vote_count['player'] == self._player, 'voted_by'].tolist()
            self._voters  = ', '.join(self._voters)

            self._vote_string  =  f'1. [url={thread_url}?u={self._player}]**{self._player}**[/url]: {self._votes} ( _{self._voters}_ ) \n'  
            self._vote_rank    = self._vote_rank + self._vote_string

        return self._vote_rank


