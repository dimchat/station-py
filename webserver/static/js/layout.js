
!function (ns) {
    'use strict';

    var MAX_WIDTH = 768;  // 512, 256

    var screen_size = function () {
        if (document.compatMode === 'BackCompat') {
            return {
                width: document.body.clientWidth,
                height: document.body.clientHeight
            };
        } else {
            return {
                width: document.documentElement.clientWidth,
                height: document.documentElement.clientHeight
            };
        }
    };

    var set_width = function (div, width) {
        div.style.width = width + "px";
        return div
    };

    var layout = function () {
        var size = screen_size();
        if (size.width < MAX_WIDTH) {
            narrow_screen(size);
        } else {
            wide_screen();
        }
    };

    var narrow_screen = function (size) {
        var wrappers = document.getElementsByClassName('layout_wrapper');
        for (var i = 0; i < wrappers.length; ++i) {
            set_width(wrappers[i], size.width);
        }

        var panel = document.getElementsByClassName('layout_panel')[0];
        panel.style.float = 'none';
        // show border bottom of panel
        panel.style.borderBottom = '1px';
        panel.style.borderBottomStyle = 'solid';
        panel.style.borderBottomColor = '#57A1CE';
        set_width(panel, size.width - 16);

        var main = document.getElementsByClassName('layout_main')[0];
        main.style.float = 'none';
        // hide border right of main
        main.style.borderRight = '0';
        set_width(main, size.width - 16);
    };

    var wide_screen = function () {
        var wrappers = document.getElementsByClassName('layout_wrapper');
        for (var i = 0; i < wrappers.length; ++i) {
            set_width(wrappers[i], MAX_WIDTH);
        }

        var panel_width = Math.floor(MAX_WIDTH / 3);
        var main_width = MAX_WIDTH - panel_width;

        var panel = document.getElementsByClassName('layout_panel')[0];
        panel.style.float = 'right';
        // hide border bottom of panel
        panel.style.borderBottom = '0';
        set_width(panel, panel_width - 17);

        var main = document.getElementsByClassName('layout_main')[0];
        main.style.float = 'left';
        // show border right of main
        main.style.borderRight = '1px';
        main.style.borderRightStyle = 'solid';
        main.style.borderRightColor = '#57A1CE';
        set_width(main, main_width - 17);
    };

    layout();

    ns.addOnLoad(layout);

    window.onresize = layout;

}(dwitter);

!function (ns) {
    'use strict';

    //
    //  Logo
    //
    var logo = function () {
        var logo = document.getElementById('appName');
        if (!logo) {
            return;
        }
        logo.onclick = function () {
            ns.openURL('/');
        };
    };

    logo();

    ns.addOnLoad(logo);

    //
    //  Register Window
    //
    ns.showRegisterWindow = function () {
        if (!ns.im) {
            alert('loading DIM ...');
            return;
        }
        ns.im.RegisterWindow.show();
    };

}(dwitter);
