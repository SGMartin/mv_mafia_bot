'''
Needed workaround until robobrowser import bug is fixed
'''
import werkzeug
werkzeug.cached_property  = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

import pandas as pd

import modules.thread_reader as tr
import modules.game_actions  

class User:

    def  __init__(self, config: object):

        
        # Load vote rights table, we need vote visibility info.
        self.vote_config = pd.read_csv('vote_config.csv', sep=',')

        # Attempt to log into MV with these credentials.
        #TODO: Log errors here
        self.config = config
        self.browser = self.login(self.config.mediavida_user, self.config.mediavida_pwd)

        # Init internal queue
        self._queue      = list()

    def clear_queue(self):
        """Empty the queue of messages to push to the game thread."""
        self._queue.clear()


    def add_vhistory_to_queue(self, action:modules.game_actions.GameAction, vhistory:pd.DataFrame, victim_is_voter:bool):
        """Generate a vhistory message and append it to the queue.

        Args:
            action (modules.game_actions.GameAction): Vhistory request action.
            vhistory (pd.DataFrame): The whole vote history as a pandas dataframe.
            victim_is_voter (bool): If the action victim is the voter or the voted player.
        """
        self._message = self.generate_history_message(vhistory=vhistory,
                                                      is_voter=victim_is_voter,
                                                      player=action.victim,
                                                      requested_by=action.author)

        self._queue.append(self._message)


    def push_queue(self):
        """Post the whole queue of messages to the game thread."""

        if len(self._queue) > 0:
            self._resolved_queue = '\n'.join(self._queue)
            self.post(self._resolved_queue)
            self.clear_queue()


    def push_votecount(self, vote_count:pd.DataFrame, alive_players:pd.DataFrame, vote_majority:int, post_id:int):
        """Generate a new vote count message and push it to the game thread. Skips the queue.

        Args:
            vote_count (pd.DataFrame): The vote count object used to generate the message.
            alive_players (int): The number of alive players
            vote_majority (int): The number of votes necessary to reach majority.
            post_id (int): The post number of the last vote.
        """
        
        self._message_to_post = self.generate_vote_message(vote_count=vote_count,
                                                           alive_players=alive_players,
                                                           vote_majority=vote_majority,
                                                           post_id=post_id)
        self.post(self._message_to_post)

    def push_new_mayor(self, new_mayor:str):
        self._header = '# ¡El alcalde del pueblo aparece! \n'
        self._body = f"**¡{new_mayor} se revela para liderar al pueblo!** \n\n"
        self._footer = f"@{new_mayor} desde ahora cuentas con 3 votos. Úsalos con sabiduría."

        self._message_to_post = self._header + self._body + self._footer
        self.post(self._message_to_post)

    def push_welcome_message(self):
        self._message_to_post = self.generate_initial_msg(this_cfg=self.config)
        self.post(self._message_to_post)

    def queue_shooting(self, attacker:str, victim:str, is_dead:bool, reveal:str="unknown"):
        """Push a new shootoing event immediately, skipping the queue

        Args:
            attacker (str): The attacking player.
            victim (str): The player who has been shot.
            is_dead (bool): Is the victim dead?
            reveal (str): Role reveal
        """
        self._header = f'# ¡{attacker} tiene un arma! \n'
        self._body = f"_¡{attacker} revela un arma y dispara a {victim} ante la atónita mirada de la multitud!_ \n\n"

        if is_dead:
            if self.config.reveal_day_kill:
                self._footer = f"**¡{victim} ha sido asesinado!**\n [Spoiler={victim} era...]**{reveal}**[/spoiler]\n\n @{self.config.game_master}, se ha producido un asesinato."
            else:
                self._footer = f"**¡{victim} ha sido asesinado!**\n [Spoiler={victim} era...]Será revelado por el GM[/spoiler]\n\n @{self.config.game_master}, se ha producido un asesinato."
        else:
            self._footer = f"**¡{victim} sigue en pie!**"

        self._message_to_post = self._header + self._body + self._footer
        self._queue.append(self._message_to_post)
        
    def push_lynch(self, last_votecount: pd.DataFrame, victim:str, post_id:int, reveal=str, is_eod=False):
        """Generate a player lynched message and immediately post it the game thread. Skips the queue.

        Args:
            last_votecount (pd.DataFrame): The vote count table after the last vote.
            victim (str): The lynched player name.
            post_id (int): The post number where the vote triggering the lynch was casted.
            reveal(str): The role to reveal, if necessary
        """

        if is_eod:
            self._message_to_post = self.generate_eod_message(
                last_votecount=last_votecount,
                victim=victim,
                post_id=post_id,
                role=reveal
                )
        else:
            self._message_to_post = self.generate_lynch_message(last_votecount=last_votecount,
                                                                victim=victim,
                                                                post_id=post_id,
                                                                role=reveal
                                                                )
        self.post(self._message_to_post)


    def login(self, user:str, password:str):
        """Open and resolve mediavida.com login form to log into the bot account.

        Args:
            user (str): The user id to log into the account.
            password (str): The password to log into the account.

        Returns:
            [Robobrowser]: The resolved form.
        """

        self._browser = RoboBrowser(parser="html.parser")
        self._browser.open('http://m.mediavida.com/login')

        self._login = self._browser.get_form(id='login_form')
        self._login['name'].value = user
        self._login['password'].value = password

        self._browser.submit_form(self._login)

        return self._browser


    def post(self, message:str):
        """Open and resolve the post message form from mediavida.com

        Args:
            message (str): The message to post in the game thread.

        Returns:
            [Robobrowser]: The resolved form.
        """
        self.browser.open(f'http://www.mediavida.com/foro/post.php?tid={self.config.thread_id}')
        self._post  = self.browser.get_form(id='postear')
        self._post['cuerpo'].value = message
        
        self.browser.submit_form(self._post)
        
        return self.browser.url
        
    def generate_vote_message(self, vote_count: pd.DataFrame, alive_players: pd.DataFrame, vote_majority:int, post_id:int) -> str:
        """Generate a formatted Markdown message representing the vote count results.

        Args:
            vote_count (pd.DataFrame): The vote count to parse.
            alive_players (int): The number of alive players.
            vote_majority (int): The current number of votes to reach abs.majority.
            post_id (int): The post id of the last vote parsed in the vote_count.

        Returns:
            str: A string formatted in Markdown suitable to be posted as a new message in mediavida.com
        """

        self._header = "# Recuento de votos \n"
        self._votes_rank  = self.generate_string_from_vote_count(vote_count)
        self._non_voters = list(set(alive_players) - set(vote_count["voted_by"].values.tolist()))
        self._non_voters = ", ".join(self._non_voters)

        self._non_voters_msg = (f"1. **No han votado:** {self._non_voters}.\n")
        self._footer  = (f'_Con {len(alive_players)} jugadores vivos, la mayoría se alcanza con {vote_majority} votos._ \n')
        self._updated = (f'_Actualizado hasta el mensaje: {post_id}._ \n \n')
        self._bot_ad  = "**Soy un bot de recuento automático. Por favor, no me cites _¡N'wah!_** \n"

        self._message  = self._header + self._votes_rank  + self._non_voters_msg + "\n" + self._footer + self._updated + self._bot_ad

        return self._message


    def generate_lynch_message(self, last_votecount: pd.DataFrame, victim:str, post_id:int, role:str="Unknown") ->str:
        """Generate a formatted Markdown message announcing a player lynch.

        Args:
            last_votecount (pd.DataFrame): The vote count when the player is lynched.
            victim (str): The lynched player.
            post_id (int): The post id of the last vote before the lynch.

        Returns:
            str: A formatted Markdown message.
        """

        self._header = '# Recuento de votos final \n'

        if victim  == 'no_lynch':
            self._announcement = f'### ¡Se ha alcanzado mayoría absoluta en {post_id}. Nadie será linchado! ### \n'
        
        else:
            self._announcement = f'### ¡Se ha alcanzado mayoría absoluta en {post_id}, se linchará a {victim}! ### \n'

        self._final_votecount = self.generate_string_from_vote_count(vote_table=last_votecount)

        self._no_votes = f'**Ya no se admiten más votos.** \n \n'

        if self.config.reveal_lynch and victim != "no_lynch":
            self._footer = f"[Spoiler={victim} era...]**{role}**[/spoiler]\n\n @{self.config.game_master}, el pueblo ha hablado. \n"
        else:
            self._footer=f'@{self.config.game_master}, el pueblo ha hablado y aguarda tu resolución. \n'

        self._message = self._header + self._final_votecount + '\n' + self._announcement + self._no_votes + self._footer

        return self._message

    def generate_eod_message(self, last_votecount: pd.DataFrame, victim:str, post_id:int, role:str="unknown") -> str:
        """Generate a formatted Markdown message announcing a player lynch after EoD.

        Args:
            last_votecount (pd.DataFrame): The vote count when the player is lynched.
            victim (str): The lynched player.
            post_id (int): The post id of the last vote before the lynch.

        Returns:
            str: A formatted Markdown message.
        """
        self._header = '# Recuento de votos final \n'

        if victim  == 'no_lynch':
            self._announcement = f'### ¡Se ha alcanzado el final del día! Última acción válida en {post_id}. Nadie será linchado! ### \n'
        elif victim is None:
            self._announcement = f'### ¡Se ha alcanzado el final del día! Última acción válida en {post_id}. El GM decidirá el linchamiento ### \n'
        else:
            self._announcement = f'### ¡Se ha alcanzado el final del día! Última acción válida en {post_id}, se linchará a {victim}! ### \n'

        self._final_votecount = self.generate_string_from_vote_count(vote_table=last_votecount)

        self._no_votes = f'**Ya no se admiten más votos.** \n \n'

        if self.config.reveal_eod_lynch and victim is not None and victim != "no_lynch":
            self._footer = f"[Spoiler={victim} era...]**{role}**[/spoiler]\n\n @{self.config.game_master}, el pueblo ha hablado. \n"
        else:
            self._footer=f'@{self.config.game_master}, el día ha terminado y el pueblo aguarda tu resolución. \n'

        self._message = self._header + self._final_votecount + '\n' + self._announcement + self._no_votes + self._footer

        return self._message


    def generate_string_from_vote_count(self, vote_table: pd.DataFrame) -> str:
        """Generate a formatted Markdown message representing the results from the current vote count.

        Args:
            vote_table (pd.DataFrame): A pandas dataframe with the current vote count.

        Returns:
            str: A string formatted in Markdown table suited to be posted in mediavida.com
        """

        self._vote_table = vote_table

        self._vote_count = self._vote_table['public_name'].value_counts().sort_values(ascending=False)
        self._vote_rank = ''

        for i in range(0, len(self._vote_count)):

            self._player = self._vote_count.index[i]
            self._votes  = self._vote_count[i]
            
            self._voters  = self._vote_table.loc[self._vote_table['public_name'] == self._player, 'voted_as'].tolist()
            self._voters  = ', '.join(self._voters)

            if self._player == 'no_lynch':
                self._player = 'No linchamiento'

            self._vote_string  =  f'1. [url={self.config.game_thread}?u={self._player}]**{self._player}**[/url]: {self._votes} (_{self._voters}_) \n'  
            self._vote_rank    = self._vote_rank + self._vote_string

        return self._vote_rank


    def generate_history_message(self, vhistory:pd.DataFrame, is_voter:bool, player:str, requested_by:str) ->str:
        """Generate a vote history report as a Markdown formatted string to be posted in mediavida.com

        Args:
            vhistory (pd.DataFrame): The current history of votes from the start of the game.
            is_voter (bool): If the report is from a player casted votes or the votes casted to the player.
            player (str): The player from which to generate the report.
            requested_by (str): The player requesting the report.

        Returns:
            str: A string formatted in Markdown suited to be posted in mediavida.com
        """

        #TODO: Consider an enumerator in the future
        if is_voter:

            self._header  = f'# Historial de votos de {player}\n'
            self._column_to_search = 'voted_as'
            self._target_column    = 'public_name'
        else:
            self._header = f'# Historial de votantes de {player}\n'
            self._column_to_search = 'public_name'
            self._target_column    = 'voted_as'

        ## check if the provided name has been voted. 
        self._matches = vhistory[self._column_to_search].str.contains(player, case=False)
        self._votes   = vhistory[self._matches].copy()

        if len(self._votes.index) == 0:
            self._markdown_table = 'No se han encontrado votos.\n'
        else:
            self._votes['post_link'] = [f'[{x}]({self.config.game_thread}/{tr.get_page_number_from_post(x)}#{x})' for x in self._votes['post_id']]

            # For each player, create a column of type list with all the posts where they have been voted
            self._votes_post_id = self._votes.groupby(self._target_column)['post_link'].apply(list).reset_index(name='posts')

            # Cast the list to str by joining each of them
            self._votes_post_id['posts'] = self._votes_post_id['posts'].apply(lambda x: ','.join(map(str, x)))

            # Transform said dataframe  to a dict, where keys are players and values a list of posts
            self._votes_post_id = self._votes_post_id.set_index(self._target_column)['posts'].to_dict()

            # Count how many votes each player had
            self._vote_history = self._votes[self._target_column].value_counts()
            self._vote_history = pd.DataFrame(self._vote_history)

            # Rename columns and the index
            self._vote_history.columns       = ['Votos']
            self._vote_history.index.names   = ['Jugador']

            # Add the messages column
            self._vote_history['Votado en'] = self._vote_history.index.map(self._votes_post_id)

            # Requires pip/conda package tabulate
            self._markdown_table = self._vote_history.to_markdown(numalign='center', stralign='center') + '\n'

            del self._votes

        self._footer  = f'Solicitado por @{requested_by}'
        self._message = self._header + self._markdown_table + self._footer
        return self._message


    def generate_initial_msg(self, this_cfg: object) -> str:
        """
            Generate initial bot activation message string"
        """
        self._header = "# ¡Bot activado con éxito!\n"
        self._subheader = "## Parámetros de la partida\n\n"

        self._gm_item= f"* **GM**: {this_cfg.game_master}\n"
        self._mods_item = f"* **Moderadores**: {','.join(this_cfg.moderators)}\n"
        self._frequencies = f"* **Frecuencias de recuento**: {this_cfg.posts_until_update} mensajes, {this_cfg.votes_until_update} voto(s).\n"
        self._autoflip = f"* **Resolución de linchamiento automática**: No.\n\n"

        self._cite_gm = f"@{this_cfg.game_master} ya estoy en funcionamiento."

        self._message = self._header + self._subheader + self._gm_item + self._mods_item + self._frequencies + self._autoflip + self._cite_gm
        return self._message