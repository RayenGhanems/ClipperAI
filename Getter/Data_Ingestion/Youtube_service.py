import requests
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()
YOUTUBE_API_KEY=os.getenv("YOUTUBE_API_KEY")

class YoutubeService:
    BASE_URL="https://www.googleapis.com/youtube/v3"
    def extract_handle(self, channel_url: str):
        parts=channel_url.rstrip("/").split("/")
        return parts[-1]
    

    def get_channel_info(self, channel_url: str):
        handle=self.extract_handle(channel_url)

        response=requests.get(f"{self.BASE_URL}/channels",
                               params={ "part": "snippet,statistics,contentDetails",
                                        "forHandle": handle, "key": YOUTUBE_API_KEY, }, 
                                        timeout=20, )
        
        response.raise_for_status()
        data=response.json()

        if not data.get("items"): 
            raise ValueError("Chaîne YouTube introuvable") 
        
        item = data["items"][0] 

        return { "channel_id": item["id"],
                 "channel_name": item["snippet"]["title"], 
                 "channel_url": channel_url, 
                 "youtube_video_count": int(item["statistics"].get("videoCount", 0)),
                 "uploads_playlist_id": item["contentDetails"]["relatedPlaylists"]["uploads"], }
    
    def get_channel_videos(self, uploads_playlist_id: str, max_pages: int = 5): 
        videos = [] 
        next_page_token = None 
        page = 0 
        while page < max_pages: 
            response = requests.get( f"{self.BASE_URL}/playlistItems",
                                     params={ "part": "snippet,contentDetails",
                                              "playlistId": uploads_playlist_id,
                                                "maxResults": 50,
                                                  "pageToken": next_page_token,
                                                    "key": YOUTUBE_API_KEY, }, timeout=20, )
            response.raise_for_status()
            data = response.json()
            for item in data.get("items", []): 
                snippet = item["snippet"] 
                video_id = snippet["resourceId"]["videoId"] 
                videos.append({ "youtube_video_id": video_id,
                                "title": snippet.get("title"),
                                   "published_at": snippet.get("publishedAt"),
                                     "youtube_url": f"https://www.youtube.com/watch?v={video_id}", })

            next_page_token = data.get("nextPageToken") 
            page += 1 

            if not next_page_token: 
                break 

        return videos 
            

