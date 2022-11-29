
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

!function (ns) {
    'use strict';

    //
    //  Refresh User Profile
    //

    var show = function (dataSpan) {
        var json = dataSpan.innerText;
        if (!json || json.charAt(0) !== '{' || json.charAt(json.length-1) !== '}') {
            // not JsON data
            return;
        }
        var dict = DIMP.format.JSON.decode(json);
        var profile = DIMP.Profile.getInstance(dict);
        if (!profile) {
            console.error('profile error: ', json);
            return;
        }
        var facebook = DIMP.Facebook.getInstance();
        var identifier = facebook.getIdentifier(profile.getIdentifier());
        if (!identifier) {
            console.error('profile ID error: ', profile);
            return;
        }
        var div = document.createElement('DIV');
        div.className = 'user';
        // avatar URL
        var img = document.createElement('IMG');
        img.className = 'avatar';
        var url = profile.getProperty('avatar');
        if (url) {
            img.src = url;
        } else {
            img.src = 'http://apps.dim.chat/DICQ/images/icon-120.png';
        }
        div.appendChild(img);
        // user link
        var link = document.createElement('span');
        // link.href = ns.getUserURL(identifier.address);
        var name = profile.getName();
        if (!name) {
            if (identifier.name) {
                name = identifier.name;
            } else {
                name = identifier;
            }
        }
        var number = facebook.getNumberString(identifier);
        link.innerText = name + ' (' + number + ')';
        div.appendChild(link);
        // show
        var parentNode = dataSpan.parentNode;
        parentNode.insertBefore(div, dataSpan);
        parentNode.removeChild(dataSpan);
    };

    var refresh = function () {
        if (typeof DIMP !== 'object') {
            alert('loading DIM ...');
            return;
        }
        var spans = document.getElementsByClassName('profile');
        for (var i = spans.length - 1; i >= 0; --i) {
            show(spans[i]);
        }
    };

    ns.addOnLoad(refresh);

    // ns.refreshUserProfile = refresh;

}(dwitter);
