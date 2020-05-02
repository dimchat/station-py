
!function (ns) {
    'use strict';

    //
    //  Meta
    //

    var s_query_history = {};

    var get_meta = function (identifier) {
        if (!ns.im) {
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

    var base = window.location.href;
    var pos = base.indexOf('://');
    pos = base.indexOf('/', pos + 3);
    base = base.substring(0, pos);

    var user_url = function (address) {
        if (typeof DIMP === 'object') {
            if (address instanceof DIMP.ID) {
                address = address.address;
            }
        } else {
            var pos = address.indexOf('@');
            if (pos >= 0) {
                address = address.substring(pos + 1);
            }
        }
        return base + '/dwitter/' + address;
    };

    // path: '/dwitter/{ID}/meta.js'
    var meta_url = function (identifier) {
        return base + '/dwitter/' + identifier + '/meta.js';
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
            return /^\/dwitter\/[^\/]+\/meta\.js$/.test(path);
        },
        function (json, request) {
            var facebook = DIMP.Facebook.getInstance();
            var path = request['path'];
            var pos = path.indexOf('/meta.js');
            var identifier = path.substring('/dwitter/'.length, pos);
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
            var ok = facebook.saveMeta(meta, identifier);
            if (!ok) {
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

    /**
     *  Get User's home URL
     *
     * @param {ID} identifier - user ID
     * @return {String} user home URL
     */
    ns.getUserURL = user_url;

    ns.openURL = function (url) {
        if (url.indexOf('://') < 0) {
            if (url.charAt(0) === '/') {
                url = base + url;
            } else {
                console.error('open URL: ', url);
            }
        }
        window.document.location.href = url;
    };

}(dwitter);
