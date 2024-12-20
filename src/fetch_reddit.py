import os
import requests
import datetime
from jinja2 import Template  # You can use jinja2 for templating. If not available, just inline string.

CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')
USERNAME = os.environ.get('REDDIT_USERNAME')
PASSWORD = os.environ.get('REDDIT_PASSWORD')
USER_AGENT = "DailyFeedScript/1.0"

# Get an OAuth token
def get_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {
        'grant_type': 'password',
        'username': USERNAME,
        'password': PASSWORD
    }
    headers = {'User-Agent': USER_AGENT}
    res = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)
    token = res.json()['access_token']
    return token

def get_top_posts(token, subreddit='chatgpt', limit=10):
    headers = {'Authorization': f'bearer {token}', 'User-Agent': USER_AGENT}
    url = f'https://oauth.reddit.com/r/{subreddit}/top?t=day&limit={limit}'
    res = requests.get(url, headers=headers)
    posts = res.json()['data']['children']
    return posts

def get_top_comments(token, post_id, limit=5):
    headers = {'Authorization': f'bearer {token}', 'User-Agent': USER_AGENT}
    url = f'https://oauth.reddit.com/r/chatgpt/comments/{post_id}?limit={limit}'
    res = requests.get(url, headers=headers)
    # The first object in response is the post, second is comments
    comment_data = res.json()
    if len(comment_data) > 1:
        comments = comment_data[1]['data']['children']
        top_comments = []
        for c in comments:
            if c['kind'] == 't1':
                top_comments.append({
                    'author': c['data']['author'],
                    'body': c['data']['body']
                })
            if len(top_comments) == limit:
                break
        return top_comments
    return []

def generate_html(posts_info):
    # Simple HTML template
    template_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Daily Reddit Feed (r/chatgpt)</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; max-width: 800px; margin: auto; }
            h1 { text-align: center; }
            .post { margin-bottom: 40px; }
            .post-title { font-size: 1.2em; font-weight: bold; }
            .comment { margin-left: 20px; padding: 10px; border-left: 3px solid #ccc; margin-bottom: 10px; }
            .comment-author { font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>Daily Top Reddit Posts from r/chatgpt</h1>
        <p>Updated on {{date}} at 3:00 PM</p>
        {% for post in posts %}
        <div class="post">
            <div class="post-title"><a href="{{post.url}}" target="_blank">{{ post.title }}</a> (by {{ post.author }})</div>
            <p>{{ post.selftext }}</p>
            <h3>Top Comments:</h3>
            {% for comment in post.comments %}
            <div class="comment">
                <div class="comment-author">{{ comment.author }}</div>
                <div class="comment-body">{{ comment.body }}</div>
            </div>
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    </html>
    """
    template = Template(template_str)
    html = template.render(posts=posts_info, date=datetime.datetime.utcnow().strftime("%Y-%m-%d"))
    return html

def main():
    token = get_token()
    posts = get_top_posts(token)
    posts_info = []
    for p in posts:
        data = p['data']
        post_id = data['id']
        title = data['title']
        author = data['author']
        url = f"https://www.reddit.com{data['permalink']}"
        selftext = data['selftext'][:300] + '...' if len(data['selftext']) > 300 else data['selftext']
        comments = get_top_comments(token, post_id)
        posts_info.append({
            'title': title,
            'author': author,
            'url': url,
            'selftext': selftext,
            'comments': comments
        })

    html = generate_html(posts_info)
    # Write to index.html
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    main()
