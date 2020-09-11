import logging


import pandas as pd

class  VoteCount():

    def __init__(self, game_master):

        # Initialize empty vote table
        self._vote_table = pd.DataFrame(columns=['player', 'voted_by',
                                                'post_id', 'vote_alias'])
    

        # Load vote rights table
        self.vote_rights = pd.read_csv('vote_config.csv', sep=',')
        
        # use lowercase player names as keys, player column as true names
        self.vote_rights.index = self.vote_rights['player'].str.lower()

        self.game_master = game_master


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
        self._real_names[self.game_master.lower()] = 'GM'

        self._translat_table = self._vote_table
        self._translat_table['player'] = self._translat_table['player'].map(self._real_names)
        self._translat_table['voted_by'] = self._translat_table['voted_by'].map(self._real_names)

        return self._translat_table


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

        return self.vote_rights.loc[player, 'mod_to_lynch']

    def vote_player(self, author:str, victim:str, post_id:int, vote_alias:str):

        if self.is_valid_vote(author, victim):
            self._append_vote(author, victim, post_id, vote_alias)


    def unvote_player(self, author:str, victim:str, post_id:int):

        if self.is_valid_unvote(author, victim):
            self._remove_vote(author, victim, post_id)


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

        if player == self.game_master.lower():
            self._player_max_votes = 999
        else:
            self._player_max_votes = self.vote_rights.loc[player, 'allowed_votes']
        
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


    def _append_vote(self, player:str, victim:str, post_id:int, vote_alias:str):
        '''
        This function process votes and keeps track of the vote table. Votes are added or removed based on the victim. 

        Parameters:\n
        player (str): The player who casts the vote.\n
        victim (str): The player who receives the vote. Can be set to "desvoto" to remove a previously casted voted by player.\n
        post_id  (int): The post ID where the vote was casted.\n
        Returns: None.
        '''

        self._vote_table  = self._vote_table.append({'player': victim,
                                                    'voted_by': player,
                                                    'post_id': post_id,
                                                    'vote_alias': vote_alias},
                                                    ignore_index=True)
        
        logging.info(f'{player} voted {victim} at {post_id}')


    def _remove_vote(self, player:str, victim:str, post_id:int):
        '''
        This function removes a given vote from the vote table. They are always
        removed from the oldest to the newest casted vote. 

        Parameters:\n
        player (str): The player who removes the vote.\n
        victim (str): The unvoted player. Can be set to "none" to remove the oldest vote no matter the victim.\n
        post_id  (int): The post ID where the unvote was casted.\n
        Returns: None.
        '''

        if victim == 'none': 
            self._old_vote = self._vote_table[self._vote_table['voted_by'] == player].index[0]
        else:
            self._old_vote = self._vote_table[(self._vote_table['player'] == victim) & (self._vote_table['voted_by'] == player)].index[0]
        
            ## Always remove the oldest vote casted
            self._vote_table.drop(self._old_vote, axis=0, inplace=True)
        
        logging.info(f'{player} unvoted {victim}.')