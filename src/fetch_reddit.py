import os
import random
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
    'singularity': 8,  # subreddit name: number of posts
    'ufos': 2,
    'joerogan': 3,
    'nosurf': 2,
    'chatgpt': 2,
    'productivity': 2,
    'lifeprotips': 1,
    'conspiracy': 2,
    'askreddit': 1
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
                c_data = c['data']
                comment_author = c_data.get('author')
                comment_body = c_data.get('body', '')
                comment_ups = c_data.get('ups', 0)
                
                # Convert UNIX time to human-readable
                comment_created_utc = c_data.get('created_utc', None)
                if comment_created_utc:
                    comment_date_str = datetime.datetime.utcfromtimestamp(comment_created_utc).strftime("%Y-%m-%d %H:%M")
                else:
                    comment_date_str = "N/A"

                # Process replies if they exist
                replies_data = c_data.get('replies')
                replies = []
                if isinstance(replies_data, dict):
                    reply_children = replies_data['data'].get('children', [])
                    for reply in reply_children[:3]:  # Limit replies to 3
                        if reply['kind'] == 't1':
                            r_data = reply['data']
                            reply_author = r_data.get('author')
                            reply_body = r_data.get('body', '')
                            reply_ups = r_data.get('ups', 0)

                            reply_created_utc = r_data.get('created_utc', None)
                            if reply_created_utc:
                                reply_date_str = datetime.datetime.utcfromtimestamp(reply_created_utc).strftime("%Y-%m-%d %H:%M")
                            else:
                                reply_date_str = "N/A"

                            replies.append({
                                'author': reply_author,
                                'body': reply_body,
                                'ups': reply_ups,
                                'date': reply_date_str
                            })

                top_comments.append({
                    'author': comment_author,
                    'body': comment_body,
                    'ups': comment_ups,
                    'date': comment_date_str,
                    'replies': replies
                })

                if len(top_comments) == limit:  # Limit top-level comments to 3
                    break

        return top_comments
    else:
        return []

