import logging
import pandas as pd

import modules.game_actions as actions
class Players:
    
    def __init__(self, players: list, bot_cycle:int):
        try:
            self.attack_table = pd.read_csv("attack_and_defense.csv", sep=",")
        except:
            logging.info('Failed to load attack table. Setting all attacks and defense to 0')
            self.attack_table = pd.DataFrame(self.players, columns = ["player"])
            self.attack_table["attack"] = 0
            self.attack_table["defense"] = 0
            self.attack_table["last_shot"] = 0

        self.attack_table.index = self.attack_table["player"].str.lower()

        try:
            self.shots_history = pd.read_csv("shots_history.csv", sep=",")
            self.fallen = self.shots_history.loc[~self.shots_history["survived"], "victim"].tolist()
            self.players =  list(set(players) - set(self.fallen))
        except:
            logging.info("Failed to load shots history. Starting from scratch")
            self.shots_history = pd.DataFrame(columns=["shooter", "victim", "survived", "post_id", "bot_cycle"])
            self.players = list(set(players))
            self.fallen = []
        
        try:
            self.role_list = pd.read_csv("role_list.csv", sep=",")
        except:
            logging.info("Failed to load role list. Setting all roles to unknown")
            self.role_list = pd.DataFrame(self.players, columns = ["player"])
            self.role_list["team"] = "unknown"
            self.role_list["role"] = "unknown"
        
        self.role_list.index = self.role_list["player"].str.lower()

        self.bot_cycle = bot_cycle

    def player_exists(self, player:str):
        if player in self.players:
            return True
        else:
            return False

    def remove_player(self, player: str):
        if self.player_exists(player):
            self.players.remove(player)
            self.fallen.append(player)
        else:
            logging.info("Cannot remove {player}. {player} not present.")   

    ## TODO: Do this too with the role table
    def replace_player(self, player_out: str, player_in :str):
        if self.player_exists(player_out) and not self.player_exists(player_in):
            self.remove_player(player_out)
            self.players.append(player_in)

            ## copy this player and keep it's attack and defense rights
            if player_in not in self.attack_table.index.tolist():
                self._append_to_attack_table(player=player_in, based_on_player=player_out)
        else:
            logging.info("Ignoring replacement {player_out} by {player_in}")


    def revive_player(self, player_back:str):
        if not self.player_exists(player_back) and player_back in self.fallen:
            self.players.append(player_back)


    def is_valid_shot(self, action:actions):
        self._valid_shot = False

        self._attacker = action.author
        self._victim = action.victim
        self._post_id = action.id 
        if self.player_exists(self._attacker) and self._attacker.lower() in self.attack_table.index:
            if self.player_exists(self._victim) and self._victim.lower() in self.attack_table.index:
                try:
                    self._attack_rights = self.get_player_offense(self._attacker)
                    self._defense_rights = self.get_player_defense(self._victim)

                    if self._attack_rights > 0:
                        ## check if we are seeing a double shooter or a previous action
                        self._last_shot, self._old_cycle = self.get_player_last_shot(self._attacker)
                        self._double_shooter = self._last_shot == self._post_id and self.bot_cycle == self._old_cycle

                        if self._last_shot != self._post_id or self._double_shooter:
                            self._valid_shot = True
                    else:
                        logging.info(f"{self._attacker} has no rights to shoot!")
                except:
                    logging.ERROR(f"{self._attacker} or {self._victim} rights not found in attack table. Invalid shot")
            else:
                logging.info(f"{self._victim} does not exists in the shoots rights table.")
        else:
            logging.info(f"{self._attacker} does not exists in the shoots rights table.")

        return self._valid_shot   
    
    def get_player_offense(self, player:str):
        self._offense = 0
        try:
            self._offense = int(self.attack_table.loc[player.lower(), "attack"])
        except:
            logging.warn(f"{player} offensive rights not found in attack table. Corruption?")

        return self._offense
    
    def get_player_defense(self, player:str):
        self._defense = 0
        try:
            self._defense = int(self.attack_table.loc[player.lower(), "defense"])
        except:
            logging.warn(f"{player} defensive rights not found in attack table. Corruption?")

        return self._defense
    
    def get_player_team(self, player:str):
        self._team = "unknown"
        try:
            self._team = self.role_list.loc[player.lower(), "team"]
        except:
            logging.warn(f"{player} team not found. Corruption?")
        
        return self._team
    
    def get_player_role(self, player:str):
        self._role = "unknown"
        try:
            self._role = self.role_list.loc[player.lower(), "role"]
        except:
            logging.warn(f"{player} role not found. Corruption?")
        
        return self._role
    
    def reduce_player_offense(self, player:str, offset:int = 1):
        self._last_offense = self.get_player_offense(player)
        self._new_offense = int(self._last_offense) - abs(offset)

        if self._new_offense < 0:
            self._new_offense = 0
        
        self.attack_table.loc[player.lower(), "attack"] = self._new_offense
        logging.info(f"Update {player} attack: {self._last_offense} to {self._new_offense}")
        self.attack_table.to_csv('attack_and_defense.csv', sep=',', index=False, header=True)
    
    def reduce_player_defense(self, player:str, offset:int = 1):
        self._last_defense = self.get_player_defense(player)
        self._new_defense = int(self._last_defense) - abs(offset)

        if self._new_defense < 0:
            self._new_defense = 0
        
        self.attack_table.loc[player.lower(), "defense"] = self._new_defense
        logging.info(f"Update {player} defense: {self._last_defense} to {self._new_defense}")
        self.attack_table.to_csv('attack_and_defense.csv', sep=',', index=False, header=True)

    
    def get_player_last_shot(self, player:str):
        self._last_shot = self.shots_history[self.shots_history["shooter"] == player]["post_id"]
        self._last_bot_cycle = self.shots_history[self.shots_history["shooter"] == player]["bot_cycle"]

        if len(self._last_shot) == 0:
            return (0, 0)
        else:
            ## return the most recent post id
            return (self._last_shot.iloc[-1], self._last_bot_cycle.iloc[-1])

    def shoot_player(self, action:actions):
        # True/False if shot is valid and True/False if victim was killed    
        self._result = (False, False)

        if self.is_valid_shot(action):
            self._attacker = action.author.lower()
            self._victim = action.victim.lower()

            if self.get_player_defense(self._victim) - 1 < 0:
                self.remove_player(self._victim)
                self._result = (True, True)
            else:
                self.reduce_player_defense(self._victim)
                self._result = (True, False)

            self.reduce_player_offense(self._attacker)
            self.update_last_shot(action)
                
        return self._result
    
    def update_last_shot(self, action:actions):
        self._shooter = action.author
        self._shot_id = action.id
        self._previous_shooting_id, self._previous_cycle = self.get_player_last_shot(self._shooter)

        if self._shot_id > self._previous_shooting_id or self._previous_cycle == self.bot_cycle:
            self.attack_table.loc[self._shooter.lower(), "last_shot"] = int(self._shot_id)
            # update the table too
            logging.info(f"Update shooting history and table after valid shot for {self._shooter} at {self._shot_id}")
            self.attack_table.to_csv('attack_and_defense.csv', sep=',', index=False, header=True)
                        
            self._shot_to_update = pd.Series(
                 {
                        "shooter": self._shooter.lower(),
                        "victim": action.victim.lower(),
                        "survived": self._victim in self.players,
                        "post_id": self._shot_id,
                        "bot_cycle": self.bot_cycle
                    }
            )
            if len(self.shots_history) == 0:
                # update shots history
                self.shots_history = self.shots_history.append(self._shot_to_update, ignore_index=True)
            else:
                self._columns_to_check = ["shooter", "victim", "survived", "post_id"]

                # Check for a perfect match in all columns but bot_cycle
                self._already_appended = self.shots_history[self._columns_to_check] == self._shot_to_update
                self._already_appended = self._already_appended.all(axis=1)

                self._same_cycle = (self.shots_history[self._already_appended]["bot_cycle"] == self.bot_cycle).any()
                self._already_appended = self._already_appended.any()

                # Two shots sharing every column adn cycle come from the same user double shooting
                if not self._already_appended or (self._already_appended and self._same_cycle):
                    self.shots_history = self.shots_history.append(self._shot_to_update, ignore_index=True)
            
            self.shots_history.to_csv("shots_history.csv", sep =",", index=False, header=True)


    def _append_to_attack_table(self, player:str, based_on_player:str):
        """Add a player to the attack_and_defense table by copying the rights of
        another player.

        Args:
            player (str): The name of the player entry to add to the table.
            based_on_player (str): The name of a player whose vote rights will be used
            for the new player.
        """
        ## Get the rights reg. to base the new entry on
        self._old_player = self.attack_table.loc[based_on_player].to_dict()

        # Change the player name
        self._old_player['player'] = player

        # Create a 1 row dataframe whose index is the lowercased player name
        self._new_attack_and_defense = pd.DataFrame(self._old_player, index=[player.lower()])

        # Append it to the end of the vote rights table
        self.attack_table = self.attack_table.append(self._new_attack_and_defense)

        # Just in case the bot closes, let's update the vote_rights. 
        #TODO: Find  a better way to do this. 
        logging.info(f'Updated attack table with {player}')
        self.attack_table.to_csv('attack_and_defense.csv', sep=',', index=False, header=True)