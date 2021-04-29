from flask_restful_swagger_2 import Schema
class TagModel(Schema):
    type = 'object'
    properties = {
        'name':{
            'type': 'string',
        },
        'keywords_for_search':{
            'type': 'string',
        }
    }
def serialize_tag(tag):
    return{
        'name':tag['name'],
        'keywords_for_search':tag['keywords_for_search']
    }