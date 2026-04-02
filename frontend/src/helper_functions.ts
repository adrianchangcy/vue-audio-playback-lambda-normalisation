import { v4 } from 'uuid';



export function prettyDuration(seconds:number) : string {
    return new Date(
        seconds * 1000
    ).toISOString().substring(14, 19);
}


export function getRandomUUID() : string {

    return v4();
}


export async function drawCanvasRipples(
    canvas_container_rect:DOMRect,
    canvas_element:HTMLCanvasElement,
    audio_volume_peaks:number[]=[],
    transform_origin:'center'|'bottom'='center',
    ripple_width_px:number=2,
) : Promise<void> {

    //everything must be rounded to non-float values allow css image-rendering to work properly
    //be sure that <canvas> also has css w-full h-full

    if(
        (canvas_container_rect.width === 0 && canvas_container_rect.height === 0) ||
        audio_volume_peaks.length === 0
    ){

        return;
    }

    //get font colour for canvas later
    //when dark mode, colour will change accordingly
    const peak_colour_rgb = getComputedStyle(document.documentElement.getElementsByTagName('body')[0])['color'];

    //use DPI to maintain canvas resolution
    //depending on device, or whether user is zoomed in, DPI can be different
    const dpi = window.devicePixelRatio;

    //ensure ripple also scales with DPI
    ripple_width_px = Math.floor(2 * dpi);

    const canvas_context = canvas_element.getContext('2d') as CanvasRenderingContext2D;
    const ripple_quantity = audio_volume_peaks.length;

    //clear canvas for redraw
    canvas_context.clearRect(0, 0, canvas_element.width, canvas_element.height);

    //canvas width and css width are separate things
    //if they are not equal, you will get stretching, pixelation, etc.
    //we adjust resolution according to DPI, while canvas still behaves within w-full h-full CSS
    canvas_element.width = Math.floor(canvas_container_rect.width * dpi);
    canvas_element.height = Math.floor(canvas_container_rect.height * dpi);

    //spacing between ripples, divided without -1 so we have right-most space
    //what's surprising is that the ripples themselves don't need to be accounted for here
    const spacing = Math.floor(canvas_element.width / (ripple_quantity - 1));

    //recalculate width, with and without DPI
    //this allows us to perfectly fit our rects, and we can then mx-auto it
    const new_canvas_width = (spacing * (ripple_quantity - 1)) + ripple_width_px;
    canvas_element.width = new_canvas_width;
    canvas_element.style.width = (new_canvas_width / dpi).toString() + 'px';

    //canvas must have valid and latest width and height, else this won't be applied
    canvas_context.fillStyle = peak_colour_rgb;

    //use this function to ensure that peaks stay within our range
    function getRipple(
        canvas_height:number,
        audio_volume_peak:number,
        lowest_peak:number=0.05,
        highest_peak:number=1,
    ) : number {

        if(audio_volume_peak < lowest_peak){

            return canvas_height * lowest_peak;

        }else if(audio_volume_peak > highest_peak){

            return canvas_height;

        }else{

            return canvas_height * audio_volume_peak;
        }
    }

    //start drawing

    let ripple_height_px = 0;

    if(transform_origin === 'center'){

        //loop through and draw evenly spaced lines
        //do i=1 for left-most space to already exist
        for(let i = 0; i < ripple_quantity; i++){

            ripple_height_px = getRipple(canvas_element.height, audio_volume_peaks[i]);

            //draw ripple
            canvas_context.fillRect(
                (i * spacing),
                Math.round((canvas_element.height - ripple_height_px) / 2),
                ripple_width_px,
                ripple_height_px
            );
        }

    }else if(transform_origin === 'bottom'){

        //loop through and draw evenly spaced lines
        //do i=1 for left-most space to already exist
        for(let i = 0; i < ripple_quantity; i++){

            ripple_height_px = getRipple(canvas_element.height, audio_volume_peaks[i]);

            //draw ripple
            canvas_context.fillRect(
                (i * spacing),
                canvas_element.height,
                ripple_width_px,
                Math.round(-ripple_height_px)
            );
        }
    }
}












