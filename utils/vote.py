import random

def vote_post(post):
    try:
        vote_action = random.choice(['up', 'down', 'none'])
        if vote_action == 'up':
            post.upvote()
            print(f"Upvoted post.")
        elif vote_action == 'down':
            post.downvote()  
            print(f"Downvoted post.")
        else:
            print(f"No vote cast for post.")

    except Exception as e:
        print(f"Error voting on post: {e}")

def vote_comment(comment):
    try:
        vote_action = random.choice(['up', 'down', 'none'])
        if vote_action == 'up':
            comment.upvote()  
            print(f"Upvoted comment.")
        elif vote_action == 'down':
            comment.downvote() 
            print(f"Downvoted comment.")
        else:
            print(f"No vote cast for comment.")
    except Exception as e:
        print(f"Error voting on comment: {e}")