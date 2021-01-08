import enum

class Action(enum.Enum):
    vote          = 'voto'
    unvote        = 'desvoto'
    replace       = 'reemplazo'
    unknown       = 'unknown'
    request_count = 'recuento'
    replace_player = 'reemplazo'
    vote_history   = 'historial'
    get_voters     = 'votantes'
    