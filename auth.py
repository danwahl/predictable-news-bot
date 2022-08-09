from dotenv import load_dotenv
import os
import tweepy


def auth():
    load_dotenv()

    # https://docs.tweepy.org/en/v4.10.0/authentication.html#pin-based-oauth
    oauth1_user_handler = tweepy.OAuth1UserHandler(
        consumer_key=os.getenv("CONSUMER_KEY"),
        consumer_secret=os.getenv("CONSUMER_SECRET"),
        callback="oob"
    )

    print(oauth1_user_handler.get_authorization_url())

    verifier = input("Input PIN: ")
    access_token, access_token_secret = oauth1_user_handler.get_access_token(
        verifier)

    print("Add the following to your .env file:")
    print(f"ACCESS_TOKEN={access_token}")
    print(f"ACCESS_TOKEN_SECRET={access_token_secret}")


if __name__ == "__main__":
    auth()
