import requests

#per_page : number of articles
#page : page number
def get_dev_to_url(per_page,page):
    return 'https://dev.to/search/feed_content?per_page={}&page={}&sort_by=public_reactions_count&sort_direction=desc&approved=&class_name=Article&published_at%5Bgte%5D=2020-03-29T13%3A57%3A39Z'.format(per_page,page)

resp = requests.get(get_dev_to_url(1,1))
if resp.status_code != 200:
    # This means something went wrong.
    raise ApiError('GET Status Code:{}'.format(resp.status_code))

print(resp.json())