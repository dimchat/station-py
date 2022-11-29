
if (typeof dwitter !== 'object') {
    dwitter = {};
}

!function (ns) {
    'use strict';

    //
    //  template format:
    //
    //      <div><a href="${{link}}">${text}</a></div>
    //

    var replace = function (string, tag, data) {
        if (typeof data === 'string' || typeof data === 'number') {
            // string, number
            string = string.replace(new RegExp(tag, 'g'), data);
        } else if (data instanceof Date) {
            // date
            string = string.replace(new RegExp(tag, 'g'), data.toLocaleString());
        // } else if (data instanceof Array) {
        //     // array
        //     for (var i = 0; i < data.length; ++i) {
        //         string = replace(string, tag + '(\\[|%5B)'+i+'(\\]|%5D)', data[i]);
        //     }
        } else {
            // dictionary
            var names = Object.getOwnPropertyNames(data);
            for (var j = 0; j < names.length; ++j) {
                var k = names[j];
                string = replace(string, tag + '({|%7B)'+k+'(}|%7D)', data[k]);
            }
        }
        return string;
    };

    /**
     *  Replace template string with data
     *
     * @param {String} string - template string
     * @param {map} data - dictionary for key value pairs
     */
    ns.template = function (string, data) {
        return replace(string, '(\\$|%24)', data);
    };

}(dwitter);

!function (ns) {
    'use strict';

    //
    //  OnLoad
    //

    var s_list = [];

    var add = function (fn) {
        if (s_list) {
            s_list.push(fn);
        } else {
            // already loaded, run it immediately
            fn();
        }
    };

    var onload = function () {
        for (var i = 0; i < s_list.length; ++i) {
            s_list[i].apply(arguments);
        }
        s_list = null;
    };

    ns.addOnLoad = add;

    ns.onload = onload;

}(dwitter);

!function (ns) {
    'use strict';

    var base = window.location.href;
    var pos = base.indexOf('://');
    pos = base.indexOf('/', pos + 3);
    base = base.substring(0, pos);

    // path: '/channel/{Address}.js'
    var user_url = function (address) {
        if (typeof DIMP !== 'object') {
            var pos = address.indexOf('@');
            if (pos >= 0) {
                address = address.substring(pos + 1);
            }
        } else if (address instanceof DIMP.ID) {
            address = address.address;
        }
        return base + '/channel/' + address;
    };

    var open = function (url) {
        if (url.indexOf('://') < 0) {
            if (url.charAt(0) === '/') {
                url = base + url;
            } else {
                console.error('open URL: ', url);
            }
        }
        window.document.location.href = url;
    };

    ns.baseURL = base + '/';

    /**
     *  Get User's home URL
     *
     * @param {ID} identifier - user ID
     * @return {String} user home URL
     */
    ns.getUserURL = user_url;

    ns.openURL = open;

}(dwitter);
