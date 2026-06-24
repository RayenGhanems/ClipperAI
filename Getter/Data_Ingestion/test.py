import os
from pytubefix import YouTube
from moviepy import VideoFileClip



def extract_audio(video_path: str):

    wav_dir = "storage/wav"
    os.makedirs(wav_dir, exist_ok=True)

    video_id = os.path.splitext(
        os.path.basename(video_path)
    )[0]

    audio_path = os.path.join(
        wav_dir,
        f"{video_id}.wav"
    )

    video = VideoFileClip(video_path)

    video.audio.write_audiofile(
        audio_path,
        codec="pcm_s16le"
    )

    video.close()

    return audio_path 
def download_one_video(youtube_url: str, video_id: str):
    output_dir = "storage/raw_videos"
    os.makedirs(output_dir, exist_ok=True)

    yt = YouTube(youtube_url)

    stream = (
        yt.streams
        .filter(progressive=True, file_extension="mp4")
        .order_by("resolution")
        .desc()
        .first()
    )

    if stream is None:
        raise RuntimeError("Aucun stream progressif MP4 trouvé.")

    saved_path = stream.download(
        output_path=output_dir,
        filename=f"{video_id}.mp4"
    )

    print("Téléchargé ici :", saved_path)
    print("Existe :", os.path.exists(saved_path))
    print("Taille :", os.path.getsize(saved_path), "octets")

    # Extraction audio
    audio_path = extract_audio(saved_path)

    print("Audio sauvegardé :", audio_path)
    print("Audio existe :", os.path.exists(audio_path))

if __name__ == "__main__":
    download_one_video(
        youtube_url="https://www.youtube.com/watch?v=mw_BBN73Uq0",
        video_id="mw_BBN73Uq0"
    )