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

def get_top_posts(token, subreddit='singularity', limit=20):
    headers = {'Authorization': f'bearer {token}', 'User-Agent': USER_AGENT}
    url = f'https://oauth.reddit.com/r/{subreddit}/top?t=day&limit={limit}'
    res = requests.get(url, headers=headers)
    posts = res.json()['data']['children']
    return posts

def get_top_comments(token, post_id, limit=3):
    headers = {'Authorization': f'bearer {token}', 'User-Agent': USER_AGENT}
    url = f'https://oauth.reddit.com/r/chatgpt/comments/{post_id}?limit={limit}&sort=best'
    res = requests.get(url, headers=headers)
    # The first object in response is the post, second is comments
    comment_data = res.json()
    if len(comment_data) > 1:
        comments = comment_data[1]['data']['children']
        top_comments = []
        for c in comments:
            if c['kind'] == 't1':
                replies = []
                if c['data'].get('replies'):
                    for reply in c['data']['replies']['data']['children'][:3]:
                        if reply['kind'] == 't1':
                            replies.append({
                                'author': reply['data']['author'],
                                'body': reply['data']['body']
                            })
                top_comments.append({
                    'author': c['data']['author'],
                    'body': c['data']['body'],
                    'replies': replies
                })
            if len(top_comments) == limit:
                break
        return top_comments
    return []

def generate_html(posts_info):
    template_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Daily Reddit Feed (r/chatgpt)</title>
        <style>
            :root {
                --primary-color: #1a1a1b;
                --secondary-color: #ffffff;
                --accent-color: #ff4500;
                --border-color: #343536;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                padding: 20px;
                max-width: 1000px;
                margin: auto;
                background: var(--primary-color);
                color: var(--secondary-color);
            }
            h1 {
                text-align: center;
                color: var(--accent-color);
            }
            .post {
                margin-bottom: 40px;
                padding: 20px;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                background: #222222;
            }
            .post-title {
                font-size: 1.4em;
                font-weight: bold;
                margin-bottom: 15px;
            }
            .post-title a {
                color: var(--secondary-color);
                text-decoration: none;
            }
            .post-title a:hover {
                color: var(--accent-color);
            }
            .post-author {
                color: #4fbcff;
                margin-bottom: 15px;
            }
            .post-content {
                margin: 15px 0;
            }
            .media-container {
                position: relative;
                width: 100%;
                height: 0;
                padding-bottom: 56.25%; /* 16:9 aspect ratio */
                margin: 15px 0;
            }
            .media-container img, .media-container video {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: cover;
                border-radius: 4px;
            }
            .comment {
                margin: 15px 0;
                padding: 15px;
                border-left: 3px solid var(--accent-color);
                background: #2d2d2d;
                border-radius: 0 8px 8px 0;
            }
            .comment-author {
                font-weight: bold;
                color: #4fbcff;
                margin-bottom: 8px;
            }
            .comment-body {
                line-height: 1.5;
            }
            .reply {
                margin-left: 20px;
                padding: 10px;
                border-left: 2px solid var(--accent-color);
                background: #3a3a3a;
                border-radius: 4px;
            }
            .reply-author {
                font-weight: bold;
                color: #4fbcff;
                margin-bottom: 5px;
            }
            .reply-body {
                line-height: 1.4;
            }
            .update-time {
                text-align: center;
                color: #808080;
                margin-bottom: 30px;
            }
        </style>
    </head>
    <body>
        <h1>Daily Top Reddit Posts from r/chatgpt</h1>
        <p class="update-time">Updated on {{date}} UTC</p>
        {% for post in posts %}
        <div class="post">
            <div class="post-title"><a href="{{post.url}}" target="_blank">{{ post.title }}</a></div>
            <div class="post-author">Posted by u/{{ post.author }}</div>
            {% if post.selftext %}
            <div class="post-content">{{ post.selftext }}</div>
            {% endif %}
            {% if post.media_type == 'image' %}
            <div class="media-container">
                <img src="{{ post.media_url }}" alt="Post image">
            </div>
            {% elif post.media_type == 'video' %}
            <div class="media-container">
                <video controls>
                    <source src="{{ post.media_url }}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
            {% endif %}
            <h3>Top Comments:</h3>
            {% for comment in post.comments %}
            <div class="comment">
                <div class="comment-author">u/{{ comment.author }}</div>
                <div class="comment-body">{{ comment.body }}</div>
                {% for reply in comment.replies %}
                <div class="reply">
                    <div class="reply-author">u/{{ reply.author }}</div>
                    <div class="reply-body">{{ reply.body }}</div>
                </div>
                {% endfor %}
            </div>
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    </html>
    """
    template = Template(template_str)
    html = template.render(posts=posts_info, date=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
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
        selftext = data['selftext'][:500] + '...' if len(data['selftext']) > 500 else data['selftext']
        
        # Handle media content
        media_type = None
        media_url = None
        
        # Handle images
        if data.get('post_hint') == 'image':
            media_type = 'image'
            media_url = data['url']
        # Handle videos
        elif data.get('is_video'):
            media_type = 'video'
            if 'reddit_video' in data['media']:
                media_url = data['media']['reddit_video']['fallback_url']
        
        comments = get_top_comments(token, post_id)
        posts_info.append({
            'title': title,
            'author': author,
            'url': url,
            'selftext': selftext,
            'comments': comments,
            'media_type': media_type,
            'media_url': media_url
        })

    html = generate_html(posts_info)
    # Write to index.html
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    main()
