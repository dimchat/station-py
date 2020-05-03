
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
