var XPMobileLoggedIn = false;

window.getListCamera = async () => {
    if(!XPMobileLoggedIn){
        await loginXPMobile()
        XPMobileLoggedIn = true
    }
    return new Promise(r => {
            XPMobileSDK.getAllViews(function (items) {
            const Items = items[0].Items[0].Items[0].Items;
           r(Items)
        });
    })
}
window.loginXPMobile = async () => {
    return new Promise(r => {
        LoginManager.loadAndLogin({
            connectionDidLogIn: r
        });
    })
    
}