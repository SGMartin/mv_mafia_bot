import math
import requests
import re

from bs4 import BeautifulSoup

from modules.game_actions import GameAction
from states.stage import Stage


def get_game_phase(game_thread, game_master) -> tuple:
        '''
        Parse the GM posts to figure out if the game is currently on game phase.
        Parameters: None

        Returns: an enumeration with the following values:
        - Day: 1
        - Night: 2
        - End: 3
        '''
        
        post_id = 1

        gm_posts         = game_thread + '?u=' + game_master
        gm_posts         = requests.get(gm_posts).text

        # Get total gm pages
        gm_pages = get_page_count_from_page(gm_posts)

        # We'll start looping from the last page to the previous one
        for pagenum in range(gm_pages, 0, -1):

            request      = f'{game_thread}?u={game_master}&pagina={pagenum}'
            request      = requests.get(request).text
            current_page = BeautifulSoup(request, 'html.parser')

            #TODO: log these iterations?
            posts        = current_page.find_all('div', attrs={'data-num':True,
                                                               'data-autor':True})
          
            for post in reversed(posts): # from more recent to older posts

                headers = post.find_all('h2') # get all GM h2 headers

                for pday in headers:
                    
                    game_end      = re.findall('^Final de la partida', pday.text)
                    stage_end     = re.findall('^Final del día [0-9]*', pday.text)
                    stage_start   = re.findall('^Día [0-9]*', pday.text)

                    post_id       = int(post['data-num'])

                    ## TODO: This could be improved
                    if game_end:
                        return (Stage.End, post_id)
                    elif stage_end:
                      return (Stage.Night, post_id) 
                    elif stage_start:
                        return (Stage.Day, post_id)


def get_player_list(game_thread:str, start_day_post_id:int) -> list():
    '''
    Based on a given post ID representing the day start, this function parses
    said post to retrieve a list of alive players by extracting all <ol> and
    <a> elements. 

    This is based on a day start scheme which must be used for the bot to
    work properly.

    Parameters:\n 
    post_id: The ID of the post which starts the game day.

    Returns:\n 
    A list (collection) of (string) players.
    '''
    start_day_page = get_page_number_from_post(start_day_post_id)

    request_url = f'{game_thread}/{start_day_page}'
    request     = requests.get(request_url).text

    response  = BeautifulSoup(request, 'html.parser')
    all_posts = response.find_all('div', attrs={'data-num':True,
                                                                'data-autor':True})
        
    player_list = []

    for post in all_posts:

        # We found the post of interest
        if int(post['data-num']) == start_day_post_id: 

            # Get the first list. It should be the player lists according to the template
            players = post.find('ol').find_all('a')

            for player in players:
                player_list.append(player.contents[0].lower().strip())

            return player_list

#TODO: refactor candidate
def get_last_votecount(game_thread:str, bot_id:str) -> tuple:
    '''
    Parses the bot messages in the game thread to get the post id of the 
    last automated vote count pushed.
    
    Parameters:
    game_thread: A string representing the game thread
    bot_id: Bot name.

    Returns:
    A tuple of two values: an int being the post ID of the last votecount
    and a boolean indicating if the last votecount was an EoD votecount.
    '''

    bot_posts         = f'{game_thread}?u={bot_id}'
    bot_posts         = requests.get(bot_posts).text

        
    # Get total gm pages
    bot_pages = get_page_count_from_page(bot_posts)

    ## initialize values for the tuple
    last_count_id = 1
    last_count_was_lynch = False

    result = (last_count_id, last_count_was_lynch)

    # We'll start looping from the last page to the previous one
    for pagenum in range(bot_pages, 0, -1):

        request      = f'{game_thread}?u={bot_id}&pagina={pagenum}'
        request      = requests.get(request).text
        current_page = BeautifulSoup(request, 'html.parser')

        #TODO: log these iterations?
        posts        = current_page.find_all('div', attrs={'data-num':True, 'data-autor':True})
          
        for post in reversed(posts): # from more recent to older posts

            headers = post.find_all('h2') #get all GM h2 headers

            for pcount in headers:
                    
                vote_count_post        = re.findall('^Recuento de votos$', pcount.text)
                vote_count_was_lynch   = re.findall('^Recuento de votos final$', pcount.text)

                if vote_count_post or vote_count_was_lynch:

                    if vote_count_was_lynch:
                        last_count_was_lynch = True

                    last_count_id = int(post['data-num'])
                    result        = (last_count_id, last_count_was_lynch)
                    return(result)

    return result

# TODO: refactor candidate
def get_last_vhistory_from(game_thread:str, bot_id:str, player:str) -> tuple:
    '''
    Parses the bot messages in the game thread to get the post id of the 
    last pushed vote history for a given player.
    
    Parameters:
    game_thread: A string representing the game thread
    bot_id: Bot name.
    player: The player whose vote history was pushed.

    Returns:
    The post id of the last vote history pushed for the given player
    '''

    last_vhistory_id = 1

    bot_posts         = f'{game_thread}?u={bot_id}'
    bot_posts         = requests.get(bot_posts).text
  
    # Get total gm pages
    bot_pages = get_page_count_from_page(bot_posts)

    # We'll start looping from the last page to the previous one
    for pagenum in range(bot_pages, 0, -1):

        request      = f'{game_thread}?u={bot_id}&pagina={pagenum}'
        request      = requests.get(request).text
        current_page = BeautifulSoup(request, 'html.parser')

        #TODO: log these iterations?
        posts        = current_page.find_all('div', attrs={'data-num':True, 'data-autor':True})
          
        for post in reversed(posts): # from more recent to older posts

            headers = post.find_all('h2') #get all GM h2 headers

            for pcount in headers:   

                vote_count_post = re.findall(f'^Historial de votos de {player}$', pcount.text)

                if vote_count_post:
                    last_vhistory_id = int(post['data-num'])
                    return last_vhistory_id

    return last_vhistory_id

