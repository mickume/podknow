README

Create a python 3.12 command line utility that does the following:
- it receives an URL to a podcast RSS feed as input
- retrieve the podcast RSS feed and extract the data for the latest, newest podcast episode
- create a markdown file in a predefined location with the podcast episode meta data as content, especially: the title, any description, chapter marks
- if there are links mentioned in the metadata, create a list of these links
- next, find the url to the podcast media file, either in mp3 or mp4 format.
- download the podcat media file to a temporary location
- feed the podcast media file to a LLM for transcription. Assume that there is a local Ollama API available.
- append the podcast transcription to the markdown file

---
```shell
# Install dependencies
pip install -r requirements.txt

# Run the utility
python podknow.py <rss_feed_url> [-o output_directory]

# Example
python podknow.py "https://rss.art19.com/tim-ferriss-show" -o ./output
```

https://rss.art19.com/tim-ferriss-show