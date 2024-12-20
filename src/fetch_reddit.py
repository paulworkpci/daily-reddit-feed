import os
import requests
import datetime
from jinja2 import Template

# Reddit API Configuration
CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')
USERNAME = os.environ.get('REDDIT_USERNAME')
PASSWORD = os.environ.get('REDDIT_PASSWORD')
USER_AGENT = "DailyFeedScript/1.0"

# Subreddit Configuration
SUBREDDITS = {
    'singularity': 20,  # subreddit name: number of posts
    'ufos': 10,
    'joerogan': 10,
    # Add more subreddits and their post limits here
}

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
    res.raise_for_status()  # Added for error handling
    token = res.json()['access_token']
    return token

def get_top_posts(token, subreddit='chatgpt', limit=20):
    headers = {'Authorization': f'bearer {token}', 'User-Agent': USER_AGENT}
    url = f'https://oauth.reddit.com/r/{subreddit}/top?t=day&limit={limit}'
    res = requests.get(url, headers=headers)
    res.raise_for_status()  # Added for error handling
    posts = res.json()['data']['children']
    return posts

def get_top_comments(token, subreddit, post_id, limit=3):
    headers = {
        'Authorization': f'bearer {token}',
        'User-Agent': USER_AGENT
    }
    url = f'https://oauth.reddit.com/r/{subreddit}/comments/{post_id}?sort=top'
    res = requests.get(url, headers=headers)
    res.raise_for_status()  # Added for error handling
    comment_data = res.json()

    # comment_data typically looks like: [ {post info}, {comment tree} ]
    if (isinstance(comment_data, list) and len(comment_data) > 1 
        and 'data' in comment_data[1] 
        and 'children' in comment_data[1]['data']):
        
        all_children = comment_data[1]['data']['children']
        
        top_comments = []
        for c in all_children:
            if c['kind'] == 't1':  # Ensure it's a comment
                comment_author = c['data'].get('author')
                comment_body = c['data'].get('body', '')

                # Process replies if they exist
                replies_data = c['data'].get('replies')
                replies = []
                if isinstance(replies_data, dict):
                    reply_children = replies_data['data'].get('children', [])
                    for reply in reply_children[:3]:  # Limit replies to 3
                        if reply['kind'] == 't1':
                            replies.append({
                                'author': reply['data'].get('author'),
                                'body': reply['data'].get('body', '')
                            })

                top_comments.append({
                    'author': comment_author,
                    'body': comment_body,
                    'replies': replies
                })

                if len(top_comments) == limit:  # Limit top-level comments to 3
                    break

        return top_comments
    else:
        return []

