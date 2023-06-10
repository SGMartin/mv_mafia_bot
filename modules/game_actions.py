import logging
import re
import states.action as actions

class GameAction:
    def __init__(self, post_id: int, post_time: int, contents: str, author: str):

        ## Instance variables
        self.id = post_id
        self.post_time = post_time
        self.actor, self.author, self.alias = author, author, author

        self.victim = "none"
        self.target_post = 0
        self._contents = contents.lower().rstrip(".").split(" ")

        ## Available commands
        self._action_responses = {
            actions.Action.vote: self._parse_vote,
            actions.Action.unvote: self._parse_unvote,
            actions.Action.replace_player: self._replace_player,
            actions.Action.request_count: self._parse_vote_count_request,
            actions.Action.vote_history: self._set_victim_from_arg,
            actions.Action.get_voters: self._set_victim_from_arg,
            actions.Action.kill: self._set_victim_from_arg,
            actions.Action.modkill: self._set_victim_from_arg,
            actions.Action.winner: self._set_victim_from_arg,
            actions.Action.freeze_vote: self._freeze_votes,
            actions.Action.lylo: self._set_lylo,
            actions.Action.reveal: self._reveal_mayor,
            actions.Action.shoot: self._set_victim_from_arg,
            actions.Action.revive: self._set_victim_from_arg,
        }

        # Parse command type
        self.type = self._parse_expression(command=self._contents[0])

        # Execute command
        if self.type != actions.Action.unknown:

            # Attempt to remove the trailing dot from action sentence
            self._contents[-1] = self._contents[-1].rstrip(".")

            self._response = self._action_responses.get(
                self.type, self._default_not_found
            )
            self._response(argument=self._contents)

    def _set_victim(self, victim:str):
        
        self._new_victim = re.sub("[()]","", victim)
        self.victim = self._new_victim

    def _set_victim_from_arg(self, argument: list):
         self.victim = argument[-1]
    
    def _parse_expression(self, command: str) -> actions.Action:

        self._command = command

        ## attempt to clean up common sentence pauses
        self._command = self._command.rstrip(",:")

        try:
            action = actions.Action(self._command)
            return action
        except:
            # TODO: build upon this
            logging.error(f"Unknown action: {self._command}")
            return actions.Action.unknown

    def _parse_vote(self, argument: list):

        if "como" in argument:
            self.alias = argument[-1]

        if "no" in argument and "linchamiento" in argument:
            self._this_victim = "no_lynch"
        else:
            self._this_victim  = argument[-3] if self.alias != self.author else argument[-1]
        
        self._set_victim(self._this_victim)

    def _parse_unvote(self, argument: list):

        self.victim = argument[-1] if len(argument) > 1 else "none"

    def _parse_vote_count_request(self, argument: list):

        ## Check if the vote count request is the default ### Recuento
        if len(argument) > 1:

            # People will use this character to reference post
            self._post_candidate = argument[-1].strip("#")
            try:
                self.target_post = int(self._post_candidate)
            except:
                logging.warning(
                    f"Cannot parse vote count request for player {self.author} at {self.id}"
                )

    def _replace_player(self, argument: list):
        """
        Returns the subbed player as actor and the substitute name as victim.
        """
        # for flexibility, the first word after command will be the player
        # who is subbing out and the last word, the substitute.
        self.actor = re.sub("[()]","", argument[1])
        self._set_victim(argument[-1])

        
    def _request_vote_history(self, argument:list):
        self._set_victim(argument[1])


    def _request_voters_history(self, argument:list):
        self._set_victim(argument[1])


    def _modkill(self, argument:list):
        self._set_victim(argument[1])
    
    def _set_lylo(self, argument:list):
        self.target_post = self.id

    def _freeze_votes(self, argument: list):
        
        self.target_post = self.id

        if len(argument) > 1:
            self._set_victim(argument[1])
    
    def _reveal_mayor(self, argument: list):
        self.actor = self.author

    def _default_not_found(self, argument: str):
        logging.warning(
            f"No method to resolve action: {self.type}. Defaulting to unknown"
        )
        self.type = actions.Action.unknown
