interface AudioClipsTypes{
    audio_clip_tone: {
        id: number,
        audio_clip_tone_name: string,
        audio_clip_tone_slug: string,
        audio_clip_tone_symbol: string,
    },
    audio_file: string,
    audio_duration_s: number,
    audio_volume_peaks: number[],
}

export default AudioClipsTypes;