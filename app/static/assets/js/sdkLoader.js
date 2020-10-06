(function () {
    window.LoadMobileSdk = function (callback) {
        callback = callback || function () { };

        var startApp = function () {
            XPMobileSDK.onLoad = callback;
            if (XPMobileSDK.isLoaded()) {
                callback();
            }
        }

        if ('XPMobileSDK' in window) {
            startApp();
        }
        else {
            script = document.createElement('script');
            script.addEventListener('load', startApp);
            script.src = '/static/assets/js/XPMobileSDK.js';
            document.querySelector('head').appendChild(script);
        }
    };
})();