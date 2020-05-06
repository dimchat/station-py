
!function (ns) {
    'use strict';

    //
    //  JS request and response handler
    //

    var s_observers = [];

    ns.js = {
        request: function (url) {
            ns.im.loader.importJS(url);
        },
        /**
         *  Callback for JS request
         *
         * @param {Object} json - respond data from server
         * @param {Request} request - request object with 'path'
         */
        respond: function (json, request) {
            var ob;
            for (var i = 0; i < s_observers.length; ++i) {
                ob = s_observers[i];
                if (ob.evaluate(request)) {
                    ob.callback(json, request);
                }
            }
        },
        addObserver: function (evaluate, callback) {
            // check duplicated
            for (var i = s_observers.length - 1; i >= 0; --i) {
                var item = s_observers[i];
                if (item['evaluate'] === evaluate &&
                    item['callback'] === callback) {
                    console.error('duplicate observer');
                    return;
                }
            }
            // add observer
            s_observers.push({
                'evaluate': evaluate,
                'callback': callback
            });
        },
        removeObserver: function (evaluate, callback) {
            for (var i = s_observers.length; i >= 0; --i) {
                var item = s_observers[i];
                if (item['evaluate'] === evaluate &&
                    item['callback'] === callback) {
                    s_observers.splice(i, 1);
                }
            }
        }
    };

}(dwitter);

!function (ns) {
    'use strict';

    //
    //  Meta
    //

    var s_query_history = {};

    var get_meta = function (identifier) {
        if (typeof DIMP !== 'object') {
            alert('DIM loading');
            return;
        }
        var db = DIMP.db.MetaTable.getInstance();
        var meta = db.getMeta(identifier);
        if (!meta) {
            query_meta(identifier);
        }
        return meta;
    };

    // path: '/meta/{Address}.js'
    var meta_url = function (address) {
        if (typeof DIMP !== 'object') {
            var pos = address.indexOf('@');
            if (pos >= 0) {
                address = address.substring(pos + 1);
            }
        } else if (address instanceof DIMP.ID) {
            address = address.address;
        }
        return ns.baseURL + 'meta/' + address + '.js';
    };

    var query_meta = function (identifier) {
        var now = (new Date()).getTime() / 1000;
        var expires = s_query_history[identifier];
        if (expires && now < expires) {
            return;
        }
        s_query_history[identifier] = now + 300;
        ns.js.request(meta_url(identifier));
    };

    // callback for receive meta
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/meta\/[^.]+\.js$/.test(path);
        },
        function (json, request) {
            var facebook = DIMP.Facebook.getInstance();
            var path = request['path'];
            var pos = path.indexOf('.js');
            var identifier = path.substring('/meta/'.length, pos);
            identifier = facebook.getIdentifier(identifier);
            if (!identifier) {
                console.error('id error: ', request);
                return;
            }
            var meta = DIMP.Meta.getInstance(json);
            if (!meta) {
                console.error('meta error: ', json);
                return;
            }
            if (!identifier.name) {
                identifier = meta.generateIdentifier(identifier.getType());
            }
            var ok = facebook.saveMeta(meta, identifier);
            if (ok) {
                console.log('received meta: ', meta, identifier);
                var nc = DIMP.stargate.NotificationCenter.getInstance();
                nc.postNotification('MetaReceived', this,
                    {'ID': identifier, 'meta': meta});
            } else {
                console.error('failed to save meta: ', meta, identifier);
            }
        }
    );

    /**
     *  Get Meta for User ID
     *
     * @param {ID} identifier - user ID
     * @return {String} meta URL
     */
    ns.getMeta = get_meta;

}(dwitter);