#TODO: refactor candidate
def get_last_voters_from(game_thread:str, bot_id:str, player:str) -> tuple:
    '''
    Parses the bot messages in the game thread to get the post id of the 
    last pushed voters history for a given player.
    
    Parameters:
    game_thread: A string representing the game thread
    bot_id: Bot name.
    player: The player whose voters history was pushed.

    Returns:
    The post id of the last vote history pushed for the given player
    '''

    last_vhistory_id = 1

    bot_posts         = f'{game_thread}?u={bot_id}'
    bot_posts         = requests.get(bot_posts).text
  
    # Get total gm pages
    bot_pages = get_page_count_from_page(bot_posts)

    # We'll start looping from the last page to the previous one
    for pagenum in range(bot_pages, 0, -1):

        request      = f'{game_thread}?u={bot_id}&pagina={pagenum}'
        request      = requests.get(request).text
        current_page = BeautifulSoup(request, 'html.parser')

        #TODO: log these iterations?
        posts        = current_page.find_all('div', attrs={'data-num':True, 'data-autor':True})
          
        for post in reversed(posts): # from more recent to older posts

            headers = post.find_all('h2') #get all GM h2 headers

            for pcount in headers:   

                vote_count_post = re.findall(f'^Historial de votantes de {player}$', pcount.text)

                if vote_count_post:
                    last_vhistory_id = int(post['data-num'])
                    return last_vhistory_id

    return last_vhistory_id



def get_last_post(game_thread) -> int:
    '''
    Parses the game thread messages to get the post id of the 
    last posted message.
    
    Parameters: None

    Returns:
    An int representing the post id of the last posted message.
    '''

    last_page = request_page_count(game_thread)
    request   = f'{game_thread}/{last_page}'
    request   =  requests.get(request).text

    page      = BeautifulSoup(request, 'html.parser')

    all_posts = page.find_all('div', attrs={'data-num':True, 'data-autor':True})

    return int(all_posts[-1]['data-num'])


def get_actions_from_page(game_thread:str, page_to_scan:int, start_from_post:int) -> list():
    '''
    Parses a defined page of the game thread and retrieves all h4 
    HTML elements, which may be commands or votes (actions). 
    
    Parameters:\n
    page_to_scan (int): A game thread page to parse.

    Returns: a list of instances of class action
    '''
    queue = list()

    parsed_url = f'{game_thread}/{page_to_scan}'
    request    = requests.get(parsed_url).text
        
    parser = BeautifulSoup(request, 'html.parser')

    # MV has unqiue div elements for odd and even posts, 
    # and another one for the very first post of the page.
    # I'm ignoring edit div elements because players should not edit while
    # playing.

    posts = parser.findAll('div', class_ = ['cf post','cf post z','cf post first'])

    for post in posts:

        author          = post['data-autor'].lower()
        post_id         = int(post['data-num'])
        post_time       = int(post.find('span', class_ = 'rd')['data-time'])
        post_content    = post.find('div', class_ = 'post-contents')
        post_commands   = post_content.findAll('h4')

        if post_id > start_from_post:

            for command in post_commands:

                command = command.text.lower()

                Action  = GameAction(post_id=post_id,
                                     post_time=post_time,
                                     contents=command,
                                     author=author)

                queue.append(Action)

    return queue
                    

def request_page_count(game_thread):
    '''
    Performs an HTML request of the game thread and parses the resulting
    HTML code to get the total page length of the thread.

    Parameters: None.

    Returns: 
    An int representing the total page length of the thread.
    '''
        
    request = requests.get(game_thread).text
    page_count = get_page_count_from_page(request)

    return page_count


def get_page_count_from_page(request_text):
    '''
    Parses an used defined HTML code from mediavida.com to extract the page
    count of a given thread. To do so it uses BeautifulSoup as a parser engine.

    Parameters: 
    request_text: A string of HTML text from the requests.get library.

    Returns: 
    An int representing the total page length of the thread.
    '''

    # Let's try to parse the page count from the bottom  page panel
    page_count = 1
    try:
        panel_layout = BeautifulSoup(request_text, 'html.parser') 
        panel_layout = panel_layout.find('div', id = 'bottompanel')

        result     = panel_layout.find_all('a')[-2].contents[0]
        page_count = int(result)

    except:
        page_count = 1
        
    return page_count



def get_page_number_from_post(post_id:int):
    '''
    Calculate the page number of a given post by assuming each game thread
    page has 30 posts.

    Parameters: 
    post_id: The ID of the post of interest.

    Returns: 
    An int representing the page number of the input post.
    '''

    page_number = math.ceil(post_id / 30)

    return page_number 