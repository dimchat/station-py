
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
    var pos = base.indexOf('/', base.indexOf('://') + 3);
    base = base.substring(0, pos) + '/dwitter/';

    var query_meta = function (identifier) {
        var now = (new Date()).getTime() / 1000;
        var expires = s_query_history[identifier];
        if (expires && now < expires) {
            return;
        }
        s_query_history[identifier] = now + 300;
        // meta URL: '/dwitter/{ID}/meta.js'
        var url = base + identifier + '/meta.js';
        ns.js.request(url);
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

    ns.getMeta = get_meta;

}(dwitter);
