<template>
    <div class="flex flex-col">

        <!--
        files in this repo and why they exist
            -package.json
                -the code works well up to the package versions listed
            -shims-vue.d.ts
                -some libraries need you to declare themselves using this file in order to be usable
            -VPlayback.vue
                -main file
                -imports VSliderYSmall.vue
                -has code from these separated sources in my project, inserted into VPlayback.vue for your ease of use:
                    -helper_functions.ts, base.css, tailwind.config.js
            -VSliderYSmall.vue
                -a simple reusable component with a surprising amount of code
                -i wanted to squeeze it into VPlayback.vue, but it's not worth your headache nor mine
            -ExampleApp.vue
                -showing you how to use <VPlayback>
            -lambdas.py
                -what you can use in AWS Lambda to normalise an audio file directly from S3 and return audio peaks
        -->

        <!--
        propIsOpen:
            true: playback is brought into view, and it will render everything
            false: pause audio
        -->
        <VPlayback
            :prop-audio-clip="audio_clip"
            :prop-is-open="true"
        />
    </div>
</template>

<script setup lang="ts">
    import VPlayback from '@/components/medium/VPlayback.vue';
</script>


<script lang="ts">
    import { defineComponent } from 'vue';
    import AudioClipsTypes from '@/types/AudioClips.interface';

    export default defineComponent({
        name: 'ExampleApp',
        data() {
            return {
                //move VPlayback's AudioClipsTypes interface to its own .interface file and you can use the interface here
                audio_clip: {
                    //instead of emoji, you can consider user icon images
                    //but you'll have to make changes to VPlayback by yourself
                    audio_clip_tone: {
                        id: 1,
                        audio_clip_tone_name: "happihappihappi",
                        audio_clip_tone_slug: "happihappihappihappihappi",
                        audio_clip_tone_symbol: "😊",
                    },
                    //you can obtain these by using AWS Lambda to process via FFMPEG and send to your server to store in db
                    audio_file: "your_local_filepath_or_https_url.mp3",
                    audio_duration_s: 60,
                    //VPlayback's drawCanvasRipples() will draw any amount
                    //if your VPlayback is expected to be narrow like my website, 20 peaks is good
                    audio_volume_peaks: [
                        0.05, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 1,
                        0.05, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 1,
                    ],
                } as AudioClipsTypes
            };
        },
    });
</script>