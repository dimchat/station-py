
!function (ns, im) {
    'use strict';

    //
    //  Refresh User Profile
    //

    var get_request_path = function () {
        var url = window.location.href;
        var pos = url.indexOf('/', url.indexOf('://') + 3);
        url = url.substring(pos);
        pos = url.indexOf('?');
        if (pos > 0) {
            url = url.substring(0, pos);
        }
        pos = url.indexOf('#');
        if (pos > 0) {
            url = url.substring(0, pos);
        }
        return url;
    };

    var get_address = function () {
        var string = get_request_path();
        var pos = string.indexOf('.');
        if (pos > 0) {
            string = string.substring(0, pos);
        }
        var prefix = '/user/';
        if (string.indexOf(prefix) !== 0) {
            return null;
        }
        pos = string.indexOf('@');
        if (pos < 0) {
            return string.substring(prefix.length);
        } else {
            return string.substring(pos + 1);
        }
    };

    var get_identifier = function () {
        var facebook = DIMP.Facebook.getInstance();
        var users = facebook.getLocalUsers();
        var identifier;
        var address = get_address();
        if (address) {
            for (var i = 0; i < users.length; ++i) {
                identifier = users[i].identifier;
                if (identifier.address.equals(address)) {
                    return identifier;
                }
            }
            return null;
        }
        if (users.length > 0) {
            return users[0].identifier;
        } else {
            return null;
        }
    };

    var jsonify = function (object) {
        var json = DIMP.format.JSON.encode(object);
        return DIMP.format.UTF8.decode(json);
    };

    var show_form = function (dataSpan) {
        var identifier = get_identifier();
        var meta = im.getMeta(identifier);
        var profile = im.getProfile(identifier);
        dataSpan.innerText = jsonify(profile);
        // upload form
        var url = '/profile';
        var form = document.createElement('FORM');
        form.id = 'profile_form';
        form.action = url;
        form.method = 'POST';
        // ID
        var id = document.createElement('INPUT');
        id.name = 'ID';
        id.value = identifier;
        form.appendChild(id);
        // meta
        var m = document.createElement('INPUT');
        m.name = 'meta';
        m.value = jsonify(meta);
        form.appendChild(m);
        // profile
        var p = document.createElement('INPUT');
        p.name = 'profile';
        p.value = jsonify(profile);
        form.appendChild(p);
        // button
        var b = document.createElement('BUTTON');
        b.className = 'profile_button';
        b.type = 'submit';
        b.innerText = 'Upload Profile';
        form.appendChild(b);
        dataSpan.parentNode.appendChild(form);
    };

    var needs_update = function (json) {
        if (!json) {
            return true;
        }
        var dict = DIMP.format.JSON.decode(json);
        var profile = DIMP.Profile.getInstance(dict);
        if (!profile) {
            console.error('profile error: ', json);
            return true;
        }
        var facebook = DIMP.Facebook.getInstance();
        var identifier = facebook.getIdentifier(profile.getIdentifier());
        if (!identifier) {
            console.error('profile ID error: ', profile);
            return true;
        }
        var old = im.getProfile(identifier);
        return old.getValue('signature') !== profile.getValue("signature");
    };

    var show_modify_button = function (dataSpan) {
        // button
        var b = document.createElement('BUTTON');
        b.className = 'profile_button';
        b.innerText = 'Edit Profile';
        b.onclick = function (ev) {
            var win = dwitter.im.AccountWindow.show();
            win.onExit = function () {
                window.location.reload();
            };
        };
        dataSpan.parentNode.appendChild(b);
    };

    var refresh = function () {
        if (typeof DIMP !== 'object') {
            alert('loading DIM ...');
            return;
        }
        var spans = document.getElementsByClassName('profile');
        var dataSpan = spans[0];
        show_modify_button(dataSpan);
        if (needs_update(dataSpan.innerText)) {
            show_form(dataSpan);
        }
    };

    ns.addOnLoad(refresh);

    // ns.refreshUserProfile = refresh;

}(dwitter, dim);
