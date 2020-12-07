import logging

import pandas as pd

import modules.game_actions as gm

class  VoteCount():

    def __init__(self, staff:list, day_start_post:int):

        # Initialize empty vote table
        self._vote_table = pd.DataFrame(columns=['player', 'voted_by',
                                                'post_id', 'post_time', 'vote_alias'])
    
        self._vote_history = self._vote_table.copy()

        # Load vote rights table
        self.vote_rights = pd.read_csv('vote_config.csv', sep=',')
        
        # use lowercase player names as keys, player column as true names
        self.vote_rights.index = self.vote_rights['player'].str.lower()

        self.staff = staff

        self.lynched_player = ''


    def get_vote_table(self) -> list:
        '''
        This function translates lowercased player names to their actual mediavida
        names for a fancier vote count post. To do so, it relies on the vote_rights
        table, which features a player column. A dictionary is built in which
        the table index is the lowercased player name and the dict. values are taken
        from the player column. 

        The vote table names are then mapped using this dictionary.

        Parameters: None \n
        Returns: 
        A vote table pandas object in which lowercase names have been mapped to 
        their real mediavida names.
        '''

        self._real_names = self.vote_rights['player'].to_dict()
  
        self._staff_to_gm = {self._staff.lower(): 'GM' for self._staff in self.staff}

        self._real_names.update(self._staff_to_gm)

        self._translat_table = self._vote_table
        self._translat_table['player'] = self._translat_table['player'].map(self._real_names)
        self._translat_table['voted_by'] = self._translat_table['voted_by'].map(self._real_names)

        return self._translat_table


    def player_exists(self, player:str) -> bool:
        '''
        Checks if a given player is in the vote_rights table. 

        Parameters:
        - player(str):  the player to check

        Returns:
            False if the player does not exists. True otherwise.
        '''

        if player.lower() in self.vote_rights.index:
            return True
        else:
            return False


    def get_real_name(self, player:str) -> str:

        if player in self.vote_rights.index:
            return self.vote_rights.loc[player, 'player']

        else:
            logging.error(f'{player} not in index. Returning Nerevar :)')
            return 'Nerevar'


    def get_player_current_votes(self, player:str) -> int:
        '''
        Counts current casted votes by a given player.

        Parameters:\n
        player (str): The player whose votes are to be counted.

        Returns:\n
        An int of the valid votes casted by said player.
        '''
        self._player_current_votes = len(self._vote_table[self._vote_table['voted_by'] == player])

        return self._player_current_votes


    def get_victim_current_votes(self, victim:str) -> int:
        '''
        Counts current votes on a given player.

        Parameters:\n
        victim (str): The player whose votes are to be counted

        Returns:\n
        An int of the valid votes casted on said player.
        '''
        
        self._lynch_votes = len(self._vote_table[self._vote_table['player'] == victim])

        return self._lynch_votes
        

    def get_player_mod_to_lynch(self, player:str) -> int:

        if self.player_exists(player):
            return self.vote_rights.loc[player, 'mod_to_lynch']
        else:
            logging.error(f'{player} is not in the vote_rights table. Returning 0')
            return 0


    def vote_player(self, action: gm.GameAction):

        if self.is_valid_vote(action.author, action.victim):

            self._append_vote(player=action.author,
                              victim=action.victim,
                              post_id=action.id,
                              post_time=action.post_time,
                              vote_alias=action.alias)


    def unvote_player(self, action: gm.GameAction):

        if self.is_valid_unvote(action.author, action.victim):
            self._remove_vote(action.author, action.victim)


    def is_valid_vote(self, player:str, victim:str) -> bool:
        '''
        Evaluates if a given vote is valid. A valid vote has to fulfill the following
        requirements:

        a) The victim can be voted: alive, playing and set as vote candidate in the vote rights table.\n
        b) The voting player must have casted less votes than their current limit.

        Parameters:\n 
        player (str): The player casting the vote.
        victim (str): The player who receives the vote.\n
        Returns:\n 
        True if the vote is valid, False otherwise.
        '''

        self._is_valid_vote = False

        if player in self.staff:
            self._player_max_votes = 999
        else:
            if self.player_exists(player):
                self._player_max_votes = self.vote_rights.loc[player, 'allowed_votes']
            else:
                logging.error(f'{player} is not in the vote_rights table. Invalid vote!')
                return False
        
        self._player_current_votes = self.get_player_current_votes(player)

        if self._player_current_votes < self._player_max_votes:

            if victim in self.vote_rights.index:

                self._victim_can_be_voted  = bool(self.vote_rights.loc[victim, 'can_be_voted'])

                if self._victim_can_be_voted:
                    self._is_valid_vote = True

                else:
                    logging.info(f'{player} voted non-votable player: {victim}')    
            else:
                logging.error(f'{victim} not found in vote_rights.csv')
        else:
            logging.info(f'{player} has reached maximum allowed votes')

        return self._is_valid_vote


    def is_valid_unvote(self, player:str, victim:str) -> bool:
        '''
        Evaluates if a given unvote is valid. A valid unvote has to fulfill the following
        requirements: The player has previously casted a voted to victim or has
        at least one casted vote if victim = 'none'

        Parameters:\n 
        player (str): The player casting the vote.
        victim (str): The player who receives the unvote the vote. Can be none for a general unvote.\n
        Returns:\n 
        True if the unvote is valid, False otherwise.
        '''

        self._is_valid_unvote = False

        if player in self._vote_table['voted_by'].values:

            if self.get_player_current_votes(player) >  0:

                if victim == 'none':
                    self._is_valid_unvote = True
                    
                else: 
                    # Get all casted voted to said victim by player
                    self._casted_votes = self._vote_table[(self._vote_table['player'] == victim ) & (self._vote_table['voted_by'] == player)]

                    if len(self._casted_votes) > 0: 
                        self._is_valid_unvote = True
    
        return self._is_valid_unvote


    def replace_player(self, replaced:str, replaced_by:str):
        '''
        STUB
        '''
        if self.player_exists(player=replaced):

            ## Update the votetable. This is run-safe.
            self._vote_table.loc[self._vote_table['player'] == replaced, 'player'] = replaced_by
            self._vote_table.loc[self._vote_table['voted_by'] == replaced, 'voted_by'] = replaced_by

            ## Update the vote rights, do not edit it. It would invalidate the votes casted to the replaced
            ## player on the next run.
            if not self.player_exists(player=replaced_by):
                self._append_to_vote_rights(player=replaced_by, based_on_player=replaced)
        else:
            logging.warning(f'Attempting to replace unknown player {replaced} with {replaced_by}')


    def _append_vote(self, player:str, victim:str, post_id:int, post_time:int, vote_alias:str):
        '''
        This function process votes and keeps track of the vote table. Votes are added or removed based on the victim. 

        Parameters:\n
        player (str): The player who casts the vote.\n
        victim (str): The player who receives the vote. Can be set to "desvoto" to remove a previously casted voted by player.\n
        post_id  (int): The post ID where the vote was casted.\n
        post_time (int): Unix epoch time of the post where the vote was casted.\n
        Returns: None.
        '''

        self._vote_table  = self._vote_table.append({'player': victim,
                                                    'voted_by': player,
                                                    'post_id': post_id,
                                                    'post_time': post_time,
                                                    'vote_alias': vote_alias},
                                                    ignore_index=True)
        
        self._update_vote_history()
        logging.info(f'{player} voted {victim} at {post_id}')


    def _remove_vote(self, player:str, victim:str):
        '''
        This function removes a given vote from the vote table. They are always
        removed from the oldest to the newest casted vote. 

        Parameters:\n
        player (str): The player who removes the vote.\n
        victim (str): The unvoted player. Can be set to "none" to remove the oldest vote no matter the victim.\n
        Returns: None.
        '''

        if victim == 'none': 
            self._old_vote = self._vote_table[self._vote_table['voted_by'] == player].index[0]
        else:
            self._old_vote = self._vote_table[(self._vote_table['player'] == victim) & (self._vote_table['voted_by'] == player)].index[0]
        
        ## Always remove the oldest vote casted
        self._vote_table.drop(self._old_vote, axis=0, inplace=True)
        
        logging.info(f'{player} unvoted {victim}.')
    

    def _update_vote_history(self):
        '''
        This function copies the last appended row of the vote_table to  the
        vote history table.
        '''
        self._vote_history = self._vote_history.append(self._vote_table.tail(1),
                                                       ignore_index=True)


    def _append_to_vote_rights(self, player:str, based_on_player:str):
        '''

        '''
        ## Get the rights reg. to base the new entry on
        self._old_player = self.vote_rights.loc[based_on_player].to_dict()

        # Change the player name
        self._old_player['player'] = player

        # Create a 1row dataframe whose index is the lowercased player name
        self._new_vote_rights = pd.DataFrame(self._old_player, index=[player.lower()])

        # Append it to the end of the vote rights table
        self.vote_rights = self.vote_rights.append(self._new_vote_rights)

        # Just in case the bot closes, let's update the vote_rights. 
        #TODO: Find  a better way to do this. 

        logging.info(f'Updated vote_rights.csv with {player}')
        self.vote_rights.to_csv('vote_config.csv', sep=',', index=False, header=True)