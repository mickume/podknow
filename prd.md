
A command-line tool that downloads podcast episodes from RSS feeds and transcribes them using Whisper, optimized for Apple Silicon.

PodKnow takes a podcast RSS feed URL and:
1. Downloads the audio/video file for an episode
2. Transcribes it using **MLX-Whisper** (optimized for Apple M-series chips)
3. Creates a markdown file with episode metadata and full transcription

PodKnow is implemented with python 3.13

It should use a podcast directory like Apple's or Spotify's to search for a particular podcast feed RSS, either using the title, autor or any other keyword in the search.
Once one/many podcasts are found, the tool will subscribe to them i.e. keep a local file with podasts and their feed URLs to check for new episodes regularly. This is similar to what a "podcatcher" app would do, onyl locally and without any backand service and on the command line.
For a found podcast, download the media file and transcibe the content, if the language is "english" only.

Create two markdown files for the podcast episode:
- one with the episode metadata as frontmatter and the original transcription  
- a markdown file with a version of the transcription that has: a summary of the episode, a list of the topics covered in the episode as a one-sentence and a list of relevant keywords

Use Claude API for the analysis but also implement the option to have a local LLM, e.g. with Ollama.

All the metadata used to direct the LLM should be in a local markdown file that can be edited without changing the implementation.

