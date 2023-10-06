from .schema import *
import asks

DBMi = DBM()
SESS = s = asks.Session(connections=100)