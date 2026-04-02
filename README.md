# vue-audio-playback-and-lambda-normalization
Vue + Tailwind audio playback component to solve HTML Audio's native behaviours. Keyboard-friendly.
Includes Python/AWS Lambda to normalize audio and return volume peaks. Tests included.

Continue reading for a demo comparison and a detailed review of how these solutions solve specific problems, and advice on specific use cases.

### Demo
[HTMLAudio_demo.webm](https://github.com/user-attachments/assets/7ac5b80c-cffb-4ee3-b57b-20fb31078f07)
[VPlayback_demo.webm](https://github.com/user-attachments/assets/c5a94fdf-659e-4f14-908c-0fe6250b6b35)

### Disclaimer
To keep my full repo private, only safe and isolated full solutions are shared.
Thanks for understanding!

### To Recruiters 👋
You are welcome to a full code walkthrough during the interview. There's more to show.
With transferable core concepts learned across different tools, it feels great to improve at system design and big-picture focus.
For example, these switches will feel familiar to me:
- TS for Vue to React/Angular
- OOP for C# to Java,
- MVC for Django to Rails
- SQL for PostgreSQL to MySQL
- AWS to GCP/Azure, etc.
##### LinkedIn: https://www.linkedin.com/in/adrian-chang-8a87491a0/


## 1. VPlayback (Vue + Tailwind)

### Problems
- Default playback slider is staggered and not smooth
- When playback completes, HTMLAudio.ended is still false
- Dragging to end after completion causes sudden 0.5s final playback; bad UX
- Unpleasant DX when .play() returns a Promise, while .pause() is sync
- Animejs does not perfectly replay its animation
- No native display for audio peaks to prevent surprises

### "Why not use ready-made solutions like vue-audio?"
- The few decent options are either highly-opinionated, inactively maintained, bugged, or not detail-oriented
- My use-cases require infinite scrolling integration, >= 1 instances, URL/Blob data type, with specified design details
- I estimated that coding from scatch would only take slightly longer than forcing a solution to fit the mould
- This provided strong benefits of knowing what was coded, and a tailored solution to cover all use cases

#### I acknowledge that this is not always the best path during collaboration vs. solo work.
However, I believe in being context-first, and for this project, it was the right thing to do.

### Solutions
- Uses Animejs for smooth animation
- Lets HTMLAudio play the final 0.5s without the user knowing
- Write-once logic to handle .play() and .pause() easily across the codebase
- Fixed Animejs's edge cases while coupling it directly to HTMLAudio's states and UI actions
- Careful use of event listeners and focus behaviors for the keyboard, with YouTube as inspiration
- Mobile-friendly by re-rendering UI (sliders, peaks) whenever screen width changes
- Highly performant audio peaks display via HTMLCanvas, as having that many HTML divs will cause severe lag

### Caveats
- Moderately complex CSS solution was used to achieve certain design goals
- HTMLCanvas cannot be fixed to full playback width for perfect accuracy, due to it blurring with mismatched dimensions

### Tips on Use
- If you have >1 instances to track, give each of them their own UUID, and track with a parent component or store (Pinia)
- For infinite scrolling, use <Teleport> to reuse VPlayback by "taking it out" or "putting it in" (works with vue-virtual-scroller)
- Consider implementing your own replacement for emojis in the component (i.e. audio clip tones) with users' profile icons


## 2. AWS Lambda to Normalise Audio and Extract Volume Peaks

### Problems
- Different users capture audio differently, causing inconsistent audio volumes
- I love audio but I'm also easily startled, so I need surprise mitigation via volume peaks
- When using an equalizer for better audio, without a limiter, high signals will cause devices to clip loudly
- Unsure what counts as waiting too long for audio to finish processing
- Unsure what is the appropriate value for normalisation; not too quiet, not too loud

### Context
- My project, voicewake.com, is focused on short-form audio, capping the ceiling in processing time
- AWS Lambda costs vary by memory allocation, and cold startups is a time factor
- To give room for user tolerance, a distraction would be useful

### Solutions
- The server invokes Lambda in the background, to use FFMPEG to normalise and return volume peaks
- Used tests to measure the combined factors of audio length, Lambda memory, and cold/warm startup times
- Used an EU-recommended LUFS normalisation value of -23 with "loudnorm=I=-23:LRA=7:TP=-2"
- Redirect the user to the front page and give a pop-up when audio is done processing

### Lambda Test Results
- Take a look at /backend/test_lambdas.py for the numbers

### Tips on Use
#### Frontend
- User submits -> server updates db and returns S3 presigned URL -> frontend directly uploads
-> frontend calls server to process -> server queues Celery task to invoke Lambda and instantly returns 200 OK
-> redirect user to distraction (front page) -> poll server for processing completion -> display pop-up
#### Lambda
- Download ffmpeg.exe -> compress it into .zip -> store it privately in S3 -> let Lambda retrieve it
- Take a look at /backend/lambdas.py for code to run at Lambda, and /backend/services.py for invocation

## 🌸 Flowers/Credits 🌸
#### 🌸🌸🌸 A big thank you to the OSS contributors and maintainers for the code and documentation of Django, Vue, PostgreSQL, FFMPEG, Celery, Tailwind, Redis, and relevant libraries and packages. Thank you to those who post their rare edge-case solutions online for the love of the game. You've all brought light in the deep and dark spiralling tunnels. 🌸🌸🌸

## Final Thoughts
Leetcode was not helpful here. It has its time and place, and it teaches intuition, but most real-world problems are messy with complex constraints.
I'd choose to work on the latter, always. I have enough A's in maths to back it up, despite forgetting about most of it. 💔

My full project has a lot more to show compared to this. Thank you for checking out my work! 👋
