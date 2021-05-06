from neo4j import GraphDatabase, basic_auth
from neo4j.exceptions import Neo4jError
import neo4j.time
import os
def description_write():
    return 'write module from db'
def cprint(content,module='DEBUG',*args):
    if args:
        print('\033[1;32;43m ['+module+'] \033[0m '+ content + '\033[1;35m' +str(args) +' \033[0m' + time.strftime(" |%Y-%m-%d %H:%M:%S|", time.localtime()) )
    else:
        print('\033[1;32;43m ['+module+'] \033[0m '+ content + time.strftime(" |%Y-%m-%d %H:%M:%S|", time.localtime()))

def create_nodes(session,labels,properties):
    '''
    Create nodes with custom labels and properties
    Args:
        session: db session,driver.session()
        labels: ["Human", "MovieStar"]
        properties => [{name: "Tom Cruise", placeOfBirth: "Syracuse, New York, United States"},
                        {name: "Reese Witherspoon", placeOfBirth: "New Orleans, Louisiana, United States"}]
    Return:
        Added nodes 
    '''
    def _cypher(tx, labels, properties):
                return list(tx.run(
                    '''
                    CALL apoc.create.nodes( $labels, $properties);
                    ''', {'labels': labels , 'properties': properties}
                ))
    result = session.write_transaction(_cypher,labels,properties)
    cprint(str(len(result))+'record added','DB')
    return result



def create_relation(session,label,props,id1,id2):
    '''
    Create relation with specific id
    Args:
        session: db session,driver.session()
        labels: ["Human"]
        limit: max number of nodes
    Return:
        Cypher result
    '''
    def _cypher(tx,label,id1,id2,props):
        return list(tx.run(
        '''
        MATCH (p) WHERE id(p) = $id1
        MATCH (m) WHERE id(m) = $id2
        CALL apoc.create.relationship(p, $label, $props, m)
        YIELD rel
        RETURN rel;
        ''',{'label':label,'props':props,'id1':id1,'id2':id2}
        ))
    result = session.write_transaction(_cypher,label,props,id1,id2)
    cprint(str(len(result))+'record added','DB')
    return result

def create_tag_relation_to_article(session,tag_name,article_url):
    '''
    Args: db session, Tag.name, Article.url
    Return: cypher result of created relation
    '''
    def _cypher(tx,tag_name,article_url):
#CALL apoc.create.relationship(a, "HAS_TAG",{article_id:$article_id, tag_name:$tag_name},  t)
        return list(tx.run(
        '''
        MATCH (a:Article {url: $article_url})
        MATCH (b:Tag {name: $tag_name})
        MERGE (a)-[rel:HAS_TAG]->(b)
        RETURN rel
        ''',{'article_url':article_url,'tag_name':tag_name}
        
        ))    
    result = session.write_transaction(_cypher,tag_name,article_url)
    return result

def create_author_relation_to_article(session):
    '''
    Request: csv file
    Args: db session
    Return: None
    '''
    def _cypher(tx,url,username):
        return list(tx.run(
        '''
        MATCH (a:Article {url: $url})
        MATCH (b:Author {username: $username})
        MERGE (a)-[rel:WRITTEN_BY]->(b)
        RETURN rel
        ''',{'url':url,'username':username}
        ))
    if os.path.exists(DATA_FILE_PATH):
        if not os.path.getsize(DATA_FILE_PATH):
            cprint(DATA_FILE_PATH +'is empty')
        else:
            with open(DATA_FILE_PATH, mode='r',encoding="utf-8") as data_file_r:
                csv_reader = csv.DictReader(data_file_r)
                line_count = 0
                props=set()
                for row in csv_reader:
                    if line_count == 0:
                        cprint(f'Processing CSV header {", ".join(row)}','CSV')
                        line_count += 1
                    session.write_transaction(_cypher,row['url'],row['author_username'])
                    line_count += 1
                cprint(f'File processed successfully with {line_count-1} ids.','CSV')
                cprint(f'Added {line_count-1} relations.','DB')
            data_file_r.close()
    else:
        cprint(DATA_FILE_PATH +' does not exist')
def create_subsume_relation(session,parent_tag,child_tag):
    '''
    Create relation: (parent_tag)-[SUBSUME]->(child_tag)
    Args:
        session: db session,driver.session()
        parent_tag: string, name of tag
        child_tag: string, name of tag
    Return:
        Cypher result of created relation
    '''
    if not parent_tag:
        return 'parent tag is empty'
    if not child_tag:
        return 'child tag is empty'
    def _cypher(tx,parent_tag,child_tag):
        return list(tx.run(
        '''
        MERGE (n:Tag {name:$parent_tag})
        MERGE (m:Tag {name:$child_tag})
        MERGE (n)-[subsume:SUBSUME]-> (m)
        RETURN subsume
        ''',{'parent_tag': parent_tag , 'child_tag': child_tag}
        ))
    result = session.write_transaction(_cypher,parent_tag,child_tag)
    return result

def add_keywords_to_tag(session,tag_name,keyword):
    '''
    Update attribution 'keywords' of Tag node
    Args:
        session: db session,driver.session()
        tag_name: string of tag name
        keyword: string of keyword to add
    Return:
        Cypher result of updated node
    Error Return:
        String with specific info
    '''
    
    if not keyword:
        return 'keyword is empty'
    if not tag_name:
        return 'tag name is empty'
    else:
        keyword = keyword.replace("+", " ")
    def _cypher_get_node(tx,tag_name):
        return list(tx.run(
        '''
        MATCH (n:Tag {name:$tag_name})
        RETURN n
        ''',{'tag_name':tag_name}
        ))
    def _cypher_update_node(tx,tag_name,new_keyword):
        return list(tx.run(
        '''
        MATCH (n:Tag {name:$tag_name})
        SET n.keywords_for_search = $keyword
        RETURN n
        ''',{'tag_name' : tag_name,'keyword' : new_keyword}
        ))
    
    tag_node = session.read_transaction(_cypher_get_node,tag_name)

    if tag_node:
        old_keywords = serialize_tag(tag_node[0]['n'])['keywords_for_search']
    else:
        return 'No such Tag node'
    if (old_keywords):
        if keyword in old_keywords:
            return 'keyword is already logged'
        new_keyword = old_keywords+'+'+keyword
    else:
        new_keyword = keyword

    result = session.write_transaction(_cypher_update_node,tag_name,new_keyword)
    return result
     