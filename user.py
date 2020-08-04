'''
Needed workaround until robobrowser import bug is fixed
'''
import werkzeug
werkzeug.cached_property  = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

import pandas as pd

class User:

    def  __init__(self, thread_id:int, thread_url:str, bot_id:str, bot_password:str, game_master:str):

        
        # Load vote rights table, we need vote visibility info.
        self.vote_config = pd.read_csv('vote_config.csv', sep=',')

        # Attempt to log into MV with these credentials.
        #TODO: Log errors here
        self.thread_url = thread_url
        self.thread_id  = thread_id

        self.user_id    = bot_id
        self.password   = bot_password

        self.game_master = game_master

        self.browser = self.login(self.user_id, self.password)
       

    def push_votecount(self, vote_count, alive_players, vote_majority):

        self._message_to_post = self.generate_vote_message(vote_count, alive_players, vote_majority)
        self.post(self._message_to_post)

    
    def push_lynch(self, last_votecount, victim):

        self._message_to_post = self.generate_lynch_message(last_votecount=last_votecount,
                                                            victim=victim)
        self.post(self._message_to_post)

   
    def login(self, user, password):

        self._browser = RoboBrowser(parser="html.parser")
        self._browser.open('http://m.mediavida.com/login')

        self._login = self._browser.get_form(id='login_form')
        self._login['name'].value = user
        self._login['password'].value = password

        self._browser.submit_form(self._login)

        return self._browser


    def post(self, message):

        self.browser.open(f'http://www.mediavida.com/foro/post.php?tid={self.thread_id}')
        self._post  = self.browser.get_form(id='postear')
        self._post['cuerpo'].value = message
        
        self.browser.submit_form(self._post)
        
        return self.browser.url

    def generate_vote_message(self, vote_count: pd.DataFrame, alive_players:int, vote_majority:int):

        self._header = "# Recuento de votos \n"

        self._votes_rank  = self.generate_string_from_vote_count(vote_count)

        self._footer  = (f'_Con {alive_players}  jugadores vivos, la mayoría se alcanza con {vote_majority} votos._ \n \n')
        self._bot_ad  = "**Soy un bot de recuento automático. Por favor, no me cites _¡N'wah!_** \n"

        self._message  = self._header + self._votes_rank + '\n' + self._footer + self._bot_ad

        return self._message


    def generate_string_from_vote_count(self, vote_count: pd.DataFrame):

        self._vote_count = vote_count['player'].value_counts().sort_values(ascending=False)
        self._vote_rank = ''

        for i in range(0, len(self._vote_count)):

            self._player = self._vote_count.index[i]
            self._votes  = self._vote_count[i]
            
            self._voters  = vote_count.loc[vote_count['player'] == self._player, 'voted_by'].tolist()
            self._voters  = ', '.join(self._voters)

            if self._player == 'no_lynch':
                self._player = 'No linchamiento'

            self._vote_string  =  f'1. [url={self.thread_url}?u={self._player}]**{self._player}**[/url]: {self._votes} ( _{self._voters}_ ) \n'  
            self._vote_rank    = self._vote_rank + self._vote_string

        return self._vote_rank


    def generate_lynch_message(self, last_votecount: pd.DataFrame, victim:str):

        if victim  == 'no_lynch':
            self._header = f'### ¡Se ha alcanzado mayoría absoluta. Nadie será linchado! ### \n \n'
        else:
            self._header   = f'### ¡Se ha alcanzado mayoría absoluta, {victim} será linchad@ en breves! ### \n \n'

        self._final_votecount = self.generate_string_from_vote_count(vote_count=last_votecount)

        self._no_votes = f'**Ya no se admiten más votos.** \n \n'
        self._footer   = f'@{self.game_master}, el pueblo ha hablado. \n'

        self._message = self._header + self._final_votecount + '\n' + self._no_votes + self._footer

        return self._message
