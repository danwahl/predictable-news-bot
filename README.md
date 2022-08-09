# predictable-news-bot

A bot that tweets daily updates about questions on [Metaforecast](https://metaforecast.org/), inspired by [Astral Codex Ten](https://astralcodexten.substack.com/p/mantic-monday-31422).

See also:

- [MetaculusAlert](https://twitter.com/MetaculusAlert)
- [PredictionDiffs](https://predictiondiffs.com/)


## Python setup

1. Create a new Python 3.8 virtual environment (optionally using [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/install.html))
2. Activate the environment
3. Install the required packages

```
$ mkvirtualenv --python python3.8 predictable-news-bot

...

$ workon predictable-news-bot
(predictable-news-bot) $ pip install -r requirements.txt
```

## Twitter authentication

1. Sign up for a [developer account](https://developer.twitter.com/en/support/twitter-api/developer-account) on Twitter using your "regular" account (e.g. [fakedrwahl](https://twitter.com/fakedrwahl))
2. Apply for "Elevated access" (which is required to access parts of the [v2 API functionality](https://developer.twitter.com/en/support/twitter-api/v2))
3. In the [Developer Portal](https://developer.twitter.com/en/portal/dashboard), create a new Project (e.g. "Predictable News") and corresponding App (e.g. "predictable-news-bot")
4. Copy the API Key and Secret to a local .env file under `CONSUMER_KEY` and `CONSUMER_SECRET` (don't commit this file to GitHub!)
5. Under "User authentication settings," enable OAuth 1.0a with "Read and write" permissions (Callback and Website URLs are required but not used, so just enter e.g. [http://predictable.news](http://predictable.news))
6. Log into Twitter under the "tweeting" account (e.g. [PredictableNews](https://twitter.com/PredictableNews))
7. Activate the Python virtual environment created above
8. Run auth.py script, open the authorization url, input the provided pin, and copy the resulting `ACCESS_TOKEN` and `ACCESS_TOKEN_SECRET` to the .env file from step 4

```
$ workon predictable-news-bot
(predictable-news-bot) $ python auth.py
https://api.twitter.com/oauth/authorize?oauth_token=...

...

Input PIN: 1234567
Add the following to your .env file:
ACCESS_TOKEN=...
ACCESS_TOKEN_SECRET=...
```


## Main usage

Follow the Twitter authentication steps above to create a local .env file. Then the main.py script can then be run as follows:

```
$ workon predictable-news-bot
(predictable-news-bot) $ python main.py --help
usage: main.py [-h] [-c CHANGE] [-d] [-t]

optional arguments:
  -h, --help            show this help message and exit
  -c CHANGE, --change CHANGE
                        probability change threshold for tweeting (default: 0.05)
  -d, --debug           enable debug logging (default: False)
  -t, --tweet           actually send tweets (default: False)
```

## Deploy on GitHub

Add the secrets from your local .env file (`CONSUMER_KEY`, `CONSUMER_SECRET`, `ACCESS_TOKEN`, and `ACCESS_TOKEN_SECRET`) to your repository on GitHub as described [here](https://docs.github.com/en/actions/security-guides/encrypted-secrets).

Optionally, adjust the .github/workflows/main.yml file schedule to run at the desired time.
