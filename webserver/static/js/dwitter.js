
if (typeof dwitter !== 'object') {
    dwitter = {};
}

!function (ns, tui) {
    'use strict';

    var Size = tui.Size;
    var Point = tui.Point;

    var $ = tui.$;

    //
    //  Patch for position
    //
    var center_position = function (boxSize, winSize) {
        if (!winSize) {
            winSize = new Size(window.innerWidth, window.innerHeight);
            if (winSize.width < 1 || winSize.height < 1) {
                winSize = $(document.body).getSize();
            }
        }
        var x = (winSize.width - boxSize.width) >> 1;
        var y = (winSize.height - boxSize.height) >> 1;
        return new Point(x, y);
    };
    var random_position = function (boxSize, winSize) {
        var center = center_position(boxSize, winSize);
        var dw = boxSize.width >> 2;
        var dh = boxSize.height >> 2;
        var dx = Math.round(Math.random() * dw) - (dw >> 1);
        var dy = Math.round(Math.random() * dh) - (dh >> 1);
        var x = center.x + dx;
        var y = center.y + dy;
        if (x < 0) x = 0;
        if (y < 0) y = 0;
        return new Point(x, y);
    };
    tui.getCenterPosition = center_position;
    tui.getRandomPosition = random_position;

}(dwitter, tarsier.ui);

!function (ns, tui, dimp) {
    'use strict';

    var $ = tui.$;

    var Rect = tui.Rect;

    var Label = tui.Label;
    var Input = tui.Input;
    var Button = tui.Button;

    var FieldSet = tui.FieldSet;
    var Window = tui.Window;

    var Facebook = dimp.Facebook;
    var Register = dimp.extensions.Register;

    var RegisterWindow = function () {
        var frame = new Rect(0, 0, 320, 240);
        Window.call(this, frame);
        this.setClassName('registerWindow');
        this.setTitle('Create User Account');

        var basic = new FieldSet();
        basic.setClassName('profileFieldSet');
        basic.setCaption('Nickname');
        this.appendChild(basic);

        // nickname
        var nicknameLabel = new Label();
        nicknameLabel.setClassName('nicknameLabel');
        nicknameLabel.setText('Please input your nickname');
        basic.appendChild(nicknameLabel);
        // value
        var nickname = new Input();
        nickname.setClassName('nickname');
        basic.appendChild(nickname);

        // button
        var button = new Button();
        button.setClassName('OK');
        button.setText('Register');
        var win = this;
        button.onClick = function (ev) {
            win.submit(nickname.getValue());
        };
        this.appendChild(button);
    };
    dimp.Class(RegisterWindow, Window, null);

    RegisterWindow.prototype.submit = function (nickname) {
        var reg = new Register();
        var user = reg.createUser(nickname);
        if (user) {
            var facebook = Facebook.getInstance();
            facebook.setCurrentUser(user);
            // open login window
            ns.Main();
        } else {
            alert('Failed to create user account');
        }
        this.remove();
    };

    RegisterWindow.show = function () {
        var box = document.getElementById('registerWindow');
        if (box) {
            box = $(box);
        } else {
            box = new RegisterWindow();
            $(document.body).appendChild(box);
            // adjust position
            var point = tui.getCenterPosition(box.getSize());
            box.setOrigin(point);
            box.layoutSubviews();
        }
        box.floatToTop();
        return box;
    };

    ns.RegisterWindow = RegisterWindow;

}(dwitter, tarsier.ui, DIMP);

!function (ns, tui, dimp) {
    'use strict';

    var $ = tui.$;
    var Button = tui.Button;

    var main = function () {
        var facebook = dimp.Facebook.getInstance();
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
            alert('Change user name (coming soon)');
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
        new ns.RegisterWindow.show();
    };

    ns.Main = main;

}(dwitter, tarsier.ui, DIMP);

window.onload = function (ev) {
    dwitter.Main();
};
