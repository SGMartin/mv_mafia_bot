import enum

class Action(enum.Enum):
    vote          = 'voto'
    unvote        = 'desvoto'
    replace       = 'reemplazo'
    unknown       = 'unknown'
    request_count = 'recuento'