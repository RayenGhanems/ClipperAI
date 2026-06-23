import ffmpeg

def extract_audio(mp4_file) -> str:
    ffmpeg.input(mp4_file).output(
        'wav/' + mp4_file.replace(".mp4", ".wav"),
        ar=16000,
        ac=1
    ).run()
    return 'wav/' + mp4_file.replace(".mp4", ".wav")