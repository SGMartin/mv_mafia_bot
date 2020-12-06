from datetime import date
import logging
import math
import os.path
import time

import pandas as pd

import config
import user
import vote_count
import modules.thread_reader as tr
import states.stage as stages
import states.action as actions

def main():

    ## SETUP GLOBAL VARIABLES ##
    global majority_reached
    global player_list
    global settings

    ### SETUP UP PROGRAM LEVEL LOGGER ###
    logger = logging.getLogger("mafia_bot")
    logger.setLevel(logging.DEBUG)

    #TODO: make this configurable
    logging.basicConfig(filename='mafia.log',
                        level=logging.DEBUG,
                        format='%(asctime)s %(message)s')

    # Silence requests logger #
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    settings           = config.Config(file_to_load='config.csv')
    majority_reached   =  False
    
    run(settings.update_time)


def run(update_tick: int):
    '''
    Main bot loop. It iterates each N seconds, as defined by the config file. 
    For each iteration, it parses the game thread if we are on day phase, 
    then counts all the votes and decide if a new vote count should be pushed.

    Parameters: 
    update_tick (int): Seconds to pass between bot iterations.

    Returns: None
    '''
    while(True):

        update_tick     = settings.update_time

        game_status     = tr.get_game_phase(game_thread=settings.game_thread,
                                            game_master=settings.game_master)
       
        if game_status[0] == stages.Stage.Day:


            current_day_start_post = game_status[1]
            VoteCount              = vote_count.VoteCount(settings.game_master)

            print('We are on day time!')
            global player_list
            player_list    = tr.get_player_list(game_thread=settings.game_thread,
                                                start_day_post_id=current_day_start_post)

            last_votecount = tr.get_last_votecount(game_thread=settings.game_thread,
                                                   bot_id=settings.mediavida_user)

            last_votecount_id = last_votecount[0]
            majority_reached  = last_votecount[1]
            
            if not majority_reached:

                last_thread_post  = tr.get_last_post(game_thread=settings.game_thread)

                logging.info(f'Starting vote count. Last vote count: {last_votecount_id}. Last reply: {last_thread_post}')

                start_page = tr.get_page_number_from_post(current_day_start_post)
                page_count = tr.request_page_count(game_thread=settings.game_thread)

                logging.info(f'Detected day start at page: {start_page}')
                logging.info(f'Detected {page_count} pages')

                for cur_page in range(start_page, (page_count + 1)):

                    logging.info(f'Checking page: {cur_page}')

                    action_queue = tr.get_actions_from_page(game_thread = settings.game_thread,
                                                            page_to_scan = cur_page,
                                                            start_from_post = current_day_start_post)

                    logging.info(f'Retrieved {len(action_queue)} actions for page {cur_page}')

                    resolve_action_queue(queue=action_queue, vcount=VoteCount)

                ## get votes casted since last update
                votes_since_update = len(VoteCount._vote_table[VoteCount._vote_table['post_id'] > last_votecount_id].index)

                should_update =  update_thread_vote_count(last_count=last_votecount_id,
                                                          last_post=last_thread_post,
                                                          votes_since_update=votes_since_update)     
                
                
                if should_update:
                    logging.info('Pushing a new votecount')
                    push_vote_count(vote_table=VoteCount.get_vote_table(),
                                    last_parsed_post=last_thread_post)
                else:
                    logging.info('Recent votecount detected. ')
                
            else:
                logging.info('Majority already reached. Skipping...')
                    
        else:
            logging.info('Night phase detected. Skipping...')
            print('We are on night phase!')
            
        logging.info(f'Sleeping for {update_tick} seconds.')  

        print(f'Sleeping for {update_tick} seconds.')
        time.sleep(update_tick)


