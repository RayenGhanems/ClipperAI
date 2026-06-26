import requests
import re
import os
from dotenv import load_dotenv
load_dotenv()
YOUTUBE_API_KEY=os.getenv("YOUTUBE_API_KEY")

class YoutubeService:
    BASE_URL="https://www.googleapis.com/youtube/v3"

    def extract_handle(self, channel_url: str):
        parts=channel_url.rstrip("/").split("/")
        return parts[-1]

    def _duration_to_seconds(self, duration: str | None) -> int | None:
        if not duration:
            return None

        pattern = (
            r"^P"
            r"(?:(?P<days>\d+)D)?"
            r"(?:T"
            r"(?:(?P<hours>\d+)H)?"
            r"(?:(?P<minutes>\d+)M)?"
            r"(?:(?P<seconds>\d+)S)?"
            r")?$"
        )
        match = re.match(pattern, duration)
        if not match:
            return None

        days = int(match.group("days") or 0)
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        seconds = int(match.group("seconds") or 0)

        return days * 86400 + hours * 3600 + minutes * 60 + seconds

    def _fetch_video_durations(self, video_ids: list[str]) -> dict[str, int | None]:
        durations: dict[str, int | None] = {}

        for start in range(0, len(video_ids), 50):
            batch_ids = video_ids[start:start + 50]
            response = requests.get(
                f"{self.BASE_URL}/videos",
                params={
                    "part": "contentDetails",
                    "id": ",".join(batch_ids),
                    "key": YOUTUBE_API_KEY,
                },
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                durations[item["id"]] = self._duration_to_seconds(
                    item.get("contentDetails", {}).get("duration")
                )

        return durations
    

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
    
    def get_channel_videos(
        self,
        uploads_playlist_id: str,
        max_videos: int | None = None,
        max_pages: int | None = None,
    ): 
        videos = [] 
        next_page_token = None 
        page = 0 
        while max_pages is None or page < max_pages: 
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

                if max_videos is not None and len(videos) >= max_videos:
                    return videos

            next_page_token = data.get("nextPageToken") 
            page += 1 

            if not next_page_token: 
                break 

        durations = self._fetch_video_durations(
            [video["youtube_video_id"] for video in videos]
        )

        for video in videos:
            video["duration_seconds"] = durations.get(video["youtube_video_id"])

        return videos 
            

