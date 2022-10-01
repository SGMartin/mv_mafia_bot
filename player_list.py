import logging

class Players:
    
    def __init__(self, players: list):
        self.players = list(set(players))     


    def player_exists(self, player:str):
        if player in self.players:
            return True
        else:
            return False


    def remove_player(self, player: str):
        if self.player_exists(player):
            self.players.remove(player)
        else:
            logging.info("Cannot remove {player}. {player} not present.")   


    def replace_player(self, player_out: str, player_in :str):
        if self.player_exists(player_out) and not self.player_exists(player_in):
            self.remove_player(player_out)
            self.players.append(player_in)
        else:
            logging.info("Ignoring replacement {player_out} by {player_in}")
       