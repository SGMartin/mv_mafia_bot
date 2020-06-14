import requests

from bs4 import BeautifulSoup

class MafiaBot:

    def __init__(self, game_url: str):

         #TODO: response error handling
        response = requests.get(game_url)

        # Load parser for the first page HTML code
        first_page_parser = BeautifulSoup(response.text, 'html.parser')

        self.page_count = 1
        self.game_title = self.get_game_title(first_page_parser)
        self.game_thread = game_url

    def get_game_title(self, parser):
         # Get game name
        game_title = parser.find('title').text
        # Remove the trailing '| Mediavida'
        game_title = game_title.split('|')[0]

        return game_title

    def get_page_count(self, parser):
        #Let's try to parse the page count from the bottom  page panel
        panel_layout = parser.find('div', class_ = 'lv2 pad cf')
        page_count = int(panel_layout.ul.findChildren()[6].text)
        return page_count


    def count_votes_from_page(self, page_to_parse):
        
        # Build a valid URL to scan
        page = self.game_thread + '/' +  str(page_to_parse)
        page = requests.get(page)

        #TODO: what if page does not exists
        parser = BeautifulSoup(page.text, 'html.parser')

        # MV has two different div elements for odd and even posts, 
        # and another one for the very first post of the page

        posts = parser.findAll('div', class_ = ['cf post',
                                                'cf post z',
                                                'cf post first'
                                                ])

        for post in posts:
            author  = post['data-autor']
            post_id = int(post['data-num'])
            post_content = post.find('div', class_ = 'post-contents')
            post_paragraphs = post_content.findAll('p')

            for paragraph  in post_paragraphs:
                if len(paragraph.findAll('strong')) > 0:
                   for bolded_paragraph in paragraph.findAll('strong'):    
                       ## Ok, possible vote here. Call process_vote for
                       ## further checks
                       self.process_vote_candidate(bolded_paragraph.text, author, post_id)
                       
    
    def process_vote_candidate(self, bold_text, author, post_id):

        # Check the player is not unvoting
        if 'desvoto'  in bold_text.lower():
            print(author,'is unvoting', 'at', post_id)

        # Check for the vote: struct
        if 'voto:' in bold_text.lower():
            # Remove white spaces,  if any
            player = bold_text.split(':')[1]
            player = player.replace(' ', '')

            # TODO: Check against player list
            print(author, 'voted', player, 'at', post_id)    