def generate_html(all_posts_info):
    template_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Daily Reddit Feed</title>
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
            .update-time {
                text-align: center;
                color: #808080;
                margin-bottom: 30px;
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
                margin-bottom: 5px;
            }
            .post-title a {
                color: var(--secondary-color);
                text-decoration: none;
            }
            .post-title a:hover {
                color: var(--accent-color);
            }
            .post-stats {
                font-size: 0.9em;
                color: #b3b3b3;
                margin-bottom: 15px;
            }
            .post-author {
                color: #4fbcff;
                font-size: 0.9em;
                margin-bottom: 15px;
            }
            .post-content {
                margin: 15px 0;
                line-height: 1.6;
            }
            .media-container {
                max-width: 100%;
                margin: 15px 0;
            }
            .media-container img, .media-container video {
                max-width: 100%;
                border-radius: 4px;
            }
            .comment-section-title {
                font-size: 1.2em;
                margin-top: 30px;
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 5px;
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
                margin-top: 10px;
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
            /* Add new style for subreddit section */
            .subreddit-section {
                margin-bottom: 60px;
            }
            .subreddit-title {
                font-size: 2em;
                color: var(--accent-color);
                margin: 40px 0 20px 0;
                text-align: center;
                border-bottom: 2px solid var(--border-color);
                padding-bottom: 10px;
            }
        </style>
        <!-- Include dash.js and hls.js libraries -->
        <script src="https://cdn.dashjs.org/latest/dash.all.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    </head>
    <body>
        <h1>Daily Top Reddit Posts</h1>
        <p class="update-time">Updated on {{date}} UTC</p>
        {% for subreddit, posts in all_posts.items() %}
        <div class="subreddit-section">
            <h2 class="subreddit-title">r/{{subreddit}}</h2>
            {% for post in posts %}
            <div class="post">
                <div class="post-title"><a href="{{post.url}}" target="_blank">{{ post.title }}</a></div>
                <div class="post-stats">↑ {{ post.ups }} | {{ post.num_comments }} comments</div>
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
                    <video id="video{{ post.post_id }}" controls></video>
                </div>
                <script>
                    document.addEventListener("DOMContentLoaded", function() {
                        var dashUrl = "{{ post.dash_url }}";
                        var hlsUrl = "{{ post.hls_url }}";
                        var fallbackUrl = "{{ post.media_url }}";
                        var videoElement = document.querySelector("#video{{ post.post_id }}");

                        if (dashUrl) {
                            // Use dash.js if DASH manifest is available
                            var player = dashjs.MediaPlayer().create();
                            player.initialize(videoElement, dashUrl, true);
                        } else if (hlsUrl) {
                            // Use hls.js if HLS url is available
                            if (Hls.isSupported()) {
                                var hls = new Hls();
                                hls.loadSource(hlsUrl);
                                hls.attachMedia(videoElement);
                            } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
                                // Some browsers (Safari) may support HLS natively
                                videoElement.src = hlsUrl;
                            } else {
                                // fallback no audio scenario
                                videoElement.src = fallbackUrl;
                            }
                        } else {
                            // fallback no audio scenario
                            videoElement.src = fallbackUrl;
                        }
                    });
                </script>
                {% endif %}
                
                {% if post.comments %}
                <h3 class="comment-section-title">Top Comments:</h3>
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
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    </html>
    """
    template = Template(template_str)
    html = template.render(
        all_posts=all_posts_info,
        date=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    )
    return html

def main():
    try:
        token = get_token()
    except requests.exceptions.RequestException as e:
        print(f"Error obtaining token: {e}")
        return

    all_posts_info = {}
    
    for subreddit, post_limit in SUBREDDITS.items():
        try:
            posts = get_top_posts(token, subreddit=subreddit, limit=post_limit)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching posts from r/{subreddit}: {e}")
            continue

        posts_info = []
        
        for p in posts:
            data = p['data']
            post_id = data['id']
            title = data['title']
            author = data['author']
            ups = data.get('ups', 0)
            num_comments = data.get('num_comments', 0)
            url = f"https://www.reddit.com{data['permalink']}"
            # Truncate selftext if too long
            selftext = data['selftext'][:500] + '...' if len(data['selftext']) > 500 else data['selftext']
            
            # Handle media content
            media_type = None
            media_url = None
            dash_url = None
            hls_url = None
            
            # Handle images
            if data.get('post_hint') == 'image':
                media_type = 'image'
                media_url = data['url']
            # Handle videos
            elif data.get('is_video'):
                media_type = 'video'
                reddit_video = data.get('media', {}).get('reddit_video', {})
                dash_url = reddit_video.get('dash_url')
                hls_url = reddit_video.get('hls_url')
                # fallback_url is usually video only, no audio
                fallback_url = reddit_video.get('fallback_url')

                # If no DASH or HLS, fallback to fallback_url
                # This won't have audio, but at least shows the video.
                media_url = dash_url or hls_url or fallback_url

            comments = get_top_comments(token, subreddit, post_id)
            posts_info.append({
                'post_id': post_id,  # Added post_id for unique identification
                'title': title,
                'author': author,
                'url': url,
                'selftext': selftext,
                'comments': comments,
                'media_type': media_type,
                'media_url': media_url,
                'dash_url': dash_url,
                'hls_url': hls_url,
                'ups': ups,
                'num_comments': num_comments
            })
        
        all_posts_info[subreddit] = posts_info

    html = generate_html(all_posts_info)
    os.makedirs("docs", exist_ok=True)  # Ensure the 'docs' directory exists
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML file generated successfully at 'docs/index.html'.")

if __name__ == "__main__":
    main()
