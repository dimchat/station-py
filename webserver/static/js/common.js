
if (typeof dwitter !== 'object') {
    dwitter = {}
}

!function (ns) {
    'use strict';

    //
    //  template format:
    //
    //      <div><a href="${{link}}">${text}</a></div>
    //
    var template = function (string, data, prefixes) {
        var html = string;
        for (var key in data) {
            if (!data.hasOwnProperty(key)) {
                continue;
            }
            var tag1 = prefixes[0] + '{' + key + '}';
            var tag2 = prefixes[1] + '%7B' + key + '%7D';
            var value = data[key];
            if (typeof value === 'string' || typeof value === 'number') {
                // string, number
                html = html.replace(tag1, value);
                html = html.replace(tag2, value);
            } else if (value instanceof Date) {
                // date
                html = html.replace(tag1, value.toString);
                html = html.replace(tag2, value.toString);
            } else if (value instanceof Array) {
                // list
                for (var i = 0; i < value.length; ++i) {
                    tag1 += '{' + i + '}';
                    tag2 += '%7B' + i + '%7D';
                    html = template(html, value[i], [tag1, tag2]);
                }
            } else {
                // dictionary
                for (var k in value) {
                    if (!value.hasOwnProperty(k)) {
                        continue;
                    }
                    tag1 += '{' + k + '}';
                    tag2 += '%7B' + k + '%7D';
                    html = template(html, value[k], [tag1, tag2]);
                }
            }
        }
        return html;
    };

    /**
     *  Replace template string with data
     *
     * @param {String} string - template string
     * @param {map} data - dictionary for key value pairs
     */
    ns.template = function (string, data) {
        return template(string, data, ['$', '%24']);
    };

}(dwitter);

!function (ns) {
    'use strict';

    //
    //  JS request and response handler
    //

    var observers = [];

    ns.js = {
        request: function (url, callback) {
            if (!ns.im) {
                alert('DIM loading');
                return;
            }
            ns.im.loader.importJS(url, callback);
        },
        /**
         *  Callback for JS request
         *
         * @param {Object} json - respond data from server
         * @param {Request} request - request object with 'path'
         */
        respond: function (json, request) {
            var ob;
            for (var i = 0; i < observers.length; ++i) {
                ob = observers[i];
                if (ob.evaluate(request)) {
                    ob.callback(json, request);
                }
            }
        },
        addObserver: function (evaluate, callback) {
            for (var i = observers.length - 1; i >= 0; --i) {
                var item = observers[i];
                if (item['evaluate'] === evaluate &&
                    item['callback'] === callback) {
                    alert('duplicate observer');
                    return;
                }
            }
            observers.push({
                'evaluate': evaluate,
                'callback': callback
            });
        },
        removeObserver: function (evaluate, callback) {
            for (var i = observers.length; i >= 0; --i) {
                var item = observers[i];
                if (item['evaluate'] === evaluate &&
                    item['callback'] === callback) {
                    observers.splice(i, 1);
                }
            }
        }
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
            console.log('add onload');
            s_list.push(fn);
        } else {
            console.error('run onload');
            // already loaded, run it immediately
            fn();
        }
    };

    var onload = function () {
        console.log('onload functions: ', s_list, arguments);
        for (var i = 0; i < s_list.length; ++i) {
            s_list[i].apply(arguments);
        }
        s_list = null;
    };

    ns.addOnLoad = add;

    ns.onload = onload;

}(dwitter);
