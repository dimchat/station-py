
!function (ns) {
    'use strict';

    //
    //  Refresh Timestamps
    //

    var refresh = function () {
        var spans = document.getElementsByClassName('timestamp');
        for (var i = 0; i < spans.length; ++i) {
            var span = spans[i];
            var value = span.innerText;
            if (isNaN(value)) {
                continue;
            }
            span.innerText = time_string(parseInt(value));
        }
    };

    var time_string = function (timestamp) {
        var time = new Date(timestamp * 1000);
        return time.toLocaleString();
    };

    refresh();

    ns.addOnLoad(refresh);

    ns.refreshTimestamp = refresh;

}(dwitter);

!function (ns) {
    'use strict';

    //
    //  Refresh Avatars
    //

    var refresh = function () {
        if (typeof DIMP !== 'object') {
            alert('loading DIM ...');
            return;
        }
        var facebook = DIMP.Facebook.getInstance();
        var images = document.getElementsByClassName('avatar');
        var img, identifier, profile, url;
        for (var i = 0; i < images.length; ++i) {
            img = images[i];
            identifier = img.getAttribute('did');
            if (identifier && identifier.charAt(0) !== '$') {
                identifier = facebook.getIdentifier(identifier);
                profile = facebook.getProfile(identifier);
                if (profile) {
                    url = profile.getProperty('avatar');
                    if (url) {
                        img.src = url;
                    }
                    img.removeAttribute('did');
                }
            }
        }
    };

    ns.addOnLoad(refresh);

    ns.refreshAvatar = refresh;

}(dwitter);

!function (ns) {
    'use strict';

    //
    //  Refresh User Links
    //

    var refresh = function () {
        if (typeof DIMP !== 'object') {
            alert('loading DIM ...');
            return;
        }
        var facebook = DIMP.Facebook.getInstance();
        var links = document.getElementsByTagName('A');
        var a, identifier;
        for (var i = 0; i < links.length; ++i) {
            a = links[i];
            identifier = a.getAttribute('did');
            if (identifier && identifier.charAt(0) !== '$') {
                identifier = facebook.getIdentifier(identifier);
                a.href = ns.getUserURL(identifier.address);
                a.removeAttribute('did');
            }
        }
    };

    ns.addOnLoad(refresh);

    // call it after received messages in channel
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/channel\/[^\/]+\.js$/.test(path);
        },
        refresh
    );

    // call it after received meta
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/profile\/[^.]+\.js$/.test(path);
        },
        refresh
    );

    ns.refreshLinks = refresh;

}(dwitter);

!function (ns) {
    'use strict';

    //
    //  Refresh Nicknames
    //

    var refresh = function () {
        if (typeof DIMP !== 'object') {
            alert('loading DIM ...');
            return;
        }
        var facebook = DIMP.Facebook.getInstance();
        var spans = document.getElementsByClassName('nickname');
        var div, identifier, profile, name, number;
        for (var i = 0; i < spans.length; ++i) {
            div = spans[i];
            identifier = div.getAttribute('did');
            if (identifier && identifier.charAt(0) !== '$') {
                identifier = facebook.getIdentifier(identifier);
                profile = facebook.getProfile(identifier);
                if (profile) {
                    name = profile.getName();
                    if (!name) {
                        if (identifier.name) {
                            name = identifier.name;
                        } else {
                            name = identifier;
                        }
                    }
                    number = facebook.getNumberString(identifier);
                    div.innerText = name + ' (' + number + ')';
                    div.removeAttribute('did');
                }
            }
        }
    };

    ns.addOnLoad(refresh);

    // call it after received messages in channel
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/channel\/[^\/]+\.js$/.test(path);
        },
        refresh
    );

    // call it after received meta
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/profile\/[^.]+\.js$/.test(path);
        },
        refresh
    );

    ns.refreshNicknames = refresh;

}(dwitter);
