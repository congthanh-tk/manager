export default class VideoElement {
    constructor(videoElement, mediaSource, onFallback, cameraId) {
        this.fragmentCountTimeout = null;
        this.videoStuckTimeout = null;

        this.onFallback = onFallback;
        this.onDestroy = function () { };
        this.onPlayerStarted = function () { };
        this.onPlayerEnded = function () { };
        this.cameraId = cameraId;

        this.bufferSeekInterval = 2;
        this.videoStuckTimeoutMs = 10000;
        this.videoOnWaitingTimeoutMs = 3000;
        this.videoStuckBeginTimeoutMs = 2000;

        this.videoElement = videoElement;
        this._onCanPlayThrough = this.onCanPlayThrough.bind(this);
        this._onPlay = this.onPlay.bind(this);
        this._onEnded = this.onEnded.bind(this);

        this.videoElement.preload = "none";

        this.videoElement.addEventListener('canplay', this.onCanPlay.bind(this), false);
        this.videoElement.addEventListener('canplaythrough', this._onCanPlayThrough, false);
        //this.videoElement.addEventListener('play', this._onPlay, false); //Removed for now until we decide if we need to calculate the buffer time
        this.videoElement.addEventListener('waiting', this.onWaiting.bind(this));
        this.videoElement.addEventListener('ended', this._onEnded, false);
        this.videoElement.addEventListener('playing', this.onPlaying.bind(this), false);

        this.videoElement.src = window.URL.createObjectURL(mediaSource);
        this.videoCurrentTime = 0;
    }

    onPlaying(event) {
   
       var playPromise = this.videoElement.play();

       if (playPromise !== undefined) {
           playPromise.catch(this.onPlayPromiseReject.bind(this));
       }
    }


    onPlay(event) {
        let bufferTime = (new Date().getTime() - this.startDate) / 1000;
        if (Math.ceil(bufferTime) > this.bufferSeekInterval) {
            this.bufferSeekInterval = Math.ceil(bufferTime) + 2; // Set the seek interval to be 2 seconds more than the time the player needs to buffer the video before playing
        }
        this.videoElement.removeEventListener('play', this._onPlay, false);
    }

    onCanPlayThrough() {
        var playPromise = this.videoElement.play();

        if (playPromise !== undefined) {
            playPromise.catch(this.onPlayPromiseReject.bind(this));
        }

        this.videoElement.removeEventListener('canplaythrough', this._onCanPlayThrough, false);

        this.onPlayerStarted();
    }

    onCanPlay() {
        this.clearFragmentCountTimeout();
    }

    onEnded() {
        setTimeout(() => {
            this.videoElement.play();
        }, 200);
        // Kepp the restart logic for now in case we have to go back to it in this release
        //this.onPlayerEnded();
    }

    onWaiting(event) {
        var playedBefore = this.videoElement.played.length ? this.videoElement.played.end(0) : 0;
        var bufferedBefore = this.videoElement.buffered.length ? this.videoElement.buffered.end(0) : 0;

        this.fragmentCountTimeout = setTimeout(() => {
            var playedAfter = this.videoElement.played.length ? this.videoElement.played.end(0) : 0;
            var bufferedAfter = this.videoElement.buffered.length ? this.videoElement.buffered.end(0) : 0;

            if (playedBefore === playedAfter && bufferedBefore === bufferedAfter) {
                console.log('fallback onWaiting for 3 seconds:' +this.cameraId);
                this.onVideoStuck();
            }
        }, this.videoOnWaitingTimeoutMs);
    }

    onVideoStuck(event) {
        console.log('Video stuck for 3 seconds');
        this.onFallback();
        this.onDestroy();
    }

    onBeginVideoStuck(event) {
        this.onStartVideoStuck();
    }

    onEndVideoStuck(event) {
        this.onClearVideoStuck();
    }

    onPlayPromiseReject(event) {
        // do nothing for now
        // This gets rid of "DOMException: The play() request was interrupted by a call to pause()."
    }

    sync() {
        if (!this.startDate) {
            this.startDate = Date.now();
        }

        this.clearFragmentCountTimeout();

        var isVideoStuck = this.checkVideoStuck();
        
        // Set the current video time to be no more than 2 seconds behind the buffered
        if (!isVideoStuck
            && this.bufferSeekInterval 
            && this.videoElement.currentTime > this.bufferSeekInterval 
            && this.videoElement.buffered.end(0) > this.videoElement.currentTime + this.bufferSeekInterval) {

            this.videoElement.currentTime = this.videoElement.buffered.end(0) - 1;
            
            if (this.videoElement.paused === true) {
               
                var playPromise = this.videoElement.play();

                if (playPromise !== undefined) {
                    playPromise.catch(this.onPlayPromiseReject.bind(this));
                }
            }
            console.log('seek');
        }
    }

    checkVideoStuck()  {
        
        var isVideoStuck = false;

        if (!this.videoCurrentTimeTimeStamp) {
            this.videoCurrentTimeTimeStamp = Date.now();
            return isVideoStuck;
        }

        var dateNow = Date.now();

        if (this.videoCurrentTime != this.videoElement.currentTime) {
            this.videoCurrentTime = this.videoElement.currentTime;
            this.videoCurrentTimeTimeStamp = dateNow;
            this.onEndVideoStuck();
        }
        else if (dateNow - this.videoCurrentTimeTimeStamp > this.videoStuckTimeoutMs) {
            console.log('fallback videostuck for 10 seconds ')
            isVideoStuck = true;
            this.onVideoStuck();
        }
        else if (dateNow - this.videoCurrentTimeTimeStamp > this.videoStuckBeginTimeoutMs) {
            this.onBeginVideoStuck();
        }
    
        return isVideoStuck;
    }

    clearFragmentCountTimeout() {
        if (this.fragmentCountTimeout) {
            clearTimeout(this.fragmentCountTimeout);
            this.fragmentCountTimeout = null;
        }
    }

    destroy(keepVideoConnection) {
        this.videoElement.pause();

        // This fixes browser memory leak
        if (!keepVideoConnection) {
            // Fix for the "green screen" bug. 
            // Allows time for DOM manipolations (hide video element) to be done prior to cleaning the src
            setTimeout(function () {
                this.videoElement.src = "";
            }.bind(this), 3);
        } else {
            this.videoElement.src = "";
        }

        this.videoElement.removeEventListener('ended', this._onEnded);
        
        this.clearFragmentCountTimeout();
    }
}