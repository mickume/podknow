## Product requiremnet

A command-line tool that downloads podcast episodes from RSS feeds and transcribes them using Whisper, optimized for Apple Silicon. Use Claud AI and its API for further processing and analysis of the transcribed podcast episode.

PodKnow takes a podcast RSS feed URL and:
1. Downloads the audio/video file for an episode
2. Transcribes it using **MLX-Whisper** (optimized for Apple M-series chips)
3. Creates a markdown file with episode metadata and full transcription

In order to discover podcasts, and their RSS-feed URL
- use the public iTunes and Spotify API endpoints to search for podcasts, by title, name of the author or any keywords in the description etc.
- once podcast are found, list them and their feed UTL for further commands.

Given a podcast RSS-feed URL, list the last n episodes and their episode number or identifier. This identifier will later be used to specify which episode to anlyse.

With a dedicated command, download the media file and transcribe the content. By default, detect and verify the language is English before transcribing (this can be skipped with a flag if needed). Detect paragraphs in the transcription by using Whisper's built-in function for this. Create a markdown file with metadata as frontmatter and the transcribed text.

Use Claude API to analyse the transcription in ordert to
- create a summary of the transcription
- create a list of topics covered, in one sentence
- create a list of relevant keywords to label the transcription
- try to detect "sponsor conten", i.e. narrated adds and mark them in the transciption

PodKnow is implemented with python 3.13. 
Create a virtual env for all python modules need.
The resulting tool and all its dependencies must be installed using pip or uv.
All the metadata used to direct the LLM and the API calls to Claude should be in a local markdown file that can be edited without changing the implementation.

---
Now anlyse this PRD and create a requirements, design and list of tasks. Ask questions if aspects of the PRD or for the requirements are not clear or nor specific enough.