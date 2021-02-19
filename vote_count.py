import logging

import pandas as pd

import modules.game_actions as gm

class  VoteCount:

    def __init__(self, staff:list, day_start_post:int, bot_cyle:int):

        # Initialize empty vote table
        self._vote_table = pd.DataFrame(columns=['player', 'public_name', 'voted_by', 
                                                 'voted_as', 'post_id', 'post_time', 'bot_cycle'])
    
        try:
            self._vote_history = pd.read_csv('vote_history.csv', sep=',')
        except:
            logging.info('Failed to load vote history. Starting from scratch...')
            self._vote_history = self._vote_table.copy()

        # Load vote rights table
        self.vote_rights = pd.read_csv('vote_config.csv', sep=',')

        ## Check if no_lynch row is present. Add it if missing, but keep it disabled.
        if 'no_lynch' not in self.vote_rights['player'].values:
            self.vote_rights.loc[len(self.vote_rights),:] = ['no_lynch',0,0,0]
        
        # use lowercase player names as keys, player column as true names
        self.vote_rights.index = self.vote_rights['player'].str.lower()

        self.staff = staff

        self.lynched_player = ''
        self.bot_cycle      = bot_cyle

        # Frozen vote players
        self.frozen_players = list() 

        self.locked_unvotes = False
        

    def player_exists(self, player:str) -> bool:
        """Check if a given player is in the vote_rights table. 

        Args:
            player (str): The player to check

        Returns:
            bool: False if the player does not exists. True otherwise.
        """
        if player.lower() in self.vote_rights.index:
            return True
        else:
            return False


    def get_real_names(self) -> dict:
        """Get a dictionary of the player names with proper casing.

        Returns:
            dict: A dict with lowercased player names as keys and properly cased names as values.
        """

        self._real_names  = self.vote_rights['player'].to_dict()
        self._staff_to_gm = {self._staff.lower(): 'GM' for self._staff in self.staff}
        self._real_names.update(self._staff_to_gm)
        self._real_names.update({'no_lynch':'No linchamiento'})

        return self._real_names


    def get_player_current_votes(self, player:str) -> int:
        """Count current casted votes by a given player.

        Args:
            player (str): The player whose votes are to be counted.

        Returns:
            int: The number of valid votes casted by said player.
        """
        self._player_current_votes = len(self._vote_table[self._vote_table['voted_by'] == player])

        return self._player_current_votes


    def get_victim_current_votes(self, victim:str) -> int:
        """Count current votes on a given player.

        Args:
            victim (str): The player whose votes are to be counted

        Returns:
            int: The number of valid votes casted on said player.
        """        
        self._lynch_votes = len(self._vote_table[self._vote_table['player'] == victim])

        return self._lynch_votes
        

    def get_player_mod_to_lynch(self, player:str) -> int:
        """Get the majority modifier of a given player.

        Args:
            player (str): 

        Returns:
            int: The majority modifier of the requested player
        """

        if self.player_exists(player):
            return self.vote_rights.loc[player, 'mod_to_lynch']
        else:
            logging.error(f'{player} is not in the vote_rights table. Returning 0')
            return 0


    def vote_player(self, action: gm.GameAction):
        """Parse a vote player action.

        Args:
            action (gm.GameAction): The game action featuring the vote.
        """

        if self.is_valid_vote(action.author, action.victim):

            ## Get the real MV names, with the proper casing, and the GM
            ## alias for staffers

            self._names_to_use = self.get_real_names()

            ## By default, set the author and victim to the action lowercased ids
            self._voter_real_name  = action.author
            self._victim_real_name = self._names_to_use[action.victim]

            ## If a member from the staff uses an alias, overwrite any author name.
            if action.author in self.staff and action.author != action.alias:
                self._voter_real_name = action.alias
            else:
                self._voter_real_name = self._names_to_use[action.author]

            self._append_vote(player=action.author,
                              victim=action.victim,
                              post_id=action.id,
                              post_time=action.post_time,
                              victim_alias=self._victim_real_name,
                              voted_as=self._voter_real_name)


    def unvote_player(self, action: gm.GameAction):
        """Attempt to parse an unvote action.

        Args:
            action (gm.GameAction): The action triggering the unvote.
        """

        if self.is_valid_unvote(action.author, action.victim):
            self._remove_vote(action.author, action.victim)


    def is_lynched(self, victim:str, current_majority:int) -> bool:
        """ Check if a given player has received enough votes to be lynched. This
        function evaluates if a given player accumulates enough votes by calculating
        the current absolute majority required and adding to it a player specific
        lynch modifier as defined in the vote rights table.

        Args:
            victim (str): The player who receives the vote.
            current_majority (int): The current number of votes necessary to reach abs. majority.

        Returns:
            bool: True if the player should be lynched.  False otherwise.
        """
        self._lynched = False
        
        # Count this player votes
        self._lynch_votes     = self.get_victim_current_votes(victim)
        self._player_majority = current_majority + self.get_player_mod_to_lynch(victim)

        if self._lynch_votes >= self._player_majority:
            self._lynched = True
        
        return self._lynched

        
    def is_valid_vote(self, player:str, victim:str) -> bool:
        """Evaluate if a given vote is valid. A valid vote has to fulfill the following
        requirements:

        a) The victim can be voted: alive, playing and set as vote candidate in the vote rights table.\n
        b) The voting player must have casted less votes than their current limit.\n
        c) No other special conditions (i.e. freezing) which prevent the cast of the vote apply.\n


        Args:
            player (str): The player casting the vote.
            victim (str): The player who receives the vote.\n


        Returns:
            bool: True if the vote is valid, False otherwise.
        """
        self._is_valid_vote = False

        # If the player votes are frozen then we have nothing to do here
        if player in self.frozen_players:
            return self._is_valid_vote

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
        """Evaluate if a given unvote is valid. A valid unvote has to fulfill the following
        requirements: 

        a)The player has previously casted a voted to victim 
        b)The player has at least one casted vote if victim = 'none'

        Args:
            player (str): The player casting the vote.
            victim (str): The player who receives the unvote the vote. Can be none for a general unvote

        Returns:
            bool: True if the unvote is valid, False otherwise.
        """
        self._is_valid_unvote = False

        if self.locked_unvotes:
            logging.info(f'Ignoring unvote casted by {player} due to LyLo.')
            return self._is_valid_unvote

        # If the player votes are frozen then we have nothing to do here
        if player in self.frozen_players:
            return self._is_valid_unvote
        
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
        """Attempt to replace a given player by another one. The substitute
        inherits all the votes casted to him as well as the votes casted by the
        replaced player.

        Args:
            replaced (str): The replaced player.
            replaced_by (str): The substitute.
        """
    
        if self.player_exists(player=replaced):

            ## Update the votetable. This is run-safe.
            self._vote_table.loc[self._vote_table['player'] == replaced, ['player', 'public_name']]  = replaced_by
            self._vote_table.loc[self._vote_table['voted_by'] == replaced, ['voted_by', 'voted_as']] = replaced_by

            ## Update the vote rights, do not edit it. It would invalidate the votes casted to the replaced
            ## player on the next run.
            if not self.player_exists(player=replaced_by):
                self._append_to_vote_rights(player=replaced_by, based_on_player=replaced)
        else:
            logging.warning(f'Attempting to replace unknown player {replaced} with {replaced_by}')


    def remove_player(self, player_to_remove:str):
        """Attempt to remove a player from the game. This means eliminating all
        the votes casted to and casted by this player.

        Args:
            player_to_remove (str): The player to remove.
        """
        if self.player_exists(player=player_to_remove):

            self._votes_by_player = self._vote_table[self._vote_table['player'] == player_to_remove]
            self._voted_by_player = self._vote_table[self._vote_table['voted_by'] == player_to_remove]

            self._entries_to_drop = self._vote_table[self._votes_by_player | self._voted_by_player]
            self._vote_table.drop(self._entries_to_drop, inplace=True)

            logging.info(f'Modkilled:{player_to_remove}')
        else:
            logging.warning(f'Attempting to modkill invalid player {player_to_remove}')


    def freeze_player_votes(self, frozen_player:str):
        """Attempt to append a player to the list of frozen players.

        Args:
            frozen_player (str): The player to append.
        """

        if frozen_player not in self.staff: 
            if self.player_exists(player=frozen_player):
                if frozen_player not in self.frozen_players:
                    self.frozen_players.append(frozen_player)
                else:
                    logging.info(f'{frozen_player} is already frozen.')
            else:
                logging.warning(f'Cannot freeze player {frozen_player}. Check vote_config.csv')
        else:
            logging.warning(f'Cannot freeze staff member {frozen_player}.')           


    def lock_unvotes(self):
        """
        Lock the vote count, so that players will not be able to unvote for the
        remaining of the day once a vote is casted. 
        """
        if not self.locked_unvotes:
            self.locked_unvotes = True
            logging.info('The vote count has been locked')


    #TODO: Awful function, fix it
    def _append_vote(self, player:str, victim:str, post_id:int, post_time:int, victim_alias:str, voted_as:str):
        """Append a new vote to the vote count.

        Args:
            player (str): The (lowercased) casting the vote. 
            victim (str): The (lowercased) player receiving the vote.
            post_id (int): The post number where the vote was casted.
            post_time (int): The UNIX epoch time of the post where the vote was casted.
            victim_alias (str): The real name (properly cased) of the player receiving the vote.
            voted_as (str): The vote alias of the player casting the v ote.
        """
        self._vote_table  = self._vote_table.append({'player': victim,
                                                    'voted_by': player,
                                                    'post_id': post_id,
                                                    'post_time': post_time,
                                                    'public_name': victim_alias,
                                                    'voted_as': voted_as,
                                                    'bot_cycle': self.bot_cycle},
                                                    ignore_index=True)
        
        self._update_vote_history()
        logging.info(f'{player} voted {victim} at {post_id}')


    def _remove_vote(self, player:str, victim:str):
        """Remove a given vote from the vote table. They are always
        removed from the oldest to the newest casted vote. 

        Args:
            player (str): The player who removes the vote.
            victim (str): The unvoted player. Can be set to "none" to remove the oldest vote no matter the victim.
        """
        if victim == 'none': ## Remove the oldest vote
            self._old_vote = self._vote_table[self._vote_table['voted_by'] == player].index[0]
        else:
            self._old_vote = self._vote_table[(self._vote_table['player'] == victim) & (self._vote_table['voted_by'] == player)].index[0]
        
        ## Always remove the oldest vote casted
        self._vote_table.drop(self._old_vote, axis=0, inplace=True)
        
        logging.info(f'{player} unvoted {victim}.')
    

    def _update_vote_history(self):
        """Attempt to update the vote history with the last vote from the vote table.
           Any vote already present will be skipped.
        """

        self._last_vote        = self._vote_table.iloc[-1,:]

        if len(self._vote_history) > 0:
            self._columns_to_check = ['player', 'public_name',
                                      'voted_by','voted_as',
                                      'post_id','post_time']

            # Check for a perfect match in all columns but bot_cycle
            self._already_appended = self._vote_history[self._columns_to_check] == self._last_vote[self._columns_to_check]
            self._already_appended = self._already_appended.all(axis=1)
    
            self._same_cycle       = (self._vote_history[self._already_appended]['bot_cycle']  == self.bot_cycle).any()
            self._already_appended = self._already_appended.any()

            ## Two votes sharing every column and cycle come from the same user double voting
            if not self._already_appended or (self._already_appended and self._same_cycle):
                self._vote_history = self._vote_history.append(self._last_vote, ignore_index=True)
                
        else:
            self._vote_history = self._vote_history.append(self._last_vote, ignore_index=True)


    def save_vote_history(self):
        """Save the vote history to a file called vote_history.csv"""
        self._vote_history.to_csv('vote_history.csv', sep=',', index=False)


    def _append_to_vote_rights(self, player:str, based_on_player:str):
        """Add a player to the vote_rights table by copying the vote rights of
        another player.

        Args:
            player (str): The name of the player entry to add to the table.
            based_on_player (str): The name of a player whose vote rights will be used
            for the new player.
        """
        ## Get the rights reg. to base the new entry on
        self._old_player = self.vote_rights.loc[based_on_player].to_dict()

        # Change the player name
        self._old_player['player'] = player

        # Create a 1 row dataframe whose index is the lowercased player name
        self._new_vote_rights = pd.DataFrame(self._old_player, index=[player.lower()])

        # Append it to the end of the vote rights table
        self.vote_rights = self.vote_rights.append(self._new_vote_rights)

        # Just in case the bot closes, let's update the vote_rights. 
        #TODO: Find  a better way to do this. 
        logging.info(f'Updated vote_rights.csv with {player}')
        self.vote_rights.to_csv('vote_config.csv', sep=',', index=False, header=True)