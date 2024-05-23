import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import functools

# Set up your Spotify credentials
SPOTIPY_CLIENT_ID = '4b4d7267b1bf47adae77bf7c4debd80a'
SPOTIPY_CLIENT_SECRET = 'a86c2b9b22604d0c9a10b05e4f04e493'
SPOTIPY_REDIRECT_URI = 'http://localhost:8888/callback'

# Set up the scope
scope = 'user-read-playback-state user-modify-playback-state streaming'

# Create a Spotify object with retry and increased timeout
def create_spotify_client():
    auth_manager = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                client_secret=SPOTIPY_CLIENT_SECRET,
                                redirect_uri=SPOTIPY_REDIRECT_URI,
                                scope=scope)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # Set up retries with exponential backoff
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = sp._session
    http.mount("https://", adapter)
    http.mount("http://", adapter)
    
    # Increase timeout
    sp._session.request = functools.partial(sp._session.request, timeout=10)
    
    return sp

def get_main_part_end_time(track_id, sp):
    # Get the audio analysis for the track
    analysis = sp.audio_analysis(track_id)
    
    # Find the end time of the main part of the song
    main_part_end_time = 0
    for section in analysis['sections']:
        # Customize this condition to identify the main part of the song
        if section['loudness'] > -5:  # Example condition: sections with loudness > -5 dB
            print(section['loudness'])
            main_part_end_time = max(main_part_end_time, section['start'] + section['duration'])
    
    return main_part_end_time

def play_playlist(sp, playlist_id):
    # Get playlist tracks
    results = sp.playlist_tracks(playlist_id)
    track_uris = [track['track']['uri'] for track in results['items']]
    
    # Start playing the playlist
    sp.start_playback(uris=track_uris)

def skip_after_main_part(sp, playlist_id):
    play_playlist(sp, playlist_id)
    while True:
        try:
            # Get the current playback state
            playback = sp.current_playback()
            
            if playback and playback['is_playing']:
                current_track = playback['item']
                track_id = current_track['id']
                progress_ms = playback['progress_ms'] / 1000  # Convert to seconds
                print(progress_ms)

                # Get the end time of the main part of the current track
                main_part_end_time = 5#get_main_part_end_time(track_id, sp)
                
                # If the current progress is beyond the main part, skip to the next track
                if progress_ms >= main_part_end_time:
                    sp.next_track()
            
            # Sleep for a while before checking again
            time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            time.sleep(5)

if __name__ == '__main__':
    playlist_id = '5WOcImcyK6Tu00pjWotejX'  # Replace with your playlist ID
    sp = create_spotify_client()
    skip_after_main_part(sp, playlist_id)