def generate_html(posts):
    # Notice this is now a single list (posts), not grouped by subreddit
    template_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Reddit Feed</title>
        <style>
            :root {
                --primary-color: #1a1a1b;
                --secondary-color: #ffffff;
                --accent-color: #ff4500;
                --border-color: #343536;
                --card-bg: #222222;
                --comment-bg: #2d2d2d;
                --reply-bg: #3a3a3a;
            }
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                padding: 1rem;
                background: var(--primary-color);
                color: var(--secondary-color);
                line-height: 1.6;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
            }
            h1 {
                text-align: center;
                color: var(--accent-color);
                font-size: clamp(1.5rem, 5vw, 2.5rem);
                margin: 1rem 0;
            }
            .update-time {
                text-align: center;
                color: #808080;
                margin-bottom: 2rem;
                font-size: 0.9rem;
            }
            .post {
                margin-bottom: 2rem;
                padding: 1.25rem;
                border: 1px solid var(--border-color);
                border-radius: 12px;
                background: var(--card-bg);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .subreddit-name {
                color: var(--accent-color);
                font-weight: 600;
                margin-bottom: 0.5rem;
                font-size: 0.9rem;
            }
            .post-title {
                font-size: clamp(1.1rem, 4vw, 1.4rem);
                font-weight: bold;
                margin-bottom: 0.75rem;
            }
            .post-title a {
                color: var(--secondary-color);
                text-decoration: none;
            }
            .post-title a:hover {
                color: var(--accent-color);
            }
            .post-meta {
                display: flex;
                flex-wrap: wrap;
                gap: 1rem;
                margin-bottom: 1rem;
                font-size: 0.9rem;
            }
            .post-stats, .post-author, .post-date {
                color: #b3b3b3;
            }
            .post-content {
                margin: 1rem 0;
                font-size: 0.95rem;
            }
            .media-container {
                margin: 1rem 0;
                border-radius: 8px;
                overflow: hidden;
            }
            .media-container img, .media-container video {
                width: 100%;
                height: auto;
                display: block;
            }
            .comment-section-title {
                font-size: 1.1rem;
                margin: 1.5rem 0 1rem;
                padding-bottom: 0.5rem;
                border-bottom: 1px solid var(--border-color);
            }
            /* Comments and replies */
            .comment {
                margin: 1rem 0;
                padding: 1rem;
                border-left: 3px solid var(--accent-color);
                background: var(--comment-bg);
                border-radius: 0 8px 8px 0;
            }
            .comment-header {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                align-items: baseline;
                margin-bottom: 0.5rem;
            }
            .comment-author, .reply-author {
                color: #4fbcff;
                font-weight: 600;
            }
            .comment-meta, .reply-meta {
                font-size: 0.8rem;
                color: #b3b3b3;
            }
            .reply {
                margin: 0.75rem 0 0 1rem;
                padding: 0.75rem;
                border-left: 2px solid var(--accent-color);
                background: var(--reply-bg);
                border-radius: 4px;
            }
            /* Toggle Buttons */
            .toggle-button {
                background-color: var(--accent-color);
                border: none;
                color: var(--secondary-color);
                font-size: 0.85rem;
                padding: 0.4rem 0.8rem;
                cursor: pointer;
                margin-bottom: 0.75rem;
                border-radius: 4px;
            }
            /* Collapsed class to hide elements by default */
            .collapsed {
                display: none;
            }
            @media (max-width: 600px) {
                body {
                    padding: 0.5rem;
                }
                .post {
                    padding: 1rem;
                    margin-bottom: 1rem;
                }
                .reply {
                    margin-left: 0.5rem;
                }
                .comment {
                    padding: 0.75rem;
                }
            }
        </style>
        <!-- Include dash.js and hls.js libraries -->
        <script src="https://cdn.dashjs.org/latest/dash.all.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    </head>
    <body>
        <div class="container">
            <h1>Daily Top Reddit Posts</h1>
            <p class="update-time">Updated on {{date}} UTC</p>
            
            {% for post in posts %}
            <div class="post">
                <div class="subreddit-name">r/{{ post.subreddit }}</div>
                <div class="post-title"><a href="{{ post.url }}" target="_blank">{{ post.title }}</a></div>
                <div class="post-meta">
                    <span class="post-stats">↑ {{ post.ups }} | {{ post.num_comments }} comments</span>
                    <span class="post-author">u/{{ post.author }}</span>
                    <span class="post-date">{{ post.post_date }}</span>
                </div>
                
                {% if post.selftext %}
                <div class="post-content">{{ post.selftext }}</div>
                {% endif %}
                
                {% if post.media_type == 'image' %}
                <div class="media-container">
                    <img src="{{ post.media_url }}" alt="Post image" loading="lazy">
                </div>
                {% elif post.media_type == 'video' %}
                <div class="media-container">
                    <video id="video{{ post.post_id }}" controls playsinline></video>
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
                            // Use hls.js if Hls url is available
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
                <h3 class="comment-section-title">Top Comments</h3>
                <!-- Button to toggle the entire comment section -->
                <button class="toggle-button toggle-comment-section">Show Comments</button>
                <div class="comments-wrapper collapsed">
                    {% for comment in post.comments %}
                    <div class="comment">
                        <div class="comment-header">
                            <span class="comment-author">u/{{ comment.author }}</span>
                            <span class="comment-meta">↑ {{ comment.ups }} | {{ comment.date }}</span>
                        </div>
                        <div class="comment-body">{{ comment.body }}</div>
                        
                        {% if comment.replies %}
                        <!-- Button to toggle replies for this comment -->
                        <button class="toggle-button toggle-replies">Show Replies</button>
                        <div class="replies collapsed">
                            {% for reply in comment.replies %}
                            <div class="reply">
                                <div class="comment-header">
                                    <span class="reply-author">u/{{ reply.author }}</span>
                                    <span class="reply-meta">↑ {{ reply.ups }} | {{ reply.date }}</span>
                                </div>
                                <div class="reply-body">{{ reply.body }}</div>
                            </div>
                            {% endfor %}
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        <script>
            document.addEventListener("DOMContentLoaded", function() {
                // Toggle entire comment sections
                var commentSectionToggles = document.querySelectorAll(".toggle-comment-section");
                commentSectionToggles.forEach(button => {
                    button.addEventListener("click", function() {
                        var commentSection = button.nextElementSibling;
                        if (commentSection.classList.contains("collapsed")) {
                            commentSection.classList.remove("collapsed");
                            button.textContent = "Hide Comments";
                        } else {
                            commentSection.classList.add("collapsed");
                            button.textContent = "Show Comments";
                        }
                    });
                });

                // Toggle replies within each comment
                var repliesToggles = document.querySelectorAll(".toggle-replies");
                repliesToggles.forEach(button => {
                    button.addEventListener("click", function() {
                        var repliesSection = button.nextElementSibling;
                        if (repliesSection.classList.contains("collapsed")) {
                            repliesSection.classList.remove("collapsed");
                            button.textContent = "Hide Replies";
                        } else {
                            repliesSection.classList.add("collapsed");
                            button.textContent = "Show Replies";
                        }
                    });
                });
            });
        </script>
    </body>
    </html>
    """
    template = Template(template_str)
    html = template.render(
        posts=posts,
        date=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    )
    return html

def main():
    try:
        token = get_token()
    except requests.exceptions.RequestException as e:
        print(f"Error obtaining token: {e}")
        return

    # List to store all posts from all subreddits
    combined_posts = []

    for subreddit, post_limit in SUBREDDITS.items():
        try:
            posts = get_top_posts(token, subreddit=subreddit, limit=post_limit)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching posts from r/{subreddit}: {e}")
            continue

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
            
            # Convert post creation time to human-readable
            created_utc = data.get('created_utc', None)
            if created_utc:
                post_date_str = datetime.datetime.utcfromtimestamp(created_utc).strftime("%Y-%m-%d %H:%M")
            else:
                post_date_str = "N/A"

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
                # fallback_url is usually video-only, no audio
                fallback_url = reddit_video.get('fallback_url')
                # If no DASH or HLS, fallback to fallback_url
                media_url = dash_url or hls_url or fallback_url

            comments = get_top_comments(token, subreddit, post_id)
            
            combined_posts.append({
                'subreddit': subreddit,
                'post_id': post_id,
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
                'num_comments': num_comments,
                'post_date': post_date_str,
            })

    # Shuffle all posts randomly (in-place)
    random.shuffle(combined_posts)

    # Generate HTML from the combined posts
    html = generate_html(combined_posts)

    # Ensure the 'docs' directory exists and write the index.html
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("HTML file generated successfully at 'docs/index.html'.")

if __name__ == "__main__":
    main()
