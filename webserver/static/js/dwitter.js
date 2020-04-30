
dwitter = dicq;

!function () {
    'use strict';

    var time_string = function (timestamp) {
        var time = new Date(timestamp * 1000);
        return time.toLocaleString();
    };

    var spans = document.getElementsByClassName('timestamp');
    for (var i = 0; i < spans.length; ++i) {
        var span = spans[i];
        var value = span.innerText;
        if (isNaN(value)) {
            continue;
        }
        span.innerText = time_string(parseInt(value));
    }
}();

!function (ns, tui, dimp) {
    'use strict';

    var Profile = dimp.Profile;
    var Facebook = dimp.Facebook;
    var AccountWindow = ns.AccountWindow;

    AccountWindow.prototype.submit = function (info) {
        var nickname = info['nickname'];
        var facebook = Facebook.getInstance();
        var user = facebook.getCurrentUser();
        if (!user) {
            throw Error('Current user not found');
        }
        var privateKey = facebook.getPrivateKeyForSignature(user.identifier);
        if (!privateKey) {
            throw Error('Failed to get private key for current user: ' + user);
        }
        // update profile
        var profile = user.getProfile();
        if (!profile) {
            profile = new Profile(user.identifier);
        }
        profile.setName(nickname);
        profile.sign(privateKey);
        facebook.saveProfile(profile);
        ns.Main();
        var text = 'Nickname updated, profile: ' + profile.getValue('data');
        alert(text);
        this.remove();
    };

}(dicq, tarsier.ui, DIMP);

!function (ns, tui, dimp) {
    'use strict';

    var $ = tui.$;
    var Button = tui.Button;

    var Facebook = dimp.Facebook;

    var AccountWindow = ns.AccountWindow;
    var RegisterWindow = ns.RegisterWindow;

    var main = function () {
        var facebook = Facebook.getInstance();
        var user = facebook.getCurrentUser();
        if (user) {
            show_user(user);
        } else {
            show_register();
        }
    };

    var show_user = function (user) {
        var name = user.getName();
        var btn = new Button();
        btn.setText(name);
        btn.onClick = function () {
            AccountWindow.show();
        };
        var tray = $('#myAccount');
        tray.removeChildren();
        tray.appendChild(btn);
    };

    var show_register = function () {
        var btn = new Button();
        btn.setText('Create Account');
        btn.onClick = open_register;
        var tray = $('#myAccount');
        tray.removeChildren();
        tray.appendChild(btn);
    };

    var open_register = function () {
        // register new account
        new RegisterWindow.show();
    };

    ns.Main = main;

}(dwitter, tarsier.ui, DIMP);

dwitter.Main();
