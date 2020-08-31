'''
Needed workaround until robobrowser import bug is fixed
'''
import werkzeug
werkzeug.cached_property  = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

import pandas as pd

class User:

    def  __init__(self, thread_id:int, thread_url:str, bot_id:str,
                  bot_password:str, game_master:str):

        
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
       

    def push_votecount(self, vote_count, alive_players, vote_majority, post_id):

        self._message_to_post = self.generate_vote_message(vote_count=vote_count,
                                                           alive_players=alive_players,
                                                           vote_majority=vote_majority,
                                                           post_id=post_id)
        self.post(self._message_to_post)

    
    def push_lynch(self, last_votecount, victim, post_id):

        self._message_to_post = self.generate_lynch_message(last_votecount=last_votecount,
                                                            victim=victim,
                                                            post_id=post_id)
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

    def generate_vote_message(self, vote_count: pd.DataFrame, alive_players:int, vote_majority:int, post_id:int):

        self._header = "# Recuento de votos \n"

        self._votes_rank  = self.generate_string_from_vote_count(vote_count)

        self._footer  = (f'_Con {alive_players}  jugadores vivos, la mayoría se alcanza con {vote_majority} votos._ \n')
        self._updated = (f'_Actualizado hasta el mensaje: {post_id}._ \n \n')
        self._bot_ad  = "**Soy un bot de recuento automático. Por favor, no me cites _¡N'wah!_** \n"

        self._message  = self._header + self._votes_rank + '\n' + self._footer + self._updated + self._bot_ad

        return self._message


    def generate_string_from_vote_count(self, vote_table: pd.DataFrame):

        self._vote_table = vote_table

        ## Supersede the player who voted (voted_by) by its alias if they are not the same
        self._prioritise_alias = self._vote_table['voted_by'].str.lower() != self._vote_table['vote_alias'].str.lower()
        self._vote_table.loc[self._prioritise_alias, 'voted_by'] = self._vote_table.loc[self._prioritise_alias, 'vote_alias']

        self._vote_count = self._vote_table['player'].value_counts().sort_values(ascending=False)
        self._vote_rank = ''

        for i in range(0, len(self._vote_count)):

            self._player = self._vote_count.index[i]
            self._votes  = self._vote_count[i]
            
            self._voters  = self._vote_table.loc[self._vote_table['player'] == self._player, 'voted_by'].tolist()
            self._voters  = ', '.join(self._voters)

            if self._player == 'no_lynch':
                self._player = 'No linchamiento'

            self._vote_string  =  f'1. [url={self.thread_url}?u={self._player}]**{self._player}**[/url]: {self._votes} (_{self._voters}_) \n'  
            self._vote_rank    = self._vote_rank + self._vote_string

        return self._vote_rank


    def generate_lynch_message(self, last_votecount: pd.DataFrame, victim:str, post_id:int):

        self._header = '# Recuento de votos final \n'

        if victim  == 'no_lynch':
            self._announcement = f'### ¡Se ha alcanzado mayoría absoluta en {post_id}. Nadie será linchado! ### \n'
        
        else:
            self._announcement = f'### ¡Se ha alcanzado mayoría absoluta en {post_id}, se linchará a {victim}! ### \n'

        self._final_votecount = self.generate_string_from_vote_count(vote_table=last_votecount)

        self._no_votes = f'**Ya no se admiten más votos.** \n \n'
        self._footer   = f'@{self.game_master}, el pueblo ha hablado. \n'

        self._message = self._header + self._final_votecount + '\n' + self._announcement + self._no_votes + self._footer

        return self._message
