import logging

import states.action as actions

#TODO: Move this to its own file
class VoteCountRequest:
    def __init__(self, author:str, post_id:int, count_to_post:int):

        self.author        = author
        self.id            = post_id
        self.count_to_post = count_to_post

      #  print(f'Recuento hasta {self.count_to_post} por {self.author}')


class GameAction:
    def __init__(self, post_id:int, post_time:int, contents:str, author:str):

        ## Instance variables
        self.id                 = post_id
        self.post_time          = post_time
        self.actor, self.author, self.alias = author, author, author

        self.victim             = 'none'
        self.action             =  None
        self._contents          = contents.lower().rstrip('.').split(' ')

        ## Available commands
        self._action_responses = { actions.Action.vote: self._parse_vote,
                                   actions.Action.unvote: self._parse_unvote,
                                   actions.Action.replace_player: self._replace_player,
                                   actions.Action.request_count: self._parse_vote_count_request,
                                   actions.Action.vote_history: self._request_vote_history}

        # Parse command type
        self.type   = self._parse_expression(command=self._contents[0])

        # Execute command
        if self.type != actions.Action.unknown:
            
            # Attempt to remove the trailing dot from action sentence
            self._contents[-1] = self._contents[-1].rstrip('.')

            self._response = self._action_responses.get(self.type, self._default_not_found)
            self._response(argument=self._contents)


    def _parse_expression(self, command: str) -> actions.Action:

        self._command = command

        ## attempt to clean up common sentence pauses
        self._command = self._command.rstrip(',:')
        
        try:
            action = actions.Action(self._command)
            return action
        except: 
            #TODO: build upon this
            logging.error(f'Unknown action: {self._command}')
            return actions.Action.unknown


    def _parse_vote(self, argument:list):

        if 'como' in argument:
            self.alias = argument[-1]

        if 'no linchamiento' in argument:
            self.victim = 'no_lynch'
        else:
            self.victim = argument[-3] if self.alias != self.author else argument[-1]


    def _parse_unvote(self, argument:list):

        self.victim = argument[-1] if len(argument) > 1 else 'none'
    
    
    def _parse_vote_count_request(self, argument:list):

        self._count_until_post = -1

        ## Check if the vote count request is the default ### Recuento
        if len(argument) > 1:
            # People will use this character to reference post
            self._post_candidate = argument[-1].strip('#') 
            try:
                self._count_until_post = int(self._post_candidate)
            except:
                logging.warning(f'Cannot parse vote count request for player {self.author} at {self.id}')

        self.action = VoteCountRequest(author=self.author, post_id=self.id, count_to_post=self._count_until_post)


    def _replace_player(self, argument:list):
        '''
        Returns the subbed player as actor and the substitute name as victim.
        '''
        # for flexibility, the first word after command will be the player
        # who is subbing out and the last word, the substitute.
        self.actor  = argument[1]
        self.victim = argument[-1]
        
    def _request_vote_history(self, argument:list):
        self.victim = argument[-1]

    def _default_not_found(self, argument:str):
        logging.warning(f'No method to resolve action: {self.type}. Defaulting to unknown')
        self.type = actions.Action.unknown
        
