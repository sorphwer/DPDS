from flask_restful_swagger_2 import Schema
class ArticleModel(Schema):
    type = 'object'
    properties = {
        'id': {
            'type': 'string',
        },
        'title': {
            'type': 'string',
        },
        'url': {
            'type': 'string',
        },
        'main_image_url': {
            'type': 'string',
        },
        'reading_time': {
            'type': 'integer',
        },
        'tag_names': {
            'type': 'string',
        },
        'published_at': {
            'type': 'string',
        },
        'public_reactions_count':{
            'type': 'integer',
        },
        'source_site':{
            'type': 'string',
        },
        'author':{
            'type': 'string',
        },
        'count':{
            'type': 'integer',
        }
    }

def serialize_article(article):
    return {
        'id': article['id'],
        'title': article['title'],
        'url': article['url'],
        'main_image_url': article['main_image_url'],
        'reading_time': article['reading_time'],
        'tag_names': article['tag_names'],
        'published_at': article['published_at'],
        'source_site': article['source_site'],
        'author': article['author'],
        'count': article['count']
    }