def update_thread_vote_count(last_count:int, last_post:int, votes_since_update:int) -> bool:
    '''
    Decides if a new vote count should be posted based on:
        
    a) Pending GM requests.\n
    b) How many messages were posted since the last vote count. This is used-defined.

    Parameters: None

    Returns:
    True/False (bool): Whether to push a new vote count.
    '''
    global settings

    post_update = False
    vote_update = False
    # gm_request  = False

    if last_post - last_count >= settings.posts_until_update:
        post_update = True
    elif votes_since_update >= settings.votes_until_update:
        vote_update = True

    return (vote_update |  post_update)


def resolve_action_queue(queue: list, vcount: vote_count.VoteCount):
    '''
    player_list: A list of alive players. Only moderators, the GM and alive
    players may perform game actions.

    Parameters:  \n
    player_list: A list of alive players, excluding moderators and the GM.\n
    queue: A list of game actions.\n
    vcount: The current Vote Count.\n
    '''
    global player_list

    staff = list(map(str.lower, settings.moderators))
    staff.append(settings.game_master.lower())
    
    allowed_actors      = player_list + staff

    for game_action in queue:

        if game_action.author in allowed_actors:

            #TODO: LYNCH CODE HERE
            if game_action.type == actions.Action.vote:

                vcount.vote_player(action=game_action)

                if is_lynched(victim=game_action.victim, vcount=vcount):

                    global majority_reached
                    majority_reached = True

            elif game_action.type == actions.Action.unvote:
                vcount.unvote_player(action=game_action)
    

def get_vote_majority() -> int:
    '''
    Calculates the amount of votes necessary to reach an absolute majority
    and lynch a player based on the amount of alive players. 

    Parameters:  \n
    Returns: \n
    majority (int): The absolute majority of votes required  to lynch a player.
    '''
    global player_list

    if (len(player_list) % 2) == 0:
        majority = math.ceil(len(player_list) / 2) + 1
    else:
        majority = math.ceil(len(player_list) / 2)
                
    return majority


def is_lynched(victim:str, vcount: vote_count.VoteCount) -> bool:
    '''
    Checks if a given player has received enough votes to be lynched. This
    function evaluates if a given player accumulates enough votes by calculating
    the current absolute majority required and adding to it a player specific
    lynch modifier as defined in the vote rights table.

    Parameters:\n 
    victim (str): The player who receives the vote.\n
    Returns:\n 
    True if the player should be lynched.  False otherwise.
    '''
    lynched = False

    # Count this player votes
    lynch_votes     = vcount.get_victim_current_votes(victim)
    player_majority = get_vote_majority() + vcount.get_player_mod_to_lynch(victim)
        
    if lynch_votes >= player_majority:
        lynched = True
        
    return lynched


    
def push_vote_count(vote_table: pd.DataFrame, last_parsed_post: int):
    '''
    When this function is called, a new User object is built to push a vote
    count using the current vote table. The object is deleted when the function
    ends.

    Parameters: \n
    vote_table: A dataframe with the vote table to parse for the post.\n
    last_parsed_post: Last post parsed by the bot.\n
    Returns: None
    '''
    global settings 
    global player_list

    User = user.User(config=settings)
                    
    User.push_votecount(vote_count=vote_table,
                        alive_players=len(player_list),
                        vote_majority=get_vote_majority(),
                        post_id=last_parsed_post)

    del User


def lynch_player(vote_table: pd.DataFrame, victim:str, post_id:int):
        '''
        When this function is called, a new User object is built to push a vote
        count in which the lynch is  announced. It also sets self.majority_reached
        to True, indicating to the bot that no more votes are allowed until a new day starts. 

        Parameters:\n
        vote_table: A dataframe with the vote table to parse for the post.\n
        victim (str): The player to lynch.\n
        post_id  (int): The post ID with the vote that triggered the lynch.\n
        Returns: None
        '''
        global settings

        User = user.User(config=settings)

        User.push_lynch(last_votecount=vote_table,
                        victim=victim,
                        post_id=post_id)



if __name__ == "__main__":
	main()