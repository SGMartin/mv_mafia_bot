import logging

import states.action as actions

class GameAction:
    def __init__(self, post_id:int, post_time:int, contents:str, author:str):

        ## Instance variables
        self.id                 = post_id
        self.post_time          = post_time
        self.author, self.alias = author, author
        self.victim             = 'none'
        self._contents          = contents.lower().rstrip('.').split(' ')

        ## Available commands
        self._action_responses = { actions.Action.vote: self._parse_vote,
                                   actions.Action.unvote: self._parse_unvote}

        # Parse command type
        self.type   = self._parse_expression(command=self._contents[0])

        # Execute command
        if self.type != actions.Action.unknown:

            self._response = self._action_responses.get(self.type, self._default_not_found)
            self._response(argument=self._contents)


    def _parse_expression(self, command: str) -> actions.Action:

        self._command = command

        ## attempt to clean up common sentence pauses
        to_remove = ',:'
        self._command = self._command.rstrip(to_remove)
        
        try:
            action = actions.Action(self._command)
            return action
        except: 
            #TODO: build upon this
            logging.error(f'Unknown action: {self._command}')
            return actions.Action.unknown


    def _parse_vote(self, argument:str):

        if 'como' in argument:
            self.alias = argument[-1]

        if 'no linchamiento' in argument:
            self.victim = 'no_lynch'
        else:
            self.victim = argument[-3] if self.alias != self.author else argument[-1]


    def _parse_unvote(self, argument:str):
        self.victim = argument[-1] if len(argument) > 1 else 'none'
    
    def _default_not_found(self, argument:str):
        logging.warning(f'No method to resolve action: {self.type}. Defaulting to unknown')
        self.type = actions.Action.unknown
        
