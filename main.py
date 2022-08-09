from time import sleep
from datetime import datetime, timedelta
from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.requests import log, RequestsHTTPTransport
import argparse
import logging
import os
import pandas as pd
import sys
import tweepy

# Default probability change threshold, above which a tweet is sent
CHANGE_THRESHOLD = 0.05

# GraphQL query to get the history of all 4+ star rated questions (using " " as pseudo-wildcard)
SEARCH_QUERY = gql("""
{
  searchQuestions(input: {query: " ", starsThreshold: 4, limit: 1000}) {
    history {
      fetched
      options {
        name
        probability
      }
    }
    id
    title
  }
}
""")

# Maximum tweet length in characters
TWEET_LENGTH = 280


def get_gql_client():
    try:
        # Set GraphQL logging level (defaults to INFO otherwise)
        log.setLevel(logging.WARNING)

        # Create GraphQL transport using requests
        # https://gql.readthedocs.io/en/v3.4.0/transports/requests.html
        transport = RequestsHTTPTransport(
            url="https://metaforecast.org/api/graphql")

        # Create GraphQL client
        return Client(transport=transport,
                      fetch_schema_from_transport=True)
    except Exception as e:
        logging.error(f"Failed to create GraphQL client: {e}")
        return None


def get_tweepy_client():
    try:
        # Load environment variables from .env file
        load_dotenv()

        # Create Twitter client
        # https://docs.tweepy.org/en/v4.10.0/authentication.html#id3
        return tweepy.Client(
            consumer_key=os.getenv("CONSUMER_KEY"),
            consumer_secret=os.getenv("CONSUMER_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
        )
    except Exception as e:
        logging.error(f"Failed to create Twitter client: {e}")
        return None


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--change", type=int, default=CHANGE_THRESHOLD,
                        help="probability change threshold for tweeting")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="enable debug logging")
    parser.add_argument("-t", "--tweet", action="store_true",
                        help="actually send tweets")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    logging.debug(f"Args: {args}")

    tweepy_client = get_tweepy_client()
    if tweepy_client is None:
        sys.exit(1)

    try:
        # Log Twitter username
        me = tweepy_client.get_me()
        username = me.data["username"]
        logging.debug(f"Logged in as {username}")
    except Exception as e:
        logging.error(f"Failed to get username: {e}")
        sys.exit(1)

    gql_client = get_gql_client()
    if gql_client is None:
        sys.exit(1)

    try:
        # Execute GraphQL search query
        result = gql_client.execute(SEARCH_QUERY)
    except:
        logging.error("Failed to execute query")
        sys.exit(1)

    # Script expects to runs daily, so ignore data from before this datetime
    last_run = datetime.now() - timedelta(days=1)

    # Iterate through all questions
    for i in range(len(result["searchQuestions"])):
        question = result["searchQuestions"][i]

        # Get each probability history for all option for this question
        df = pd.json_normalize(question["history"],
                               record_path=["options"], meta="fetched")
        # >>> df.tail()
        #                name  probability         fetched
        # 58   38.0% to 38.2%     0.009615  1659699931.871
        # 59   38.3% to 38.5%     0.009615  1659699931.871
        # 60   38.6% to 38.8%     0.009615  1659699931.871
        # 61   38.9% to 39.1%     0.038462  1659699931.871
        # 62  39.2% or higher     0.894231  1659699931.871

        # Pivot around fetched timestamp (index) and options (columns)
        history = df.pivot_table(index="fetched", columns="name",
                                 values="probability")
        # Convert index from fetched timestamp to datetime
        history.index = pd.to_datetime(history.index, unit="s")
        # >>> history.tail()
        # name                           37.0% or lower  37.1% to 37.3%  37.4% to 37.6%  37.7% to 37.9%  38.0% to 38.2%  38.3% to 38.5%  38.6% to 38.8%  38.9% to 39.1%  39.2% or higher
        # fetched
        # 2022-08-01 11:46:30.795000064        0.008850        0.017699        0.026549        0.044248        0.070796        0.088496        0.150442        0.212389         0.380531
        # 2022-08-02 11:47:00.298000128        0.009091        0.009091        0.009091        0.009091        0.045455        0.063636        0.136364        0.236364         0.481818
        # 2022-08-03 11:45:38.891000064        0.009009        0.009009        0.009009        0.009009        0.018018        0.063063        0.027027        0.180180         0.675676
        # 2022-08-04 11:46:48.255000064        0.009009        0.009009        0.009009        0.009009        0.009009        0.009009        0.090090        0.306306         0.549550
        # 2022-08-05 11:45:31.871000064        0.009615        0.009615        0.009615        0.009615        0.009615        0.009615        0.009615        0.038462         0.894231

        # Make sure we have at least two rows so we can calculate the difference
        if history.shape[0] < 2:
            logging.warning(
                f"Skipping question {question['id']} because it has only {history.shape[0]} row(s)")
            continue
        # Ignore this question if the most recent datetime is too old
        elif history.index[-1] < last_run:
            logging.debug(
                f"Skipping {question['id']} because {history.index[-1]} is before {last_run}")
            continue

        # Calculate the difference for each option between the most recent rows
        # TODO(drw): this assumes that rows are separated by ~one day, which may not be true
        options = pd.concat(
            [history.iloc[-1], history.diff().iloc[-1]], axis=1)
        options.columns = ["probability", "diff"]
        # Sort by overall probability so that, if we have trim the tweet, we show the most likely options first
        options.sort_values("probability", ascending=False, inplace=True)
        # >>> options.head()
        #                  probability      diff
        # name
        # 39.2% or higher     0.894231  0.344681
        # 38.9% to 39.1%      0.038462 -0.267845
        # 37.0% or lower      0.009615  0.000606
        # 37.1% to 37.3%      0.009615  0.000606
        # 37.4% to 37.6%      0.009615  0.000606

        # Get the option names that are gte the change threshold, if any
        names = options.index[options["diff"].abs() >= args.change].values
        # Skip questions with no options above the threshold
        if len(names) == 0:
            logging.debug(
                f"Skipping {question['id']} because no options are above change threshold")
            continue

        # Compose the tweet text
        text = f"{question['title']}"
        for name in names:
            text += f"\n- {name}: {100.0*options.loc[name, 'probability']:.1f}%"
            sign = "+" if options.loc[name, "diff"] > 0 else ""
            text += f" ({sign}{100.0*options.loc[name, 'diff']:.1f}%)"

        # Generate Metaforecast url (would use market url directly, but some are long)
        url = f"\nhttps://metaforecast.org/questions/{question['id']}"

        # Append url to tweet text, trimming as needed so that it fits
        if len(text) > (TWEET_LENGTH - len(url)):
            text = f"{text[:(TWEET_LENGTH - len(url) - 1)]}…"
        text += url
        # >>> text
        # What will Joe Biden's RCP job approval rating be on Aug. 5?
        # - 39.2% or higher: 89.4% (+34.5%)
        # - 38.9% to 39.1%: 3.8% (-26.8%)
        # - 38.6% to 38.8%: 1.0% (-8.0%)
        # https://metaforecast.org/questions/predictit-8053

        # Send the tweet
        if args.tweet:
            try:
                logging.debug(f"Tweeting: {text}")
                tweepy_client.create_tweet(reply_settings="mentionedUsers",
                                           text=text, user_auth=True)
                sleep(1)
            except Exception as e:
                logging.error(f"Failed to tweet: {e}")
                continue
        else:
            logging.info(f"Would tweet: {text}")


if __name__ == "__main__":
    main()
