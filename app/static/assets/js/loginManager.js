const SEVERNAME = "http://192.168.6.35:8081"
const USERNAME = "demo"
const PASSWORD = "1";
(function (undefined) {
    var loginManager = function (settings) {
        var self = this;

        self.container;
        self.streamsContainer;
        self.loginFormShown;
        self.connectionDidLogIn;
        self.credentials;

        var connectForm,
            loginForm,
            lastObserver

        var findInner = function (selector) {
            return self.container.querySelector(selector);
        };

        function connectToServer() {
            // Connect to the desired server (defaults to the current URL)
     
            XPMobileSDKSettings.MobileServerURL = SEVERNAME;

            if (lastObserver) {
                XPMobileSDK.removeObserver(lastObserver);
            }

            lastObserver = {
                connectionDidConnect: connectionDidConnect,
                connectionDidLogIn: self.connectionDidLogIn
            };

            XPMobileSDK.addObserver(lastObserver);

            XPMobileSDK.connect(SEVERNAME);
        }

        function loginCommand(username, password) {
            // console.log("vao loginCommand")
            XPMobileSDK.login(username, password, {
                SupportsAudioIn: 'Yes',
                SupportsAudioOut: 'Yes'
            });
        }

        function normalizeSettings() {
            self.container = settings.container || {};
            self.streamsContainer = settings.streamsContainer || {};
            self.loginFormShown = settings.loginFormShown || function () { };
            self.connectionDidLogIn = settings.connectionDidLogIn || function () { };
            self.credentials = settings.credentials;
        }

        function init() {
            // console.log("vao init")
            normalizeSettings();

            connectionDidConnect = function () {
                loginCommand(USERNAME, PASSWORD);
            };

            setTimeout(connectToServer, 800);

            return;
        }

        return {
            init: init
        };
    };

    loginManager.loadAndLogin = function (params) {
        function loadLoginManager() {
            // console.log("vao loadLoginManager")

            // You can pass username and password for auto-login (just for simplicity in the sample, otherwise - NOT RECOMMENDED)
            var loginManager = new LoginManager({
                connectionDidLogIn: function () {
                    if(params.connectionDidLogIn)
                        params.connectionDidLogIn();
                }
            });

            loginManager.init();
        }

        LoadMobileSdk(loadLoginManager);
    };

    window.LoginManager = loginManager;
})();