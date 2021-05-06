from neo4j import GraphDatabase, basic_auth
from neo4j.exceptions import Neo4jError
import neo4j.time
import os
def description_read():
    return 'read module from db'
def cprint(content,module='DEBUG',*args):
    if args:
        print('\033[1;32;43m ['+module+'] \033[0m '+ content + '\033[1;35m' +str(args) +' \033[0m' + time.strftime(" |%Y-%m-%d %H:%M:%S|", time.localtime()) )
    else:
        print('\033[1;32;43m ['+module+'] \033[0m '+ content + time.strftime(" |%Y-%m-%d %H:%M:%S|", time.localtime()))

def get_nodes(session,label,limit):
    '''
    Return Nodes with a given label
    Args:
        session: db session,driver.session()
        labels: ["Human"]
        limit: max number of nodes
    Return:
        Cypher result
    '''
    def _cypher(tx,label,limit):
        return list(tx.run(
            '''
            MATCH (n:$label) RETURN n LIMIT $limit
            ''', {'label': label , 'limit': limit}
        ))
    result = session.read_transaction(_cypher,label,limit)
    cprint('Get '+str(len(result))+' records','DB')
    return result

def fetch_all_tags(session):
    '''
    Fetch all nodes with label 'Tag'
    Args:
        session: db session,driver.session()
    Return:
        Cypher result, all nodes with label 'Tag'
    '''
    def _cypher(tx):
        return list(tx.run(
        '''
        MATCH (n:Tag)-[:HAS_TAG]-(ARTICLE) RETURN DISTINCT n
        '''
        ))
    result = session.read_transaction(_cypher)
    cprint(str(len(result))+'record fetched','DB')
    return result  