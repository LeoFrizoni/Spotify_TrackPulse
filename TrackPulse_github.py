import spotipy
from spotipy.oauth2 import SpotifyOAuth
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox
import threading
import concurrent.futures

# Authentication with Spotify API
def authenticate_spotify(client_id, client_secret, redirect_uri):
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                                       client_secret=client_secret,
                                                       redirect_uri=redirect_uri,
                                                       scope="user-library-read"))
        return sp
    except spotipy.SpotifyException as e:
        print(f"Error during Spotify authentication: {e}")
        return None

# Get artist ID from Spotify
def get_artist_id(sp, artist_name):
    try:
        results = sp.search(q=artist_name, type='artist')
        items = results['artists']['items']
        if len(items) > 0:
            return items[0]['id']
        else:
            return None
    except Exception as e:
        print(f"Error fetching artist ID: {e}")
        return None

# Get top 5 tracks from artist
def get_top_tracks(sp, artist_id):
    top_tracks = sp.artist_top_tracks(artist_id)
    tracks = top_tracks['tracks'][:5]
    return tracks

# Get tracks from an album
def get_album_tracks(sp, album_id):
    tracks = sp.album_tracks(album_id)['items']
    track_info = [sp.track(track['id']) for track in tracks]
    return track_info

# Get all tracks from the artist's albums
def get_all_tracks(sp, artist_id):
    albums = sp.artist_albums(artist_id, album_type='album')['items']
    all_tracks = []
    # Limit to the latest 5 albums for performance reasons
    albums = albums[:5]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_album_tracks, sp, album['id']) for album in albums]
        for future in concurrent.futures.as_completed(futures):
            all_tracks.extend(future.result())
    return all_tracks

# Analyze track popularity
def analyze_tracks(tracks):
    popularity = [track['popularity'] for track in tracks]
    avg_popularity = np.mean(popularity)
    least_popular_track = min(tracks, key=lambda x: x['popularity'])
    return avg_popularity, least_popular_track

# Plot artist data
def plot_artist_data(top_tracks, avg_popularity, least_popular_track):
    track_names = [track['name'][:20] + '...' if len(track['name']) > 20 else track['name'] for track in top_tracks] + ['Average Popularity', least_popular_track['name']]
    popularity = [track['popularity'] for track in top_tracks] + [avg_popularity, least_popular_track['popularity']]

    plt.figure(figsize=(12, max(6, len(track_names) * 0.5)))  # Adjust the figure size dynamically
    plt.barh(track_names, popularity, color='#1DB954')

    plt.xlabel('Popularity', color='black')
    plt.ylabel('Tracks', color='black')
    plt.title('Artist Analysis on Spotify', color='black')
    plt.gca().invert_yaxis()
    plt.gca().set_facecolor('white')
    plt.gca().tick_params(colors='black')
    plt.grid(True, color='black', linestyle='--', linewidth=0.5, axis='x')
    plt.xticks(color='black')
    plt.yticks(color='black')
    plt.xlim(0, max(popularity) * 1.1)  

    manager = plt.get_current_fig_manager()
    manager.window.state('zoomed')

    plt.show()

# Custom pop-up window function
open_popups = []

def custom_window(title, message, window_type='info'):
    custom_window = tk.Toplevel()
    custom_window.title(title)
    custom_window.configure(bg='#191414')
    custom_window.geometry("1000x700")  # Increase window size
    
    label = tk.Label(custom_window, text=message, fg='#1DB954', bg='#191414', font=('Helvetica', 16), wraplength=580, justify='center') 
    label.pack(pady=20, padx=20)
    
    button = tk.Button(custom_window, text="OK", command=custom_window.destroy, fg='black', bg='#1DB954', activebackground='#1ED760', font=('Helvetica', 14), width=10)  
    button.pack(pady=10)
    
    custom_window.transient()
    custom_window.grab_set()
    custom_window.wait_window()

    open_popups.append(custom_window)

# Function to save statistics to file
def save_statistics_to_file(data, file_name="artist_stats.csv"):
    import csv
    with open(file_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Track", "Popularity"])
        for track in data:
            writer.writerow([track['name'], track['popularity']])

# Main interface connection
def main():
    client_id = 'YOURID' #You have to access the spotify API and make a request to them to be able to use
    client_secret = 'YOURSECRET'
    redirect_uri = 'http://localhost:8888/callback'
    
    sp = authenticate_spotify(client_id, client_secret, redirect_uri)
    
    root = tk.Tk()
    root.title("Spotify Artist Information")
    root.configure(bg='black')
    root.geometry("800x600")
    
    def make_button_circular(widget):
        widget.config(relief=tk.FLAT, bd=0)
        widget.bind("<Enter>", lambda e: widget.config(bg='#1ED760'))
        widget.bind("<Leave>", lambda e: widget.config(bg='#1DB954'))
    
    def get_artist_info():
        artist_name = entry.get().strip()
        
        if not artist_name:
            custom_window("Input Error", "Please enter a valid artist name.", 'warning')
            return

        if len(artist_name) < 2:
            custom_window("Input Error", "Artist name must have at least 2 characters.", 'warning')
            return

        artist_id = get_artist_id(sp, artist_name)
        
        if artist_id:
            global top_tracks  # Make top_tracks accessible globally
            top_tracks = get_top_tracks(sp, artist_id)
            
            def fetch_and_display_data():
                all_tracks = get_all_tracks(sp, artist_id)
                
                avg_popularity, least_popular_track = analyze_tracks(all_tracks)
                
                top_tracks_info = "\n".join([f"{track['name'][:20]}... - Popularity: {track['popularity']}" if len(track['name']) > 20 else f"{track['name']} - Popularity: {track['popularity']}" for track in top_tracks])
                
                custom_window("Top 5 Most Popular", top_tracks_info)
                custom_window("Statistics", f"Average Popularity: {avg_popularity}\nLeast Played: {least_popular_track['name']} - Popularity: {least_popular_track['popularity']}")
                
                plot_artist_data(top_tracks, avg_popularity, least_popular_track)

            threading.Thread(target=fetch_and_display_data).start()
        else:
            custom_window("Error", "Artist not found.", 'error')

    def clear():
        entry.delete(0, tk.END)
    
    # Widgets
    label = tk.Label(root, text="Enter the artist's name:", fg='#1DB954', bg='black', font=('Helvetica', 16))
    label.pack(pady=20)

    entry = tk.Entry(root, width=50, fg='black', bg='#1DB954', font=('Helvetica', 14))
    entry.pack(pady=20)

    button_frame = tk.Frame(root, bg='black')
    button_frame.pack(pady=20)

    search_button = tk.Button(button_frame, text="Search", command=get_artist_info, fg='black', bg='#1DB954', activebackground='#1ED760', width=20, height=2)
    make_button_circular(search_button)
    search_button.pack(side=tk.LEFT, padx=10)

    clear_button = tk.Button(button_frame, text="Clear", command=clear, fg='black', bg='#1DB954', activebackground='#1ED760', width=20, height=2)
    make_button_circular(clear_button)
    clear_button.pack(side=tk.RIGHT, padx=10)

    # Export data button
    export_button = tk.Button(root, text="Export Data", command=lambda: save_statistics_to_file(top_tracks), fg='black', bg='#1DB954', width=20, height=2)
    export_button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
